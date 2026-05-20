# Function-shape checks: argument count and complexity (SLD602/SLD601).
# Also checks function names for forbidden words (SLD701).

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._ast_inspection import (
    FunctionType,
    bad_name_errors_as,
    get_function_arg_count,
    get_function_complexity,
)
from ._check_runner import format_sld601
from ._constants import MAX_FUNCTION_ARGS, MAX_FUNCTION_LINES

SLD602 = "SLD602 Function '{}' has {} arguments (limit: {})"


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionError:
    """A function-rule violation.

    ``lineno`` and ``col_offset`` locate the offending node; ``message``
    is the formatted SLD601/SLD602/SLD701 diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


def _error(node: ast.stmt | ast.expr, message: str) -> FunctionError:
    return FunctionError(
        lineno=node.lineno, col_offset=node.col_offset, message=message
    )


def check_function(
    node: FunctionType, lines: list[str], bracket_depths: dict[int, int]
) -> Iterator[FunctionError]:
    """Yield SLD601/SLD602/SLD701 violations for function ``node``.

    ``lines`` is the enclosing module source and ``bracket_depths`` maps
    each line number to its deepest opened bracket stack; both feed the
    SLD601 complexity computation.
    """
    yield from bad_name_errors_as(
        node.name, node.lineno, node.col_offset, FunctionError
    )
    complexity = get_function_complexity(node, lines, bracket_depths)
    if complexity.weight > MAX_FUNCTION_LINES:
        yield _error(node, format_sld601(node.name, complexity))
    arg_count = get_function_arg_count(node)
    if arg_count > MAX_FUNCTION_ARGS:
        yield _error(node, SLD602.format(node.name, arg_count, MAX_FUNCTION_ARGS))
