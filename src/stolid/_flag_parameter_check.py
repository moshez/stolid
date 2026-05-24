# Flag-parameter check (SLD609).
#
# A flag parameter is a parameter whose only role inside its function
# body is to select a branch -- it is tested in an if/while/ternary/
# match and never flows into a value. Functions that branch on a
# parameter are doing two jobs under one name; the remedy is to split
# them so the choice is lifted out of a parameter value and up into
# which function the caller calls.
#
# The analysis is intraprocedural by design. A parameter that is
# passed onward to a callee counts as a data use, so a pure forwarder
# is not flagged here; the callee gets flagged on its own once it has
# a branching parameter. After splitting, the forwarder has to choose
# which split to call, and on the next run its parameter has become
# branch-only and gets flagged in turn.

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._ast_inspection import COLLECTION_NODES, FUNCTION_DEF_NODES, FunctionType

SLD609 = (
    "SLD609 Parameter '{}' of '{}' is used only as a branch condition "
    "(split the function instead of passing a flag)"
)

_SKIP_NAMES = frozenset({"self", "cls"})


@dataclass(frozen=True, slots=True, kw_only=True)
class FlagParameterError:
    """A flag-parameter violation.

    ``lineno`` and ``col_offset`` locate the offending parameter;
    ``message`` is the formatted SLD609 diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _Counts:
    control: dict[str, int]
    data: dict[str, int]


def _candidate_args(func: FunctionType) -> list[ast.arg]:
    # Positional and keyword parameters worth examining: *args/**kwargs
    # and the conventional self/cls are skipped.
    arguments = func.args
    every = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
    return [a for a in every if a.arg not in _SKIP_NAMES]


def _empty_counts(names: list[str]) -> _Counts:
    return _Counts(
        control={n: 0 for n in names},
        data={n: 0 for n in names},
    )


def _record_name(node: ast.Name, slot: dict[str, int]) -> None:
    if not isinstance(node.ctx, ast.Load):
        return
    if node.id not in slot:
        return
    slot[node.id] += 1


def _visit_if_like(node: ast.If | ast.While, counts: _Counts) -> None:
    _visit(node.test, True, counts)
    for stmt in node.body:
        _visit(stmt, False, counts)
    for stmt in node.orelse:
        _visit(stmt, False, counts)


def _visit_ifexp(node: ast.IfExp, counts: _Counts) -> None:
    _visit(node.test, True, counts)
    _visit(node.body, False, counts)
    _visit(node.orelse, False, counts)


def _visit_assert(node: ast.Assert, counts: _Counts) -> None:
    _visit(node.test, True, counts)
    if node.msg is not None:
        _visit(node.msg, False, counts)


def _visit_match(node: ast.Match, counts: _Counts) -> None:
    _visit(node.subject, True, counts)
    for case in node.cases:
        if case.guard is not None:
            _visit(case.guard, True, counts)
        for stmt in case.body:
            _visit(stmt, False, counts)


def _visit_comprehension(node: ast.comprehension, counts: _Counts) -> None:
    _visit(node.iter, False, counts)
    for clause in node.ifs:
        _visit(clause, True, counts)


def _visit_call(node: ast.Call, counts: _Counts) -> None:
    _visit(node.func, False, counts)
    for argument in node.args:
        _visit(argument, False, counts)
    for keyword in node.keywords:
        _visit(keyword.value, False, counts)


def _visit_attribute(node: ast.Attribute, counts: _Counts) -> None:
    _visit(node.value, False, counts)


def _visit_subscript(node: ast.Subscript, counts: _Counts) -> None:
    _visit(node.value, False, counts)
    _visit(node.slice, False, counts)


def _visit_binop(node: ast.BinOp, counts: _Counts) -> None:
    _visit(node.left, False, counts)
    _visit(node.right, False, counts)


_NESTED_SCOPES = FUNCTION_DEF_NODES + (ast.Lambda,)


def _dispatch_control(node: ast.AST, counts: _Counts) -> bool:
    if isinstance(node, (ast.If, ast.While)):
        _visit_if_like(node, counts)
        return True
    if isinstance(node, ast.IfExp):
        _visit_ifexp(node, counts)
        return True
    if isinstance(node, ast.Assert):
        _visit_assert(node, counts)
        return True
    if isinstance(node, ast.Match):
        _visit_match(node, counts)
        return True
    if isinstance(node, ast.comprehension):
        _visit_comprehension(node, counts)
        return True
    return False


def _dispatch_expr(node: ast.AST, counts: _Counts) -> bool:
    if isinstance(node, ast.Call):
        _visit_call(node, counts)
        return True
    if isinstance(node, ast.Attribute):
        _visit_attribute(node, counts)
        return True
    if isinstance(node, ast.Subscript):
        _visit_subscript(node, counts)
        return True
    if isinstance(node, ast.BinOp):
        _visit_binop(node, counts)
        return True
    return False


def _visit(node: ast.AST, in_condition: bool, counts: _Counts) -> None:
    if isinstance(node, ast.Name):
        slot = counts.control if in_condition else counts.data
        _record_name(node, slot)
        return
    if isinstance(node, _NESTED_SCOPES):
        return
    if isinstance(node, ast.Compare):
        _visit_compare(node, in_condition, counts)
        return
    if _dispatch_control(node, counts) or _dispatch_expr(node, counts):
        return
    for child in ast.iter_child_nodes(node):
        _visit(child, in_condition, counts)


def _visit_compare(node: ast.Compare, in_condition: bool, counts: _Counts) -> None:
    # The left operand is the value being tested; the comparators on the
    # right are values compared against and are always data. Whether the
    # left operand counts as a branch test depends on the operator:
    # ``==``/``!=`` against anything is a flag-style discriminator, and
    # ``in``/``not in`` is one only against a literal (or tuple of
    # literals). ``x in runtime_value`` makes ``x`` a search needle -- a
    # data use, like indexing -- not a branch flag.
    left_in_condition = in_condition and _left_is_branch_test(
        node.ops[0], node.comparators[0]
    )
    _visit(node.left, left_in_condition, counts)
    for comparator in node.comparators:
        _visit(comparator, False, counts)


def _is_literal_membership_rhs(node: ast.expr) -> bool:
    # A compile-time literal or a tuple/list/set of literals.
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, COLLECTION_NODES):
        return all(isinstance(elt, ast.Constant) for elt in node.elts)
    return False


def _left_is_branch_test(op: ast.cmpop, rhs: ast.expr) -> bool:
    if isinstance(op, (ast.In, ast.NotIn)):
        return _is_literal_membership_rhs(rhs)
    return True


def _function_errors(node: FunctionType) -> Iterator[FlagParameterError]:
    params = _candidate_args(node)
    if not params:
        return
    counts = _empty_counts([p.arg for p in params])
    for stmt in node.body:
        _visit(stmt, False, counts)
    for p in params:
        name = p.arg
        if counts.control[name] >= 1 and counts.data[name] == 0:
            yield FlagParameterError(
                lineno=p.lineno,
                col_offset=p.col_offset,
                message=SLD609.format(name, node.name),
            )


def check_flag_parameters(tree: ast.Module) -> Iterator[FlagParameterError]:
    """Yield SLD609 violations from ``tree``."""
    for node in ast.walk(tree):
        if isinstance(node, FUNCTION_DEF_NODES):
            yield from _function_errors(node)
