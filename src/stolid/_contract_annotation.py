# Walk a public annotation expression and yield contract-violation diagnostics.
#
# The classifier is recursive over the annotation AST. The high-level rule
# is: a public annotation may name a primitive (``int``, ``str``, ...), a
# closed type (``Literal``, ``Enum``, ``NewType``), or a contract
# (``Protocol``, ``ABC``, ``TypedDict``, ``NamedTuple``) -- and may compose
# those through abstract containers (``Mapping``, ``Sequence``, ...) or
# unions. Naming an open concrete class is SLD802; using a concrete
# builtin container (``list``/``dict``/``set``/``frozenset``) is SLD803;
# using a variadic tuple (``tuple[X, ...]``) is SLD804.
#
# Names that do not resolve to any workspace-defined class are treated as
# allowed: third-party and stdlib references are out of scope for a
# workspace-only scanner.

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum, auto
from typing import AbstractSet, Iterator

from ._ast_inspection import get_base_name


class ContractViolation(Enum):
    """The three kinds of contract violation reported on a public annotation.

    Attributes:
        CONCRETE_CLASS: A workspace-defined concrete class used in a public annotation.
        CONCRETE_CONTAINER: A builtin concrete container (``list``, ``dict``, …) used.
        VARIADIC_TUPLE: A variadic ``tuple[X, ...]`` form used in a public annotation.
    """

    CONCRETE_CLASS = auto()
    CONCRETE_CONTAINER = auto()
    VARIADIC_TUPLE = auto()


@dataclass(frozen=True, slots=True, kw_only=True)
class ContractError:
    """A single contract violation found in a public annotation.

    ``lineno`` and ``col_offset`` locate the offending sub-expression;
    ``kind`` selects the SLD80x category; ``name`` is the offending
    identifier (the concrete class, the concrete container, or the empty
    string for a variadic tuple).

    Attributes:
        lineno: Line number of the offending sub-expression.
        col_offset: Column offset of the offending sub-expression.
        kind: The SLD80x violation category.
        name: The offending identifier, or empty string for a variadic tuple.
    """

    lineno: int
    col_offset: int
    kind: ContractViolation
    name: str


_PRIMITIVES: frozenset[str] = frozenset(
    {"int", "float", "str", "bool", "bytes", "complex", "bytearray", "None", "object"}
)

_CONCRETE_CONTAINERS: frozenset[str] = frozenset({"list", "dict", "set", "frozenset"})

# Abstract containers and other typing-module forms that take type parameters
# and are themselves contracts. Recursing into their parameters is enough.
_ABSTRACT_GENERICS: frozenset[str] = frozenset(
    {
        "Mapping",
        "MutableMapping",
        "Sequence",
        "MutableSequence",
        "AbstractSet",
        "MutableSet",
        "Iterable",
        "Iterator",
        "AsyncIterable",
        "AsyncIterator",
        "Awaitable",
        "Coroutine",
        "Generator",
        "AsyncGenerator",
        "Collection",
        "Container",
        "Reversible",
        "Hashable",
        "Sized",
        "ContextManager",
        "AsyncContextManager",
        "Optional",
        "Union",
        "ClassVar",
        "Final",
    }
)

# Typing forms that need their own per-subscript handling.
_TUPLE_NAMES: frozenset[str] = frozenset({"tuple", "Tuple"})
_LITERAL_NAMES: frozenset[str] = frozenset({"Literal"})
_ANNOTATED_NAMES: frozenset[str] = frozenset({"Annotated"})
_CALLABLE_NAMES: frozenset[str] = frozenset({"Callable"})
_TYPE_NAMES: frozenset[str] = frozenset({"type", "Type"})


