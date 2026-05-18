# Variable-name similarity check (SLD703).
#
# Within each scope, flag any pair of bindings whose names differ by exactly
# one edit (insertion, deletion, or single-character substitution). The only
# exception is a single-letter name bound exclusively as a for-loop iteration
# target -- "for i, thing in ..." is allowed.

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._ast_inspection import NAMED_DEF_NODES, TUPLE_LIST_NODES

SLD703 = (
    "SLD703 Name '{}' differs from earlier '{}' by only one letter "
    "(rename to disambiguate)"
)


@dataclass(frozen=True, slots=True, kw_only=True)
class VariableNamingError:
    """A near-duplicate variable name violation.

    ``lineno`` and ``col_offset`` locate the offending binding; ``message``
    is the formatted SLD703 diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _Binding:
    name: str
    lineno: int
    col_offset: int
    is_loop: bool


_FUNCTION_LIKE = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
_NESTED_SCOPES = _FUNCTION_LIKE + (ast.ClassDef,) + _COMPREHENSIONS


def _bind(target: ast.expr, is_loop: bool) -> _Binding:
    assert isinstance(target, ast.Name)
    return _Binding(
        name=target.id,
        lineno=target.lineno,
        col_offset=target.col_offset,
        is_loop=is_loop,
    )


def _targets(target: ast.expr, is_loop: bool) -> Iterator[_Binding]:
    if isinstance(target, ast.Name):
        yield _bind(target, is_loop)
    elif isinstance(target, TUPLE_LIST_NODES):
        for elt in target.elts:
            yield from _targets(elt, is_loop)
    elif isinstance(target, ast.Starred):
        yield from _targets(target.value, is_loop)


def _import_bindings(node: ast.Import | ast.ImportFrom) -> Iterator[_Binding]:
    for alias in node.names:
        if alias.name == "*":  # noqa: SLD304
            continue
        bound = alias.asname or alias.name.split(".")[0]
        yield _Binding(
            name=bound,
            lineno=alias.lineno,
            col_offset=alias.col_offset,
            is_loop=False,
        )


def _named_binding(name: str, node: ast.stmt) -> _Binding:
    return _Binding(
        name=name, lineno=node.lineno, col_offset=node.col_offset, is_loop=False
    )


def _assign_bindings(node: ast.Assign) -> Iterator[_Binding]:
    for target in node.targets:
        yield from _targets(target, False)


def _withitem_bindings(node: ast.withitem) -> Iterator[_Binding]:
    if node.optional_vars is not None:
        yield from _targets(node.optional_vars, False)


def _except_bindings(node: ast.ExceptHandler) -> Iterator[_Binding]:
    if node.name is not None:
        yield _Binding(
            name=node.name,
            lineno=node.lineno,
            col_offset=node.col_offset,
            is_loop=False,
        )


def _statement_bindings(node: ast.AST) -> Iterator[_Binding]:
    if isinstance(node, ast.Assign):
        yield from _assign_bindings(node)
    elif isinstance(node, ast.AnnAssign):
        yield from _targets(node.target, False)
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        yield from _targets(node.target, True)
    elif isinstance(node, ast.NamedExpr):
        yield _bind(node.target, False)
    elif isinstance(node, NAMED_DEF_NODES):
        yield _named_binding(node.name, node)
    elif isinstance(node, ast.withitem):
        yield from _withitem_bindings(node)
    elif isinstance(node, ast.ExceptHandler):
        yield from _except_bindings(node)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        yield from _import_bindings(node)


def _to_binding(arg: ast.arg) -> _Binding:
    return _Binding(
        name=arg.arg, lineno=arg.lineno, col_offset=arg.col_offset, is_loop=False
    )


def _arg_bindings(arguments: ast.arguments) -> Iterator[_Binding]:
    for arg in arguments.posonlyargs + arguments.args + arguments.kwonlyargs:
        yield _to_binding(arg)
    if arguments.vararg is not None:
        yield _to_binding(arguments.vararg)
    if arguments.kwarg is not None:
        yield _to_binding(arguments.kwarg)


def _walk_local(parent: ast.AST) -> Iterator[ast.AST]:
    # Yield descendants of ``parent`` without entering nested scopes.
    for child in ast.iter_child_nodes(parent):
        yield child
        if not isinstance(child, _NESTED_SCOPES):
            yield from _walk_local(child)


def _scope_bindings(scope: ast.AST) -> Iterator[_Binding]:
    if isinstance(scope, _FUNCTION_LIKE):
        yield from _arg_bindings(scope.args)
    if isinstance(scope, _COMPREHENSIONS):
        for generator in scope.generators:
            yield from _targets(generator.target, True)
    for descendant in _walk_local(scope):
        yield from _statement_bindings(descendant)


def _all_scopes(tree: ast.Module) -> Iterator[ast.AST]:
    yield tree
    for node in ast.walk(tree):
        if isinstance(node, _NESTED_SCOPES):
            yield node


def _differ_by_one(left: str, right: str) -> bool:
    # Return True iff ``left`` and ``right`` differ by exactly one insertion,
    # deletion, or substitution AND the differing character is a letter (so
    # that ``SLD102``/``SLD103``, ``foo1``/``foo2``, etc. are not flagged).
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return _diff_by_substitution(left, right)
    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    return _diff_by_one_insertion(shorter, longer)


def _diff_by_substitution(left: str, right: str) -> bool:
    diff_position: int | None = None
    for index, (char_left, char_right) in enumerate(zip(left, right)):
        if char_left == char_right:
            continue
        if diff_position is not None:
            return False
        diff_position = index
    if diff_position is None:  # pragma: no cover
        return False
    return left[diff_position].isalpha() or right[diff_position].isalpha()


def _diff_by_one_insertion(shorter: str, longer: str) -> bool:
    # Walk both strings, allowing exactly one skipped char in ``longer``.
    short_index = 0
    long_index = 0
    inserted: str | None = None
    while long_index < len(longer):
        if short_index < len(shorter) and shorter[short_index] == longer[long_index]:
            short_index += 1
            long_index += 1
        elif inserted is not None:
            return False
        else:
            inserted = longer[long_index]
            long_index += 1
    if short_index != len(shorter):  # pragma: no cover
        return False
    assert inserted is not None
    return inserted.isalpha()


def _eligible_bindings(found: list[_Binding]) -> list[_Binding]:
    # Keep the first binding per name; drop single-letter names whose every
    # occurrence is a for-loop iteration target.
    first_seen: dict[str, _Binding] = {}
    has_non_loop: set[str] = set()
    for entry in found:
        if entry.name not in first_seen:
            first_seen[entry.name] = entry
        if not entry.is_loop:
            has_non_loop.add(entry.name)
    kept: list[_Binding] = []
    for name, entry in first_seen.items():
        only_loop = name not in has_non_loop
        if len(name) == 1 and only_loop:
            continue
        kept.append(entry)
    return kept


def _ordered_bindings(scope: ast.AST) -> list[_Binding]:
    eligible = _eligible_bindings(list(_scope_bindings(scope)))
    eligible.sort(key=lambda entry: (entry.lineno, entry.col_offset))
    return eligible


def _check_scope(scope: ast.AST) -> Iterator[VariableNamingError]:
    ordered = _ordered_bindings(scope)
    for index, later in enumerate(ordered):
        for earlier in ordered[:index]:
            if _differ_by_one(later.name, earlier.name):
                yield VariableNamingError(
                    lineno=later.lineno,
                    col_offset=later.col_offset,
                    message=SLD703.format(later.name, earlier.name),
                )
                break


def check_variable_naming(tree: ast.Module) -> Iterator[VariableNamingError]:
    """Yield SLD703 violations for every scope in ``tree``."""
    for scope in _all_scopes(tree):
        yield from _check_scope(scope)
