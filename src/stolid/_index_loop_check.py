# Check for manual index-walking loops that should use enumerate or
# direct iteration.
#
# SLD610: ``for i in range(len(seq))`` builds indices only to turn around
# and subscript the sequence -- ``enumerate(seq)`` (when the index is
# wanted) or plain iteration (when it is not) says the same thing without
# the bookkeeping. The trigger is a ``for`` loop whose iterable is a
# ``range(...)`` call with a ``len(...)`` anywhere in its arguments, so
# ``range(len(x))``, ``range(0, len(x))``, and ``range(len(x) - 1)`` all
# qualify, while ``range(n)`` over a plain count is left alone.
#
# SLD611: ``while i < len(seq)`` is the same manual cursor in while-loop
# clothing -- the body invariably ends in ``i += 1`` and ``seq[i]``. An
# iterator or ``enumerate`` carries the position for you. The trigger is
# a ``while`` whose test compares a bare name against an expression
# containing ``len(...)`` with an ordering operator (``<``, ``<=``,
# ``>``, ``>=``). ``while len(stack) > 0`` -- a worklist drained by
# mutation against a constant bound -- is deliberately not flagged.

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._ast_inspection import is_name_id

SLD610 = (
    "SLD610 'for' over 'range(len(...))' should use 'enumerate' "
    "or iterate the sequence directly"
)
SLD611 = (
    "SLD611 'while' indexing against 'len(...)' should use 'enumerate' "
    "or an iterator"
)

_ORDERING_OPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)


@dataclass(frozen=True, slots=True, kw_only=True)
class IndexLoopError:
    """A manual index-loop violation.

    ``lineno`` and ``col_offset`` locate the offending loop; ``message``
    is the formatted SLD610 or SLD611 diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


def _emit(node: ast.stmt, message: str) -> IndexLoopError:
    return IndexLoopError(
        lineno=node.lineno, col_offset=node.col_offset, message=message
    )


def _is_len_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and is_name_id(node.func, "len")


def _contains_len_call(node: ast.expr) -> bool:
    return any(_is_len_call(child) for child in ast.walk(node))


def _is_range_len(node: ast.expr) -> bool:
    if not isinstance(node, ast.Call) or not is_name_id(node.func, "range"):
        return False
    return any(_contains_len_call(arg) for arg in node.args)


def _check_for(node: ast.For) -> Iterator[IndexLoopError]:
    if _is_range_len(node.iter):
        yield _emit(node, SLD610)


def _is_index_comparison(left: ast.expr, right: ast.expr) -> bool:
    # One side is a bare cursor name; the other measures a length.
    return (isinstance(left, ast.Name) and _contains_len_call(right)) or (
        isinstance(right, ast.Name) and _contains_len_call(left)
    )


def _check_while(node: ast.While) -> Iterator[IndexLoopError]:
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return
    if not isinstance(test.ops[0], _ORDERING_OPS):
        return
    if _is_index_comparison(test.left, test.comparators[0]):
        yield _emit(node, SLD611)


def check_index_loops(tree: ast.Module) -> Iterator[IndexLoopError]:
    """Yield SLD610 / SLD611 violations from ``tree``."""
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            yield from _check_for(node)
        elif isinstance(node, ast.While):
            yield from _check_while(node)
