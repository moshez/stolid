"""Discovery of binding sites within a scope frame.

Walks the body of a function, lambda, comprehension, or generator and yields
the names that are bound there, in source order. The walk does not descend
into nested scopes (their bodies have their own frames).
"""

from __future__ import annotations

import ast
from typing import Iterator

from ._ast_inspection import FunctionType, NAMED_DEF_NODES, TUPLE_LIST_NODES


def _names_in_target(target: ast.expr) -> Iterator[str]:
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, TUPLE_LIST_NODES):
        for elt in target.elts:
            yield from _names_in_target(elt)
    elif isinstance(target, ast.Starred):
        yield from _names_in_target(target.value)


SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
COMPREHENSION_NODES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _statement_binders(node: ast.AST) -> Iterator[str]:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            yield from _names_in_target(target)
    elif isinstance(node, ast.AnnAssign):
        yield from _names_in_target(node.target)
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        yield from _names_in_target(node.target)
    elif isinstance(node, ast.NamedExpr):
        yield node.target.id
    elif isinstance(node, NAMED_DEF_NODES):
        yield node.name
    elif isinstance(node, ast.withitem):
        if node.optional_vars is not None:
            yield from _names_in_target(node.optional_vars)
    elif isinstance(node, ast.ExceptHandler):
        if node.name is not None:
            yield node.name


def _iter_body_nodes(parent: ast.AST) -> Iterator[ast.AST]:
    """Yield all descendants of ``parent`` without entering nested scopes."""
    for child in ast.iter_child_nodes(parent):
        yield child
        if not isinstance(child, SCOPE_NODES + COMPREHENSION_NODES):
            yield from _iter_body_nodes(child)


def _argument_names(args: ast.arguments) -> Iterator[str]:
    for arg in args.posonlyargs + args.args + args.kwonlyargs:
        yield arg.arg
    if args.vararg is not None:
        yield args.vararg.arg
    if args.kwarg is not None:
        yield args.kwarg.arg


def function_binders(node: FunctionType) -> Iterator[str]:
    """Yield the names bound in function ``node``'s frame in source order."""
    yield from _argument_names(node.args)
    for body_node in _iter_body_nodes(node):
        yield from _statement_binders(body_node)


def lambda_binders(node: ast.Lambda) -> Iterator[str]:
    """Yield the names bound in lambda ``node``'s frame in source order."""
    yield from _argument_names(node.args)


def comprehension_binders(
    node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
) -> Iterator[str]:
    """Yield the names bound in comprehension ``node``'s frame in source order."""
    for generator in node.generators:
        yield from _names_in_target(generator.target)
