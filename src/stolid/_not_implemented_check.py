# Check for references to NotImplementedError outside of a function that
# is directly decorated with ``functools.singledispatch``.
#
# NotImplementedError is the conventional marker for an abstract method
# that subclasses must override. Stolid forbids subclassing for behavior
# (see SLD201/SLD202/SLD401), so the only legitimate use of the
# exception is the default body of a ``functools.singledispatch`` generic
# function, where it signals that no overload matched the argument type.

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._ast_inspection import FUNCTION_DEF_NODES, FunctionType, is_name_id

SLD206 = (
    "SLD206 Reference to NotImplementedError is only allowed in a function "
    "directly decorated with functools.singledispatch"
)


@dataclass(frozen=True, slots=True, kw_only=True)
class NotImplementedUseError:
    """A NotImplementedError-reference violation.

    ``lineno`` and ``col_offset`` locate the offending name; ``message``
    is the formatted SLD206 diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


def _is_singledispatch_decorator(decorator: ast.expr) -> bool:
    if is_name_id(decorator, "singledispatch"):
        return True
    if isinstance(decorator, ast.Attribute) and decorator.attr == "singledispatch":
        return True
    return False


def _has_singledispatch_decorator(func: FunctionType) -> bool:
    for decorator in func.decorator_list:
        if _is_singledispatch_decorator(decorator):
            return True
    return False


def _walk_no_function(node: ast.AST) -> Iterator[ast.AST]:
    yield node
    if isinstance(node, FUNCTION_DEF_NODES):
        return
    for child in ast.iter_child_nodes(node):
        yield from _walk_no_function(child)


def _refs_in_scope(stmts: list[ast.stmt]) -> Iterator[ast.Name]:
    for stmt in stmts:
        for node in _walk_no_function(stmt):
            if isinstance(node, ast.Name) and node.id == "NotImplementedError":
                yield node


def _emit(name: ast.Name) -> NotImplementedUseError:
    return NotImplementedUseError(
        lineno=name.lineno, col_offset=name.col_offset, message=SLD206
    )


def _check_function(func: FunctionType) -> Iterator[NotImplementedUseError]:
    if _has_singledispatch_decorator(func):
        return
    for name in _refs_in_scope(func.body):
        yield _emit(name)


def check_not_implemented(tree: ast.Module) -> Iterator[NotImplementedUseError]:
    """Yield SLD206 for ``NotImplementedError`` references in ``tree``.

    Each reference is reported unless its enclosing function is directly
    decorated with ``functools.singledispatch``.
    """
    for name in _refs_in_scope(tree.body):
        yield _emit(name)
    for node in ast.walk(tree):
        if isinstance(node, FUNCTION_DEF_NODES):
            yield from _check_function(node)
