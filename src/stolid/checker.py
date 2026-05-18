"""Flake8 plugin enforcing stolid conventions."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from typing import Iterator

from ._ast_inspection import bad_name_errors, is_attribute_attr, is_name_id
from ._check_runner import (
    CheckContext,
    ErrorLike,
    build_context,
    import_placement_errors,
    privacy_errors,
)
from ._class_check import check_abc_import, check_class
from ._constants import DANGEROUS_BUILTINS, MAX_MODULE_LINES
from ._docstring_check import check_docstrings
from ._function_check import check_function
from ._global_names_check import check_global_names
from ._module_overuse_check import check_module_overuse
from ._string_enum_check import check_string_enum

SLD102 = "SLD102 Use of patch/patch.object is prohibited (use dependency injection)"
SLD103 = (
    "SLD103 Use of '{}' is prohibited "
    "(dynamic code execution; add # noqa: SLD103 to silence if intentional)"
)
SLD203 = (
    "SLD203 Use of typing.cast is prohibited "
    "(use type narrowing; add # noqa: SLD203 to silence if intentional)"
)
SLD604 = "SLD604 Module has {} lines (limit: {})"
SLD605 = (
    "SLD605 'with' statement's body ends in a nested 'with' "
    "(flatten into contextlib.ExitStack)"
)

__all__ = ["Checker"]


@dataclass(frozen=True, slots=True, kw_only=True)
class Error:
    """A lint error: ``lineno``/``col_offset`` locate it; ``message`` describes it."""

    lineno: int
    col_offset: int
    message: str


def _error(node: ast.stmt | ast.expr, message: str) -> Error:
    return Error(lineno=node.lineno, col_offset=node.col_offset, message=message)


def _check_node(node: ast.AST, ctx: CheckContext) -> Iterator[ErrorLike]:
    # Check a single AST node for violations.
    if isinstance(node, ast.ImportFrom):
        yield from _check_import_from(node)
        yield from check_abc_import(node)
    elif isinstance(node, ast.Attribute):
        yield from _check_attribute(node)
    elif isinstance(node, ast.ClassDef):
        yield from check_class(node, ctx.abstractmethod_names)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        yield from check_function(node, ctx.lines, ctx.bracket_depths)
    elif isinstance(node, ast.Call):
        yield from _check_call(node, ctx.patch_names, ctx.cast_names)
    elif isinstance(node, ast.With):
        yield from _check_with(node, ctx.patch_names)
    elif isinstance(node, ast.Name):
        yield from _check_dangerous_name(node)


def _check_import_from(node: ast.ImportFrom) -> Iterator[Error]:
    # Check ImportFrom statements for forbidden mock/patch imports.
    if node.module not in ("unittest.mock", "mock"):  # noqa: SLD304
        return
    for alias in node.names:
        if alias.name == "patch":  # noqa: SLD304 SLD306
            yield _error(node, SLD102)


def _check_attribute(node: ast.Attribute) -> Iterator[Error]:
    # Check attribute access for patch usage.
    if node.attr != "patch":  # noqa: SLD306
        return
    value = node.value
    if is_attribute_attr(value, "mock"):
        yield _error(node, SLD102)
    elif is_name_id(value, "mock"):  # pragma: no branch
        yield _error(node, SLD102)


def _check_call(
    node: ast.Call, patch_names: set[str], cast_names: set[str]
) -> Iterator[Error]:
    # Check function calls.
    if isinstance(node.func, ast.Name):
        if node.func.id in patch_names:
            yield _error(node, SLD102)
        elif node.func.id in cast_names:
            yield _error(node, SLD203)
    elif isinstance(node.func, ast.Attribute):  # pragma: no branch
        yield from _check_call_attribute(node, patch_names)


def _check_call_attribute(node: ast.Call, patch_names: set[str]) -> Iterator[Error]:
    # Check Call nodes whose func is an Attribute (patch.object, typing.cast).
    func = node.func
    assert isinstance(func, ast.Attribute)
    if func.attr == "cast":  # noqa: SLD304
        if is_name_id(func.value, "typing"):
            yield _error(node, SLD203)
        return
    if func.attr != "object":  # noqa: SLD304
        return
    if isinstance(func.value, ast.Name):
        if func.value.id in patch_names:
            yield _error(node, SLD102)
    elif isinstance(func.value, ast.Attribute):  # pragma: no branch
        if func.value.attr == "patch":  # noqa: SLD306
            yield _error(node, SLD102)


def _check_dangerous_name(node: ast.Name) -> Iterator[Error]:
    # Flag any load-context reference to exec/eval/__import__.
    if isinstance(node.ctx, ast.Load) and node.id in DANGEROUS_BUILTINS:
        yield _error(node, SLD103.format(node.id))


def _check_with(node: ast.With, patch_names: set[str]) -> Iterator[Error]:
    # Check with statements for patch context managers and ExitStack-friendly nesting.
    for item in node.items:
        call = item.context_expr
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
            continue
        if call.func.id in patch_names:
            yield _error(node, SLD102)
    if isinstance(node.body[-1], ast.With):
        yield _error(node, SLD605)


def _get_module_name_from_filename(filename: str) -> str | None:
    # Extract module name from filename for bad name checking.
    if not filename:
        return None
    basename = os.path.basename(filename)
    if basename.endswith(".py"):
        module_name = basename[:-3]
        # Skip __init__ and other special files
        if module_name.startswith("__"):
            return None
        return module_name
    return None


def _module_level_errors(lines: list[str], filename: str) -> Iterator[ErrorLike]:
    # Yield errors derived from the module's lines or filename.
    if len(lines) > MAX_MODULE_LINES:
        yield Error(
            lineno=1,
            col_offset=0,
            message=SLD604.format(len(lines), MAX_MODULE_LINES),
        )
    module_name = _get_module_name_from_filename(filename)
    if module_name is not None:
        yield from bad_name_errors(module_name, 1, 0)


def _all_errors(
    tree: ast.Module, lines: list[str], filename: str
) -> Iterator[ErrorLike]:
    yield from _module_level_errors(lines, filename)
    yield from check_global_names(tree)
    yield from import_placement_errors(tree)
    yield from check_string_enum(tree)
    yield from check_docstrings(tree, filename)
    yield from check_module_overuse(tree)
    yield from privacy_errors(tree)
    ctx = build_context(tree, lines)
    for node in ast.walk(tree):
        yield from _check_node(node, ctx)


@dataclass(slots=True)
class Checker:  # noqa: SLD501 SLD503
    """Flake8 checker for stolid: parsed ``tree``, source ``lines``, ``filename``."""

    name = "stolid"
    version = "0.1.0"

    tree: ast.Module
    lines: list[str]
    filename: str = ""

    def run(self) -> Iterator[tuple[int, int, str, type]]:  # noqa: SLD303
        """Run all stolid checks and yield ``(line, col, message, type)`` tuples."""
        cls = type(self)
        for err in _all_errors(self.tree, self.lines, self.filename):
            yield (err.lineno, err.col_offset, err.message, cls)