def _is_ellipsis(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is Ellipsis


def _slice_elements(node: ast.expr) -> list[ast.expr]:
    if isinstance(node, ast.Tuple):
        return list(node.elts)
    return [node]


def _classify_name(
    node: ast.expr, name: str, concrete_names: AbstractSet[str]
) -> Iterator[ContractError]:
    if name in _PRIMITIVES or name in _ABSTRACT_GENERICS:
        return
    if name in _CONCRETE_CONTAINERS:
        yield ContractError(
            lineno=node.lineno,
            col_offset=node.col_offset,
            kind=ContractViolation.CONCRETE_CONTAINER,
            name=name,
        )
        return
    if name in concrete_names:
        yield ContractError(
            lineno=node.lineno,
            col_offset=node.col_offset,
            kind=ContractViolation.CONCRETE_CLASS,
            name=name,
        )


def _classify_tuple_subscript(
    node: ast.Subscript, concrete_names: AbstractSet[str]
) -> Iterator[ContractError]:
    elements = _slice_elements(node.slice)
    if len(elements) == 2 and _is_ellipsis(elements[1]):
        yield ContractError(
            lineno=node.lineno,
            col_offset=node.col_offset,
            kind=ContractViolation.VARIADIC_TUPLE,
            name="",
        )
        yield from classify_annotation(elements[0], concrete_names)
        return
    for child in elements:
        yield from classify_annotation(child, concrete_names)


def _classify_callable_subscript(
    node: ast.Subscript, concrete_names: AbstractSet[str]
) -> Iterator[ContractError]:
    elements = _slice_elements(node.slice)
    for child in elements:
        if isinstance(child, ast.List):
            for inner in child.elts:
                yield from classify_annotation(inner, concrete_names)
            continue
        if _is_ellipsis(child):
            continue
        yield from classify_annotation(child, concrete_names)


def _classify_annotated_subscript(
    node: ast.Subscript, concrete_names: AbstractSet[str]
) -> Iterator[ContractError]:
    elements = _slice_elements(node.slice)
    assert elements  # a subscript slice always has at least one element
    yield from classify_annotation(elements[0], concrete_names)


def _classify_slice(
    node: ast.Subscript, concrete_names: AbstractSet[str]
) -> Iterator[ContractError]:
    for child in _slice_elements(node.slice):
        yield from classify_annotation(child, concrete_names)


def _classify_subscript(
    node: ast.Subscript, concrete_names: AbstractSet[str]
) -> Iterator[ContractError]:
    head = get_base_name(node.value)
    if head in _LITERAL_NAMES:
        return
    if head in _ANNOTATED_NAMES:
        yield from _classify_annotated_subscript(node, concrete_names)
        return
    if head in _TUPLE_NAMES:
        yield from _classify_tuple_subscript(node, concrete_names)
        return
    if head in _CALLABLE_NAMES:
        yield from _classify_callable_subscript(node, concrete_names)
        return
    if head in _TYPE_NAMES:
        yield from _classify_slice(node, concrete_names)
        return
    yield from classify_annotation(node.value, concrete_names)
    yield from _classify_slice(node, concrete_names)


def _classify_binop(
    node: ast.BinOp, concrete_names: AbstractSet[str]
) -> Iterator[ContractError]:
    if isinstance(node.op, ast.BitOr):  # pragma: no branch
        yield from classify_annotation(node.left, concrete_names)
        yield from classify_annotation(node.right, concrete_names)


def classify_annotation(
    node: ast.expr, concrete_names: AbstractSet[str]
) -> Iterator[ContractError]:
    """Yield SLD80x violations found in annotation ``node``.

    ``concrete_names`` is the set of workspace-defined names that are
    classified as concrete (not Protocol/ABC/TypedDict/NamedTuple/Enum).
    Unknown names are treated as allowed.

    Args:
        node: The annotation AST expression to classify.
        concrete_names: Workspace-defined names classified as concrete.

    Yields:
        Each contract violation found in the annotation.
    """
    if isinstance(node, ast.Constant):
        return
    if isinstance(node, ast.Name):
        yield from _classify_name(node, node.id, concrete_names)
        return
    if isinstance(node, ast.Attribute):
        yield from _classify_name(node, node.attr, concrete_names)
        return
    if isinstance(node, ast.Subscript):
        yield from _classify_subscript(node, concrete_names)
        return
    if isinstance(node, ast.BinOp):  # pragma: no branch
        yield from _classify_binop(node, concrete_names)
