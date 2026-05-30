# Weighted-line complexity scoring (SLD601) and argument counting (SLD602).

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Mapping, Sequence

from ._ast_inspection import FunctionType

# SLD601 counts a *weighted* line budget, not raw lines. Each line's weight is
# COMPLEXITY_FACTOR ** (indent_depth + max(0, bracket_depth - 1)), where
# indent_depth is the line's indent past the function body's baseline (one
# step = INDENT_WIDTH spaces), and bracket_depth is the deepest stack of
# brackets opened on the line itself. Blank lines weigh 0; comment-only
# lines weigh 1 unweighted. A flat function still costs ~1 per line, so
# the budget reads roughly like a line count for unnested code.
#
# Factor 1.3 was chosen for symmetry with the spirit of cyclomatic
# complexity while staying tolerable: depth-4 code costs ~2.86x per line,
# so a budget of 30 fits ~10 lines of consistently 4-deep code -- enough
# room for typical guard/branch nesting, harsh enough to push staircase
# code toward extraction or early returns. INDENT_WIDTH is hardcoded to 4
# in line with PEP 8 and stolid's opinionated stance on style.
COMPLEXITY_FACTOR = 1.3
INDENT_WIDTH = 4


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionComplexity:
    """Weighted-line complexity score for a function body.

    ``weight`` is the sum of per-line weights. ``heaviest_line`` is the line
    number of the most expensive body line; ``heaviest_weight`` is its
    weight, and ``heaviest_indent`` / ``heaviest_brackets`` are the indent
    depth and bracket depth that produced it.

    Attributes:
        weight: The summed per-line weight of the function body.
        heaviest_line: The line number of the most expensive body line.
        heaviest_weight: The weight of the heaviest line.
        heaviest_indent: The indent depth that produced the heaviest line.
        heaviest_brackets: The bracket depth that produced the heaviest line.
    """

    weight: float
    heaviest_line: int
    heaviest_weight: float
    heaviest_indent: int
    heaviest_brackets: int


@dataclass(frozen=True, slots=True, kw_only=True)
class _LineCost:
    lineno: int
    weight: float
    indent: int
    brackets: int


def _line_cost(
    lineno: int, line: str, baseline_indent: int, bracket_depth: int
) -> _LineCost:
    stripped = line.lstrip()
    if not stripped:
        return _LineCost(lineno=lineno, weight=0.0, indent=0, brackets=bracket_depth)
    if stripped.startswith("#"):
        return _LineCost(lineno=lineno, weight=1.0, indent=0, brackets=bracket_depth)
    indent_chars = len(line) - len(stripped)
    indent = max(0, (indent_chars - baseline_indent) // INDENT_WIDTH)
    weight = COMPLEXITY_FACTOR ** (indent + max(0, bracket_depth - 1))
    return _LineCost(
        lineno=lineno, weight=weight, indent=indent, brackets=bracket_depth
    )


def _iter_line_costs(
    node: FunctionType, lines: Sequence[str], bracket_depths: Mapping[int, int]
) -> Iterator[_LineCost]:
    first_line = node.body[0].lineno
    last_line = node.body[-1].end_lineno or node.body[-1].lineno
    baseline = node.body[0].col_offset
    for lineno in range(first_line, last_line + 1):
        yield _line_cost(
            lineno, lines[lineno - 1], baseline, bracket_depths.get(lineno, 0)
        )


def _cost_weight(cost: _LineCost) -> float:
    return cost.weight


def get_function_complexity(
    node: FunctionType, lines: Sequence[str], bracket_depths: Mapping[int, int]
) -> FunctionComplexity:
    """Return the weighted-line complexity of function ``node``.

    ``lines`` is the source of the enclosing module and ``bracket_depths``
    maps each line number to its deepest opened bracket stack. See
    ``_constants.py`` for the formula and rationale behind
    ``COMPLEXITY_FACTOR`` and ``INDENT_WIDTH``.

    Args:
        node: The function definition to score.
        lines: The source lines of the enclosing module.
        bracket_depths: Map of line number to its deepest opened bracket stack.

    Returns:
        The weighted-line complexity breakdown for ``node``.
    """
    assert node.body, "Function body cannot be empty in valid Python"
    costs = list(_iter_line_costs(node, lines, bracket_depths))
    heaviest = max(costs, key=_cost_weight)
    return FunctionComplexity(
        weight=sum(c.weight for c in costs),
        heaviest_line=heaviest.lineno,
        heaviest_weight=heaviest.weight,
        heaviest_indent=heaviest.indent,
        heaviest_brackets=heaviest.brackets,
    )


def get_function_arg_count(node: FunctionType) -> int:
    """Return the argument count of function ``node`` (``self``/``cls`` excluded).

    Args:
        node: The function definition whose arguments to count.

    Returns:
        The number of declared arguments, excluding ``self``/``cls``.
    """
    args = node.args
    total = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
    if args.args and args.args[0].arg in ("self", "cls"):  # noqa: SLD304
        total -= 1
    return total
