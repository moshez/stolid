# Checks that flag stringly-typed code that should use an enum.

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._constants import SLD304, SLD305, SLD306, SLD307

MULTI_COMPARE_THRESHOLD = 2
MODULE_COUNT_THRESHOLD = 3
MATCH_CASE_THRESHOLD = 2

_TRACKABLE_NAMELIKE = (ast.Name, ast.Attribute, ast.Subscript)
_COLLECTION_NODES = (ast.Tuple, ast.List, ast.Set)
_SCOPE_BOUNDARY_NODES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
)
_FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass(frozen=True, slots=True, kw_only=True)
class StringEnumError:
    """A stringly-typed code violation.

    ``lineno`` and ``col_offset`` locate the offending literal; ``message``
    is the formatted SLD30x diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


def _as_str_literal(node: ast.AST) -> tuple[ast.Constant, str] | None:
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


def _iter_scope_nodes(stmts: list[ast.stmt]) -> Iterator[ast.AST]:
    # Yield all descendants of ``stmts`` without crossing nested scopes.
    for stmt in stmts:
        yield from _walk_no_scope(stmt)


def _walk_no_scope(node: ast.AST) -> Iterator[ast.AST]:
    yield node
    if isinstance(node, _SCOPE_BOUNDARY_NODES):
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
    nodes: list[ast.expr],
) -> list[tuple[ast.Constant, str]] | None:
    literals: list[tuple[ast.Constant, str]] = []
    for node in nodes:
        literal = _as_str_literal(node)
        if literal is None:
            return None
        literals.append(literal)
    return literals


def _track_in_pair(
    left: ast.expr,
    right: ast.expr,
    bucket: dict[str, dict[str, list[ast.Constant]]],
) -> None:
    if not isinstance(left, _TRACKABLE_NAMELIKE):
        return
    if not isinstance(right, _COLLECTION_NODES):
        return
    literals = _collect_str_literals(right.elts)
    if literals is None:
        return
    key = ast.unparse(left)
    for node, value in literals:
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
        for nodes in str_map.values():
            for node in nodes:
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
        if isinstance(node, _FUNCTION_NODES):
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
    for value, nodes in bucket.items():
        if len(nodes) < MODULE_COUNT_THRESHOLD:
            continue
        for node in nodes:
            yield StringEnumError(
                lineno=node.lineno,
                col_offset=node.col_offset,
                message=SLD306.format(value, len(nodes)),
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


def check_string_enum(tree: ast.Module) -> Iterator[StringEnumError]:
    """Yield errors in ``tree`` for stringly-typed code that should use an enum."""
    yield from _check_multi_compare(tree)
    yield from _check_match_statements(tree)
    yield from _check_module_string_count(tree)
    yield from _check_literal_annotations(tree)
