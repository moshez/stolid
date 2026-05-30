# Function-shape checks: argument count and complexity (SLD602/SLD601).
# Also checks function names for forbidden words (SLD701) and the
# is_-predicate convention (SLD704).

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator, Mapping, Sequence

from ._ast_inspection import FunctionType, get_base_name
from ._ast_metrics import get_function_arg_count, get_function_complexity
from ._ast_names import bad_name_errors_as
from ._check_runner import format_sld601
from ._constants import MAX_FUNCTION_ARGS, MAX_FUNCTION_LINES

SLD602 = "SLD602 Function '{}' has {} arguments (limit: {})"
SLD704 = (
    "SLD704 Function '{}' uses 'is_' prefix but return annotation is not bool "
    "(annotate '-> bool' or drop the predicate prefix)"
)

_BOOL_RETURN_NAMES: frozenset[str] = frozenset({"bool", "TypeGuard", "TypeIs"})


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionError:
    """A function-rule violation.

    ``lineno`` and ``col_offset`` locate the offending node; ``message``
    is the formatted SLD601/SLD602/SLD701 diagnostic.

    Attributes:
        lineno: Line number of the offending node.
        col_offset: Column offset of the offending node.
        message: The formatted SLD601/SLD602/SLD701 diagnostic string.
    """

    lineno: int
    col_offset: int
    message: str


def _error(node: ast.stmt | ast.expr, message: str) -> FunctionError:
    return FunctionError(
        lineno=node.lineno, col_offset=node.col_offset, message=message
    )


def _has_is_predicate_prefix(name: str) -> bool:
    stripped = name.lstrip("_")
    return stripped.startswith("is_") and len(stripped) > 3


def _check_is_predicate(node: FunctionType) -> Iterator[FunctionError]:
    if not _has_is_predicate_prefix(node.name):
        return
    if node.returns is None:
        return
    if get_base_name(node.returns) in _BOOL_RETURN_NAMES:
        return
    yield _error(node, SLD704.format(node.name))


def check_function(
    node: FunctionType, lines: Sequence[str], bracket_depths: Mapping[int, int]
) -> Iterator[FunctionError]:
    """Yield SLD601/SLD602/SLD701/SLD704 violations for function ``node``.

    ``lines`` is the enclosing module source and ``bracket_depths`` maps
    each line number to its deepest opened bracket stack; both feed the
    SLD601 complexity computation.

    Args:
        node: The function definition node to check.
        lines: The raw source lines of the enclosing module.
        bracket_depths: Mapping from line number to deepest bracket depth.

    Yields:
        One error per SLD601/SLD602/SLD701/SLD704 violation found.
    """
    yield from bad_name_errors_as(
        node.name, node.lineno, node.col_offset, FunctionError
    )
    yield from _check_is_predicate(node)
    complexity = get_function_complexity(node, lines, bracket_depths)
    if complexity.weight > MAX_FUNCTION_LINES:
        yield _error(node, format_sld601(node.name, complexity))
    arg_count = get_function_arg_count(node)
    if arg_count > MAX_FUNCTION_ARGS:
        yield _error(node, SLD602.format(node.name, arg_count, MAX_FUNCTION_ARGS))
