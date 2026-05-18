# Two complementary docstring policies:
#
# SLD81x require docstrings on public modules, classes, and functions/
# methods. Function docstrings must mention every argument by name (except
# the implicit ``self``/``cls``) and the return value (unless the function
# is annotated ``-> None``). Dataclass docstrings must mention every
# non-private field that is not documented via ``field(doc=...)``.
#
# SLD82x forbid docstrings on private modules, classes, and functions/
# methods -- implementation notes belong in ``#`` comments. Dunder names
# and inner functions (nested inside another function) are exempt from
# both policies.

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

SLD811 = "SLD811 Public module '{}' missing docstring"
SLD812 = "SLD812 Public class '{}' missing docstring"
SLD813 = "SLD813 Public function/method '{}' missing docstring"
SLD814 = (
    "SLD814 Function '{}' docstring does not mention argument '{}' "
    "(describe the semantics of every parameter)"
)
SLD815 = (
    "SLD815 Function '{}' docstring does not mention the return value "
    "(use 'return'/'returns'/'yield'/'yields' to describe what is produced)"
)
SLD816 = (
    "SLD816 Dataclass '{}' docstring does not mention field '{}' "
    "(document every non-private field, or annotate with field(doc=...))"
)
SLD821 = (
    "SLD821 Private module '{}' has a docstring "
    "(use ``#`` comments for implementation notes)"
)
SLD822 = (
    "SLD822 Private class '{}' has a docstring "
    "(use ``#`` comments for implementation notes)"
)
SLD823 = (
    "SLD823 Private function/method '{}' has a docstring "
    "(use ``#`` comments for implementation notes)"
)

_RETURN_WORDS = re.compile(r"\b(?:returns?|yields?)\b", re.IGNORECASE)

_IMPLICIT_FIRST_ARGS = frozenset({"self", "cls"})


@dataclass(frozen=True, slots=True, kw_only=True)
class DocstringError:
    """A docstring-enforcement violation.

    Attributes ``lineno`` and ``col_offset`` locate the offending node;
    ``message`` is the formatted SLD81x/SLD82x diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _is_public(name: str) -> bool:
    if not name.startswith("_"):
        return True
    return _is_dunder(name)


def _module_basename(filename: str) -> str | None:
    if not filename:
        return None
    base = os.path.basename(filename)
    if not base.endswith(".py"):
        return None
    return base[:-3]


def _mentions_return(docstring: str) -> bool:
    return bool(_RETURN_WORDS.search(docstring))


def _mentions_name(docstring: str, name: str) -> bool:
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])"
    return bool(re.search(pattern, docstring))


def _returns_none(node: FunctionType) -> bool:
    if node.returns is None:
        return True
    if isinstance(node.returns, ast.Constant) and node.returns.value is None:
        return True
    return False


def _function_arg_names(node: FunctionType) -> list[str]:
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
    return DocstringError(
        lineno=node.lineno, col_offset=node.col_offset, message=message
    )


def _check_function_docstring(
    node: FunctionType, docstring: str
) -> Iterator[DocstringError]:
    for arg_name in _function_arg_names(node):
        if not _mentions_name(docstring, arg_name):
            yield _error(node, SLD814.format(node.name, arg_name))
    if _returns_none(node):
        return
    if not _mentions_return(docstring):
        yield _error(node, SLD815.format(node.name))


def _check_function(node: FunctionType) -> Iterator[DocstringError]:
    if _is_dunder(node.name):
        return
    docstring = ast.get_docstring(node)
    if _is_public(node.name):
        if docstring is None:
            yield _error(node, SLD813.format(node.name))
            return
        yield from _check_function_docstring(node, docstring)
        return
    if docstring is not None:
        yield _error(node, SLD823.format(node.name))


def _dataclass_field_has_doc(value: ast.expr | None) -> bool:
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
    return any(is_dataclass_decorator(d) for d in node.decorator_list)


def _check_dataclass_fields(
    node: ast.ClassDef, docstring: str
) -> Iterator[DocstringError]:
    for field_name in _class_field_names(node):
        if not _mentions_name(docstring, field_name):
            yield _error(node, SLD816.format(node.name, field_name))


def _check_class(node: ast.ClassDef) -> Iterator[DocstringError]:
    docstring = ast.get_docstring(node)
    if _is_public(node.name):
        if docstring is None:
            yield _error(node, SLD812.format(node.name))
            return
        if _is_dataclass_class(node):
            yield from _check_dataclass_fields(node, docstring)
        return
    if docstring is not None:
        yield _error(node, SLD822.format(node.name))


# Recurses into class bodies (methods are still scope-level) but never
# descends into function bodies; inner functions and inner classes are
# intentionally exempt from the docstring rules.
def _walk_scope(body: list[ast.stmt]) -> Iterator[DocstringError]:
    for stmt in body:
        if isinstance(stmt, FUNCTION_DEF_NODES):
            yield from _check_function(stmt)
        elif isinstance(stmt, ast.ClassDef):
            yield from _check_class(stmt)
            yield from _walk_scope(stmt.body)


def _check_module_docstring(
    tree: ast.Module, filename: str
) -> Iterator[DocstringError]:
    name = _module_basename(filename)
    if name is None:
        return
    has_docstring = ast.get_docstring(tree) is not None
    if _is_public(name):
        if not has_docstring:
            yield DocstringError(lineno=1, col_offset=0, message=SLD811.format(name))
        return
    if has_docstring:
        yield DocstringError(lineno=1, col_offset=0, message=SLD821.format(name))


def check_docstrings(tree: ast.Module, filename: str) -> Iterator[DocstringError]:
    """Yield SLD81x/SLD82x violations for ``tree`` parsed from ``filename``."""
    yield from _check_module_docstring(tree, filename)
    yield from _walk_scope(tree.body)
