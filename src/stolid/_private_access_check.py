"""Detect violations of Python's underscore-prefix privacy convention.

Five violation kinds are emitted:

- ``external_private_read``: reading ``obj._attr`` outside the owning class.
- ``external_private_write``: assigning or deleting ``obj._attr`` outside it.
- ``absolute_private_import``: ``from pkg import _name`` (absolute import).
- ``private_submodule_import``: ``import pkg._sub`` or
  ``from pkg._sub import x``.
- ``module_private_attr``: ``mod._attr`` where ``mod`` is a name bound by an
  import.

Relative imports (``from . import _x``, ``from ._sub import y``) are permitted:
the syntax itself draws the package boundary.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Iterator

from ._ast_inspection import (
    FUNCTION_DEF_NODES,
    FunctionType,
    is_attribute_in,
    is_dunder_method,
    is_name_id,
)

EXTERNAL_PRIVATE_READ = "external_private_read"
EXTERNAL_PRIVATE_WRITE = "external_private_write"
ABSOLUTE_PRIVATE_IMPORT = "absolute_private_import"
PRIVATE_SUBMODULE_IMPORT = "private_submodule_import"
MODULE_PRIVATE_ATTR = "module_private_attr"


@dataclass(frozen=True, slots=True, kw_only=True)
class PrivacyError:
    """A privacy convention violation."""

    lineno: int
    col_offset: int
    kind: str
    attr: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _State:
    """Traversal state for the privacy visitor.

    ``_class_stack`` records enclosing class names; only its emptiness matters.
    ``_privileged_args`` records the first-arg name per enclosing function frame
    (``None`` if the frame is not a method). ``_imported_names`` is the set of
    names bound by any ``import`` or ``from`` statement seen so far.
    """

    _class_stack: list[str] = field(default_factory=list)
    _privileged_args: list[str | None] = field(default_factory=list)
    _imported_names: set[str] = field(default_factory=set)
    _violations: list[PrivacyError] = field(default_factory=list)

    def in_class(self) -> bool:
        return bool(self._class_stack)

    def enter_class(self, name: str) -> None:
        self._class_stack.append(name)

    def exit_class(self) -> None:
        self._class_stack.pop()

    def enter_function(self, privileged: str | None) -> None:
        self._privileged_args.append(privileged)

    def exit_function(self) -> None:
        self._privileged_args.pop()

    def privileged_arg(self) -> str | None:
        if not self._privileged_args:
            return None
        return self._privileged_args[-1]

    def is_imported(self, name: str) -> bool:
        return name in self._imported_names

    def bind_import(self, name: str) -> None:
        self._imported_names.add(name)

    def record(self, node: ast.stmt | ast.expr, kind: str, attr: str) -> None:
        self._violations.append(
            PrivacyError(
                lineno=node.lineno,
                col_offset=node.col_offset,
                kind=kind,
                attr=attr,
            )
        )

    def violations(self) -> Iterator[PrivacyError]:
        yield from self._violations


def _is_private(name: str) -> bool:
    """True for a single- or double-underscore name that is not a dunder."""
    return name.startswith("_") and not is_dunder_method(name)


def _has_private_segment(dotted: str) -> bool:
    """True if any segment of ``dotted`` is a private name."""
    return any(_is_private(part) for part in dotted.split("."))


def _has_staticmethod(node: FunctionType) -> bool:
    for decorator in node.decorator_list:
        if is_name_id(decorator, "staticmethod"):
            return True
        if is_attribute_in(decorator, ("staticmethod",)):
            return True
    return False


def _privileged_arg(node: FunctionType, in_class: bool) -> str | None:
    if not in_class:
        return None
    if _has_staticmethod(node):
        return None
    if not node.args.args:
        return None
    return node.args.args[0].arg


def _visit_children(node: ast.AST, state: _State) -> None:
    for child in ast.iter_child_nodes(node):
        _visit(child, state)


def _visit_class(node: ast.ClassDef, state: _State) -> None:
    state.enter_class(node.name)
    _visit_children(node, state)
    state.exit_class()


def _visit_function(node: FunctionType, state: _State) -> None:
    state.enter_function(_privileged_arg(node, state.in_class()))
    _visit_children(node, state)
    state.exit_function()


def _is_write_context(node: ast.Attribute) -> bool:
    return isinstance(node.ctx, (ast.Store, ast.Del))


def _check_attribute(node: ast.Attribute, state: _State) -> None:
    attr = node.attr
    if not _is_private(attr):
        return
    if isinstance(node.value, ast.Name):
        if node.value.id == state.privileged_arg():
            return
        if state.is_imported(node.value.id):
            state.record(node, MODULE_PRIVATE_ATTR, attr)
            return
    if _is_write_context(node):
        state.record(node, EXTERNAL_PRIVATE_WRITE, attr)
    else:
        state.record(node, EXTERNAL_PRIVATE_READ, attr)


def _visit_attribute(node: ast.Attribute, state: _State) -> None:
    _check_attribute(node, state)
    _visit_children(node, state)


def _visit_import(node: ast.Import, state: _State) -> None:
    for alias in node.names:
        if _has_private_segment(alias.name):
            state.record(node, PRIVATE_SUBMODULE_IMPORT, alias.name)
        bound = (alias.asname or alias.name).split(".")[0]
        state.bind_import(bound)


def _visit_import_from(node: ast.ImportFrom, state: _State) -> None:
    if node.level > 0:
        for alias in node.names:
            state.bind_import(alias.asname or alias.name)
        return
    if node.module is not None and _has_private_segment(node.module):
        state.record(node, PRIVATE_SUBMODULE_IMPORT, node.module)
    for alias in node.names:
        if _is_private(alias.name):
            state.record(node, ABSOLUTE_PRIVATE_IMPORT, alias.name)
        state.bind_import(alias.asname or alias.name)


def _visit(node: ast.AST, state: _State) -> None:
    if isinstance(node, ast.ClassDef):
        _visit_class(node, state)
    elif isinstance(node, FUNCTION_DEF_NODES):
        _visit_function(node, state)
    elif isinstance(node, ast.Attribute):
        _visit_attribute(node, state)
    elif isinstance(node, ast.Import):
        _visit_import(node, state)
    elif isinstance(node, ast.ImportFrom):
        _visit_import_from(node, state)
    else:
        _visit_children(node, state)


def check_private_access(tree: ast.AST) -> Iterator[PrivacyError]:
    """Yield privacy convention violations found in ``tree``."""
    state = _State()
    _visit(tree, state)
    yield from state.violations()
