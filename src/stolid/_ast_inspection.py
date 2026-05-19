# Helper functions for AST inspection.

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, TypeVar

from ._constants import BAD_NAME_WORDS, COMPLEXITY_FACTOR, INDENT_WIDTH

FUNCTION_DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
FunctionType = ast.FunctionDef | ast.AsyncFunctionDef
NAMED_DEF_NODES = FUNCTION_DEF_NODES + (ast.ClassDef,)
TUPLE_LIST_NODES = (ast.Tuple, ast.List)
LAMBDA_FUNCTION_NODES = FUNCTION_DEF_NODES + (ast.Lambda,)
SCOPE_NODES = NAMED_DEF_NODES + (ast.Lambda,)
COMPREHENSION_NODES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def iter_name_targets(target: ast.expr) -> Iterator[ast.Name]:
    """Yield every ``ast.Name`` reachable from assignment ``target``.

    Recurses through tuple/list targets and ``Starred`` wrappers; other
    expression shapes (attribute, subscript) yield nothing.
    """
    if isinstance(target, ast.Name):
        yield target
    elif isinstance(target, TUPLE_LIST_NODES):
        for elt in target.elts:
            yield from iter_name_targets(elt)
    elif isinstance(target, ast.Starred):
        yield from iter_name_targets(target.value)


def iter_args(arguments: ast.arguments) -> Iterator[ast.arg]:
    """Yield every ``ast.arg`` in ``arguments`` (positional, kw-only, *args, **kwargs)."""
    yield from arguments.posonlyargs
    yield from arguments.args
    yield from arguments.kwonlyargs
    if arguments.vararg is not None:
        yield arguments.vararg
    if arguments.kwarg is not None:
        yield arguments.kwarg


def is_name_id(node: ast.AST, name: str) -> bool:
    """Return True iff ``node`` is ``ast.Name`` with id ``name``."""
    return isinstance(node, ast.Name) and node.id == name


def is_name_among(node: ast.AST, names: Iterable[str]) -> bool:
    """Return True iff ``node`` is ``ast.Name`` whose id is in ``names``."""
    return isinstance(node, ast.Name) and node.id in names


def is_attribute_attr(node: ast.AST, attr: str) -> bool:
    """Return True iff ``node`` is ``ast.Attribute`` with ``.attr`` == ``attr``."""
    return isinstance(node, ast.Attribute) and node.attr == attr


def is_attribute_in(node: ast.AST, attrs: Iterable[str]) -> bool:
    """Return True iff ``node`` is ``ast.Attribute`` whose attr is in ``attrs``."""
    return isinstance(node, ast.Attribute) and node.attr in attrs


