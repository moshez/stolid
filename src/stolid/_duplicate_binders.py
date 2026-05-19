# Discovery of binding sites within a scope frame.
#
# Walks the body of a function, lambda, comprehension, or generator and yields
# the names that are bound there, in source order. The walk does not descend
# into nested scopes (their bodies have their own frames).

from __future__ import annotations

import ast
from typing import Iterator

from ._ast_inspection import (
    COMPREHENSION_NODES,
    FunctionType,
    NAMED_DEF_NODES,
    SCOPE_NODES,
    iter_args,
    iter_name_targets,
)


def _target_names(target: ast.expr) -> Iterator[str]:
    for name in iter_name_targets(target):
        yield name.id


def _statement_binders(node: ast.AST) -> Iterator[str]:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            yield from _target_names(target)
    elif isinstance(node, ast.AnnAssign):
        yield from _target_names(node.target)
    elif isinstance(node, (ast.For, ast.AsyncFor)):  # noqa: SLD801
        yield from _target_names(node.target)
    elif isinstance(node, ast.NamedExpr):
        yield node.target.id
    elif isinstance(node, NAMED_DEF_NODES):
        yield node.name
    elif isinstance(node, ast.withitem):
        if node.optional_vars is not None:
            yield from _target_names(node.optional_vars)
    elif isinstance(node, ast.ExceptHandler):
        if node.name is not None:
            yield node.name


def _iter_body_nodes(parent: ast.AST) -> Iterator[ast.AST]:
    # Yield all descendants of ``parent`` without entering nested scopes.
    for child in ast.iter_child_nodes(parent):
        yield child
        if not isinstance(child, SCOPE_NODES + COMPREHENSION_NODES):
            yield from _iter_body_nodes(child)


def _arg_names(arguments: ast.arguments) -> Iterator[str]:
    for arg in iter_args(arguments):
        yield arg.arg


def function_binders(node: FunctionType) -> Iterator[str]:
    """Yield the names bound in function ``node``'s frame in source order."""
    yield from _arg_names(node.args)
    for body_node in _iter_body_nodes(node):
        yield from _statement_binders(body_node)


def lambda_binders(node: ast.Lambda) -> Iterator[str]:
    """Yield the names bound in lambda ``node``'s frame in source order."""
    yield from _arg_names(node.args)


def comprehension_binders(
    node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
) -> Iterator[str]:
    """Yield the names bound in comprehension ``node``'s frame in source order."""
    for generator in node.generators:
        yield from _target_names(generator.target)
