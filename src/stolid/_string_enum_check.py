# Checks that flag stringly-typed code that should use an enum.

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._ast_inspection import FUNCTION_DEF_NODES, SCOPE_NODES, get_base_name

SLD304 = (
    "SLD304 Expression '{}' compared against multiple distinct string literals "
    "(use an enum)"
)
SLD305 = "SLD305 match case uses string literal '{}' (use an enum)"
SLD306 = (
    "SLD306 String literal '{}' appears in {} equality contexts in this module "
    "(use an enum)"
)
SLD307 = "SLD307 Literal[...] annotation uses string literal '{}' (use an enum)"
SLD308 = (
    "SLD308 Module-level string constant has identifier value '{}' "
    "(define peers as Enum members)"
)
SLD309 = (
    "SLD309 Enum member has identifier-shaped string value '{}' "
    "(use auto() to avoid a stringly-typed backdoor)"
)

MULTI_COMPARE_THRESHOLD = 2
MODULE_COUNT_THRESHOLD = 3
MATCH_CASE_THRESHOLD = 2
PEER_CONSTANT_THRESHOLD = 2
_ENUM_BASES = frozenset({"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"})

_TRACKABLE_NAMELIKE = (ast.Name, ast.Attribute, ast.Subscript)
_COLLECTION_NODES = (ast.Tuple, ast.List, ast.Set)