def get_base_name(node: ast.expr) -> str | None:
    """Return the base-class name expressed by ``node``, or ``None`` if unknown."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return get_base_name(node.value)
    return None


def is_dataclass_decorator(node: ast.expr) -> bool:
    """Return True iff ``node`` is a ``@dataclass`` or ``@dataclasses.dataclass``."""
    if is_name_id(node, "dataclass"):
        return True
    if is_attribute_attr(node, "dataclass"):
        return True
    if isinstance(node, ast.Call):
        return is_dataclass_decorator(node.func)
    return False


def is_dunder_name(name: str) -> bool:
    """Return True iff ``name`` is a dunder identifier (``__xxx__``)."""
    return name.startswith("__") and name.endswith("__")


def module_name_from_filename(filename: str) -> str | None:
    """Return the module basename of ``filename`` (no ``.py``), or ``None``.

    Returns ``None`` if ``filename`` is empty or does not end in ``.py``.
    Does not filter dunder modules; callers that care apply that check.
    """
    if not filename:
        return None
    base = os.path.basename(filename)
    if not base.endswith(".py"):
        return None
    return base[:-3]


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionComplexity:
    """Weighted-line complexity score for a function body.

    ``weight`` is the sum of per-line weights. ``heaviest_line`` is the line
    number of the most expensive body line; ``heaviest_weight`` is its
    weight, and ``heaviest_indent`` / ``heaviest_brackets`` are the indent
    depth and bracket depth that produced it.
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
    node: FunctionType, lines: list[str], bracket_depths: dict[int, int]
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
    node: FunctionType, lines: list[str], bracket_depths: dict[int, int]
) -> FunctionComplexity:
    """Return the weighted-line complexity of function ``node``.

    ``lines`` is the source of the enclosing module and ``bracket_depths``
    maps each line number to its deepest opened bracket stack. See
    ``_constants.py`` for the formula and rationale behind
    ``COMPLEXITY_FACTOR`` and ``INDENT_WIDTH``.
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
    """Return the argument count of function ``node`` (``self``/``cls`` excluded)."""
    args = node.args
    total = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
    if args.args and args.args[0].arg in ("self", "cls"):  # noqa: SLD304
        total -= 1
    return total


def _add_matching_aliases(
    aliases: list[ast.alias], wanted: tuple[str, ...], target: set[str]
) -> None:
    for alias in aliases:
        if alias.name in wanted:
            target.add(alias.asname or alias.name)


_PATCH_NAMES_WANTED = ("patch", "patch.object")
_ABSTRACT_WANTED = ("abstractmethod",)
_CAST_WANTED = ("cast",)


def collect_imports(tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
    """Return names bound in ``tree`` that alias patch, abstractmethod, and cast."""
    patch_names: set[str] = set()
    abstractmethod_names: set[str] = {"abstractmethod"}
    cast_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module in ("unittest.mock", "mock"):  # noqa: SLD304
            _add_matching_aliases(node.names, _PATCH_NAMES_WANTED, patch_names)
        if node.module == "abc":  # noqa: SLD304
            _add_matching_aliases(node.names, _ABSTRACT_WANTED, abstractmethod_names)
        if node.module == "typing":  # noqa: SLD304
            _add_matching_aliases(node.names, _CAST_WANTED, cast_names)
    return patch_names, abstractmethod_names, cast_names


# Pattern to split identifiers into words:
# - Split on underscores
# - Split on CamelCase boundaries (lowercase followed by uppercase)
_WORD_SPLIT_PATTERN = re.compile(r"_|(?<=[a-z])(?=[A-Z])")


def split_identifier_into_words(name: str) -> list[str]:
    """Split identifier ``name`` into its words and return them.

    Splits on underscores and CamelCase boundaries.

    Examples:
        "DiskUtil" -> ["Disk", "Util"]
        "disk_util" -> ["disk", "util"]
        "Futile" -> ["Futile"]
        "MyHelperClass" -> ["My", "Helper", "Class"]
    """
    return [word for word in _WORD_SPLIT_PATTERN.split(name) if word]


def find_bad_name_word(name: str) -> str | None:
    """Return the first forbidden word in identifier ``name``, or ``None`` if absent."""
    parts = split_identifier_into_words(name)
    for word in parts:
        if word.lower() in BAD_NAME_WORDS:
            return word.lower()
    return None


SLD701 = "SLD701 Name '{}' contains forbidden word '{}' (use a more specific name)"


@dataclass(frozen=True, slots=True, kw_only=True)
class BadNameError:
    """A bad-name violation.

    ``lineno`` and ``col_offset`` locate the offending name; ``message``
    is the formatted SLD701 diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


def bad_name_errors(name: str, lineno: int, col_offset: int) -> Iterator[BadNameError]:
    """Yield SLD701 if ``name`` contains a forbidden word.

    ``lineno`` and ``col_offset`` locate the offending name.
    """
    bad_word = find_bad_name_word(name)
    if bad_word is not None:
        yield BadNameError(
            lineno=lineno, col_offset=col_offset, message=SLD701.format(name, bad_word)
        )


_E = TypeVar("_E")


def bad_name_errors_as(
    name: str, lineno: int, col_offset: int, factory: Callable[..., _E]
) -> Iterator[_E]:
    """Yield ``factory(...)``-wrapped SLD701 errors for ``name``.

    ``factory`` is called with ``lineno``, ``col_offset``, and ``message``
    keyword arguments; use it to lift the shared ``BadNameError`` into
    each module's local error dataclass.
    """
    for err in bad_name_errors(name, lineno, col_offset):
        yield factory(lineno=err.lineno, col_offset=err.col_offset, message=err.message)
