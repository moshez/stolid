# Syntactic classification of a ``class X(...):`` definition.
#
# The classifier answers the question "is this class a contract (a Protocol,
# ABC, TypedDict, NamedTuple, Enum, or a data-only dataclass) that callers
# may safely depend on, or a concrete implementation that callers must not
# be coupled to?". The answer drives SLD802/SLD803/SLD804: public
# annotations may name contracts, primitives, and abstract containers, but
# not concrete classes.
#
# Detection is purely syntactic (bases, decorators, and body shape), with
# no type-checker invocation. Names match the standard library spelling;
# aliases are not resolved here -- the workspace symbol table handles them.

from __future__ import annotations

import ast
from enum import Enum, auto

from ._ast_inspection import get_base_name, has_dataclass_decorator


class ClassKind(Enum):
    """The contract-vs-concrete classification of a ``class X(...):`` statement."""

    PROTOCOL = auto()
    ABSTRACT = auto()
    TYPED_DICT = auto()
    NAMED_TUPLE = auto()
    ENUMERATION = auto()
    DATA_RECORD = auto()
    CONCRETE = auto()


_PROTOCOL_BASES: frozenset[str] = frozenset({"Protocol"})
_ABSTRACT_BASES: frozenset[str] = frozenset({"ABC"})
_TYPED_DICT_BASES: frozenset[str] = frozenset({"TypedDict"})
_NAMED_TUPLE_BASES: frozenset[str] = frozenset({"NamedTuple"})
_ENUM_BASES: frozenset[str] = frozenset(
    {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"}
)

_KIND_BY_BASE: tuple[tuple[frozenset[str], ClassKind], ...] = (
    (_PROTOCOL_BASES, ClassKind.PROTOCOL),
    (_ABSTRACT_BASES, ClassKind.ABSTRACT),
    (_TYPED_DICT_BASES, ClassKind.TYPED_DICT),
    (_NAMED_TUPLE_BASES, ClassKind.NAMED_TUPLE),
    (_ENUM_BASES, ClassKind.ENUMERATION),
)


def _is_docstring(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _is_public_field(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.AnnAssign):
        return False
    target = stmt.target
    return isinstance(target, ast.Name) and not target.id.startswith("_")


def _is_data_record_body(body: list[ast.stmt]) -> bool:
    return all(_is_docstring(stmt) or _is_public_field(stmt) for stmt in body)


def _is_data_record(node: ast.ClassDef) -> bool:
    return has_dataclass_decorator(node) and _is_data_record_body(node.body)


def classify_class(node: ast.ClassDef) -> ClassKind:
    """Return the contract-vs-concrete classification of class ``node``."""
    base_names = {get_base_name(base) for base in node.bases}
    for marker_bases, kind in _KIND_BY_BASE:
        if base_names & marker_bases:
            return kind
    if _is_data_record(node):
        return ClassKind.DATA_RECORD
    return ClassKind.CONCRETE