@dataclass(frozen=True, slots=True, kw_only=True)
class StringEnumError:
    """A stringly-typed code violation.

    ``lineno`` and ``col_offset`` locate the offending literal; ``message``
    is the formatted SLD30x diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


_StrLiteral = tuple[ast.Constant, str] | None


def _as_str_literal(node: ast.AST) -> _StrLiteral:
    # Return (node, value) when node is a string-literal Constant.
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node, node.value
    return None


def _compare_pairs(
    node: ast.Compare,
) -> Iterator[tuple[ast.expr, ast.cmpop, ast.expr]]:
    operands = [node.left, *node.comparators]
    for index, op in enumerate(node.ops):
        yield operands[index], op, operands[index + 1]


def _match_pattern_strings(
    pattern: ast.pattern,
) -> Iterator[tuple[ast.Constant, str]]:
    if isinstance(pattern, ast.MatchValue):
        literal = _as_str_literal(pattern.value)
        if literal is not None:
            yield literal
    elif isinstance(pattern, ast.MatchOr):
        for sub in pattern.patterns:
            yield from _match_pattern_strings(sub)


def _iter_scope_nodes(body: list[ast.stmt]) -> Iterator[ast.AST]:
    # Yield all descendants of ``body`` without crossing nested scopes.
    for stmt in body:
        yield from _walk_no_scope(stmt)


def _walk_no_scope(node: ast.AST) -> Iterator[ast.AST]:
    yield node
    if isinstance(node, SCOPE_NODES):
        return
    for child in ast.iter_child_nodes(node):
        yield from _walk_no_scope(child)


def _track_eq_pair(
    left: ast.expr,
    right: ast.expr,
    bucket: dict[str, dict[str, list[ast.Constant]]],
) -> None:
    for name_side, str_side in ((left, right), (right, left)):
        if not isinstance(name_side, _TRACKABLE_NAMELIKE):
            continue
        literal = _as_str_literal(str_side)
        if literal is None:
            continue
        node, value = literal
        key = ast.unparse(name_side)
        bucket.setdefault(key, {}).setdefault(value, []).append(node)
        return


def _collect_str_literals(
    members: list[ast.expr],
) -> list[tuple[ast.Constant, str]] | None:
    found: list[tuple[ast.Constant, str]] = []
    for node in members:
        literal = _as_str_literal(node)
        if literal is None:
            return None
        found.append(literal)
    return found


def _track_in_pair(
    left: ast.expr,
    right: ast.expr,
    bucket: dict[str, dict[str, list[ast.Constant]]],
) -> None:
    if not isinstance(left, _TRACKABLE_NAMELIKE):
        return
    if not isinstance(right, _COLLECTION_NODES):
        return
    found = _collect_str_literals(right.elts)
    if found is None:
        return
    key = ast.unparse(left)
    for node, value in found:
        bucket.setdefault(key, {}).setdefault(value, []).append(node)


def _track_compare(
    node: ast.Compare, bucket: dict[str, dict[str, list[ast.Constant]]]
) -> None:
    for left, op, right in _compare_pairs(node):
        if isinstance(op, (ast.Eq, ast.NotEq)):
            _track_eq_pair(left, right, bucket)
        elif isinstance(op, (ast.In, ast.NotIn)):
            _track_in_pair(left, right, bucket)


def _emit_multi_compare(
    bucket: dict[str, dict[str, list[ast.Constant]]],
) -> Iterator[StringEnumError]:
    for name_key, str_map in bucket.items():
        if len(str_map) < MULTI_COMPARE_THRESHOLD:
            continue
        for group in str_map.values():
            for node in group:
                yield StringEnumError(
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    message=SLD304.format(name_key),
                )


def _check_scope_compares(stmts: list[ast.stmt]) -> Iterator[StringEnumError]:
    bucket: dict[str, dict[str, list[ast.Constant]]] = {}
    for node in _iter_scope_nodes(stmts):
        if isinstance(node, ast.Compare):
            _track_compare(node, bucket)
    yield from _emit_multi_compare(bucket)


def _check_multi_compare(tree: ast.Module) -> Iterator[StringEnumError]:
    yield from _check_scope_compares(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, FUNCTION_DEF_NODES):
            yield from _check_scope_compares(node.body)


def _check_match_cases(match_node: ast.Match) -> Iterator[StringEnumError]:
    found: list[tuple[ast.Constant, str]] = []
    for case in match_node.cases:
        found.extend(_match_pattern_strings(case.pattern))
    if len(found) < MATCH_CASE_THRESHOLD:
        return
    for node, value in found:
        yield StringEnumError(
            lineno=node.lineno,
            col_offset=node.col_offset,
            message=SLD305.format(value),
        )


def _check_match_statements(tree: ast.Module) -> Iterator[StringEnumError]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Match):
            yield from _check_match_cases(node)


def _strings_from_compare(
    node: ast.Compare,
) -> Iterator[tuple[ast.Constant, str]]:
    for left, op, right in _compare_pairs(node):
        if isinstance(op, (ast.Eq, ast.NotEq)):
            for side in (left, right):
                literal = _as_str_literal(side)
                if literal is not None:
                    yield literal
        elif isinstance(op, (ast.In, ast.NotIn)):
            if isinstance(right, _COLLECTION_NODES):
                for elt in right.elts:
                    literal = _as_str_literal(elt)
                    if literal is not None:
                        yield literal


def _collect_equality_strings(
    tree: ast.Module,
) -> Iterator[tuple[ast.Constant, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            yield from _strings_from_compare(node)
        elif isinstance(node, ast.MatchValue):
            literal = _as_str_literal(node.value)
            if literal is not None:
                yield literal


def _check_module_string_count(tree: ast.Module) -> Iterator[StringEnumError]:
    bucket: dict[str, list[ast.Constant]] = {}
    for node, value in _collect_equality_strings(tree):
        bucket.setdefault(value, []).append(node)
    for value, group in bucket.items():
        if len(group) < MODULE_COUNT_THRESHOLD:
            continue
        for node in group:
            yield StringEnumError(
                lineno=node.lineno,
                col_offset=node.col_offset,
                message=SLD306.format(value, len(group)),
            )


def _is_literal_subscript(node: ast.Subscript) -> bool:
    target = node.value
    if isinstance(target, ast.Name):
        return target.id == "Literal"
    if isinstance(target, ast.Attribute):
        return target.attr == "Literal"
    return False


def _strings_in_literal_slice(
    slice_node: ast.expr,
) -> Iterator[tuple[ast.Constant, str]]:
    if isinstance(slice_node, ast.Tuple):
        for elt in slice_node.elts:
            literal = _as_str_literal(elt)
            if literal is not None:
                yield literal
        return
    literal = _as_str_literal(slice_node)
    if literal is not None:
        yield literal


def _check_literal_annotations(tree: ast.Module) -> Iterator[StringEnumError]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not _is_literal_subscript(node):
            continue
        for const, value in _strings_in_literal_slice(node.slice):
            yield StringEnumError(
                lineno=const.lineno,
                col_offset=const.col_offset,
                message=SLD307.format(value),
            )


def _assignment_string_value(stmt: ast.stmt) -> _StrLiteral:
    # If ``stmt`` is a single-target ``NAME = "literal"`` (with or without an
    # annotation), return ``(Constant, value)``; else return ``None``.
    if isinstance(stmt, ast.Assign):
        if len(stmt.targets) != 1:
            return None
        if not isinstance(stmt.targets[0], ast.Name):
            return None
        return _as_str_literal(stmt.value)
    if isinstance(stmt, ast.AnnAssign):
        if not isinstance(stmt.target, ast.Name):
            return None
        if stmt.value is None:
            return None
        return _as_str_literal(stmt.value)
    return None


def _check_module_string_constants(tree: ast.Module) -> Iterator[StringEnumError]:
    found: list[tuple[ast.Constant, str]] = []
    for stmt in tree.body:
        result = _assignment_string_value(stmt)
        if result is None:
            continue
        _, value = result
        if not value.isidentifier():
            continue
        found.append(result)
    if len(found) < PEER_CONSTANT_THRESHOLD:
        return
    for node, value in found:
        yield StringEnumError(
            lineno=node.lineno,
            col_offset=node.col_offset,
            message=SLD308.format(value),
        )


def _is_enum_class(node: ast.ClassDef) -> bool:
    return any(get_base_name(base) in _ENUM_BASES for base in node.bases)


def _enum_classes(tree: ast.Module) -> Iterator[ast.ClassDef]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_enum_class(node):
            yield node


def _identifier_string_members(
    node: ast.ClassDef,
) -> list[tuple[ast.Constant, str]]:
    # Return the class's string-valued members if *all* of them are valid
    # identifiers; else an empty list.
    members: list[tuple[ast.Constant, str]] = []
    for stmt in node.body:
        result = _assignment_string_value(stmt)
        if result is None:
            continue
        if not result[1].isidentifier():
            return []
        members.append(result)
    return members


def _check_enum_identifier_values(tree: ast.Module) -> Iterator[StringEnumError]:
    for node in _enum_classes(tree):
        for const, value in _identifier_string_members(node):
            yield StringEnumError(
                lineno=const.lineno,
                col_offset=const.col_offset,
                message=SLD309.format(value),
            )


def check_string_enum(tree: ast.Module) -> Iterator[StringEnumError]:
    """Yield errors in ``tree`` for stringly-typed code that should use an enum."""
    yield from _check_multi_compare(tree)
    yield from _check_match_statements(tree)
    yield from _check_module_string_count(tree)
    yield from _check_literal_annotations(tree)
    yield from _check_module_string_constants(tree)
    yield from _check_enum_identifier_values(tree)
