# Walk a module's public API surface and yield every annotation expression
# that callers are committed to.
#
# "Public" is decided per definition by its *name*, never by the module it
# lives in: a name without a leading underscore (dunders excepted) is part
# of the API surface even inside a private (``_``-prefixed) module, because
# callers can still import and depend on it. The public surface points are:
#
# - public top-level functions and async functions (parameter and return
#   annotations);
# - public top-level classes, plus their public methods and public
#   class-level annotated attributes (recursing into public nested classes);
# - public top-level annotated assignments.
#
# Only private *members* are skipped -- private-named functions, classes,
# attributes, and members nested in public classes -- because those are not
# part of the API surface regardless of where they live.

from __future__ import annotations

import ast
from typing import Iterator

from ._ast_inspection import FUNCTION_DEF_NODES, FunctionType, is_dunder_name


def _is_private_name(name: str) -> bool:
    if not name.startswith("_"):
        return False
    return not is_dunder_name(name)


def _function_annotations(node: FunctionType) -> Iterator[ast.expr]:
    args = node.args
    parameters = (
        args.posonlyargs
        + args.args
        + args.kwonlyargs
        + ([args.vararg] if args.vararg is not None else [])
        + ([args.kwarg] if args.kwarg is not None else [])
    )
    for entry in parameters:
        if entry.annotation is not None:
            yield entry.annotation
    if node.returns is not None:
        yield node.returns


def _ann_assign_annotation(stmt: ast.AnnAssign) -> Iterator[ast.expr]:
    target = stmt.target
    if isinstance(target, ast.Name) and _is_private_name(target.id):
        return
    yield stmt.annotation


def _body_annotations(body: list[ast.stmt]) -> Iterator[ast.expr]:
    for stmt in body:
        yield from _statement_annotations(stmt)


def _statement_annotations(stmt: ast.stmt) -> Iterator[ast.expr]:
    if isinstance(stmt, FUNCTION_DEF_NODES):
        if _is_private_name(stmt.name):
            return
        yield from _function_annotations(stmt)
    elif isinstance(stmt, ast.ClassDef):
        if _is_private_name(stmt.name):
            return
        yield from _body_annotations(stmt.body)
    elif isinstance(stmt, ast.AnnAssign):
        yield from _ann_assign_annotation(stmt)


def iter_public_annotations(tree: ast.Module) -> Iterator[ast.expr]:
    """Yield every annotation expression on the public surface of ``tree``.

    Every module is walked: public-named members are part of the API
    surface even in a private module, so only private *members* are
    skipped.
    """
    yield from _body_annotations(tree.body)
