"""Check for missing or incomplete docstrings on public APIs.

Public modules, public classes, and public functions/methods must carry a
docstring. Function docstrings must mention every argument by name (except
the implicit ``self``/``cls``) and the return value (unless the function is
annotated ``-> None``). Dataclass docstrings must mention every non-private
field that is not documented via ``field(doc=...)``.

Inner functions (nested inside another function) and classes nested inside
a function never need docstrings.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass
from typing import Iterator

from ._ast_inspection import (
    FUNCTION_DEF_NODES,
    FunctionType,
    is_dataclass_decorator,
)
from ._constants import SLD811, SLD812, SLD813, SLD814, SLD815, SLD816

_RETURN_WORDS = re.compile(r"\b(?:returns?|yields?)\b", re.IGNORECASE)

_IMPLICIT_FIRST_ARGS = frozenset({"self", "cls"})


@dataclass(frozen=True, slots=True, kw_only=True)
class DocstringError:
    """A docstring-enforcement violation.

    Attributes ``lineno`` and ``col_offset`` locate the offending node;
    ``message`` is the formatted SLD81x diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


def _is_dunder(name: str) -> bool:
    """Return True iff ``name`` looks like a dunder (``__foo__``)."""
    return name.startswith("__") and name.endswith("__")


def _is_public(name: str) -> bool:
    """Return True iff ``name`` is a public identifier (no leading underscore)."""
    if not name.startswith("_"):
        return True
    return _is_dunder(name)


def _module_basename(filename: str) -> str | None:
    """Return the module's basename (without ``.py``), or ``None`` if unavailable."""
    if not filename:
        return None
    base = os.path.basename(filename)
    if not base.endswith(".py"):
        return None
    return base[:-3]


def _module_is_public(filename: str) -> bool:
    """Return True iff ``filename`` refers to a public module file."""
    name = _module_basename(filename)
    if name is None:
        return False
    return _is_public(name)


def _mentions_return(docstring: str) -> bool:
    """Return True iff ``docstring`` references a return or yielded value."""
    return bool(_RETURN_WORDS.search(docstring))


def _mentions_name(docstring: str, name: str) -> bool:
    """Return True iff ``name`` appears as a word in ``docstring``."""
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])"
    return bool(re.search(pattern, docstring))


def _returns_none(node: FunctionType) -> bool:
    """Return True iff ``node`` returns ``None`` (annotated or unannotated)."""
    if node.returns is None:
        return True
    if isinstance(node.returns, ast.Constant) and node.returns.value is None:
        return True
    return False


def _function_arg_names(node: FunctionType) -> list[str]:
    """Return the user-visible argument names of ``node`` (``self``/``cls`` removed)."""
    args = node.args
    positional = args.posonlyargs + args.args
    start = 1 if positional and positional[0].arg in _IMPLICIT_FIRST_ARGS else 0
    names = [arg.arg for arg in positional[start:] + args.kwonlyargs]
    if args.vararg is not None:
        names.append(args.vararg.arg)
    if args.kwarg is not None:
        names.append(args.kwarg.arg)
    return names


def _error(node: ast.stmt, message: str) -> DocstringError:
    """Build a :class:`DocstringError` anchored at ``node`` with ``message``."""
    return DocstringError(
        lineno=node.lineno, col_offset=node.col_offset, message=message
    )


def _check_function_docstring(
    node: FunctionType, docstring: str
) -> Iterator[DocstringError]:
    """Yield SLD814/SLD815 errors for an existing function ``docstring``."""
    for arg_name in _function_arg_names(node):
        if not _mentions_name(docstring, arg_name):
            yield _error(node, SLD814.format(node.name, arg_name))
    if _returns_none(node):
        return
    if not _mentions_return(docstring):
        yield _error(node, SLD815.format(node.name))


def _check_function(node: FunctionType) -> Iterator[DocstringError]:
    """Yield docstring violations for the public function ``node``."""
    if not _is_public(node.name):
        return
    if _is_dunder(node.name):
        return
    docstring = ast.get_docstring(node)
    if docstring is None:
        yield _error(node, SLD813.format(node.name))
        return
    yield from _check_function_docstring(node, docstring)


def _dataclass_field_has_doc(value: ast.expr | None) -> bool:
    """Return True iff ``value`` is ``field(doc=...)`` (documented in-place)."""
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    is_field = (isinstance(func, ast.Name) and func.id == "field") or (
        isinstance(func, ast.Attribute) and func.attr == "field"
    )
    if not is_field:
        return False
    return any(kw.arg == "doc" for kw in value.keywords)


def _class_field_names(node: ast.ClassDef) -> list[str]:
    """Return the annotated public field names of ``node`` requiring documentation."""
    names: list[str] = []
    for child in node.body:
        if not isinstance(child, ast.AnnAssign):
            continue
        target = child.target
        if not isinstance(target, ast.Name):
            continue
        if target.id.startswith("_"):
            continue
        if _dataclass_field_has_doc(child.value):
            continue
        names.append(target.id)
    return names


def _is_dataclass_class(node: ast.ClassDef) -> bool:
    """Return True iff ``node`` carries a ``@dataclass`` decorator."""
    return any(is_dataclass_decorator(d) for d in node.decorator_list)


def _check_dataclass_fields(
    node: ast.ClassDef, docstring: str
) -> Iterator[DocstringError]:
    """Yield SLD816 errors for dataclass ``node`` fields missing from ``docstring``."""
    for field_name in _class_field_names(node):
        if not _mentions_name(docstring, field_name):
            yield _error(node, SLD816.format(node.name, field_name))


def _check_class(node: ast.ClassDef) -> Iterator[DocstringError]:
    """Yield SLD812/SLD816 violations for the public class ``node``."""
    if not _is_public(node.name):
        return
    docstring = ast.get_docstring(node)
    if docstring is None:
        yield _error(node, SLD812.format(node.name))
        return
    if _is_dataclass_class(node):
        yield from _check_dataclass_fields(node, docstring)


def _walk_scope(body: list[ast.stmt]) -> Iterator[DocstringError]:
    """Walk module/class-level ``body`` and yield docstring violations.

    Recurses into class bodies (methods are still scope-level) but never
    descends into function bodies; inner functions and inner classes are
    intentionally exempt from the docstring rules.
    """
    for stmt in body:
        if isinstance(stmt, FUNCTION_DEF_NODES):
            yield from _check_function(stmt)
        elif isinstance(stmt, ast.ClassDef):
            yield from _check_class(stmt)
            yield from _walk_scope(stmt.body)


def _check_module_docstring(
    tree: ast.Module, filename: str
) -> Iterator[DocstringError]:
    """Yield SLD811 if ``filename`` is a public module without a module docstring."""
    if not _module_is_public(filename):
        return
    if ast.get_docstring(tree) is not None:
        return
    name = _module_basename(filename)
    assert name is not None
    yield DocstringError(lineno=1, col_offset=0, message=SLD811.format(name))


def check_docstrings(tree: ast.Module, filename: str) -> Iterator[DocstringError]:
    """Yield SLD81x docstring violations for ``tree`` parsed from ``filename``."""
    yield from _check_module_docstring(tree, filename)
    yield from _walk_scope(tree.body)
