# Walk a module's public API surface and yield every annotation expression
# that callers are committed to.
#
# "Public" means the module is not private (filename does not start with a
# single underscore; ``__init__.py`` is treated as public). Inside a public
# module, the public surface points are:
#
# - public top-level functions and async functions (parameter and return
#   annotations);
# - public top-level classes, plus their public methods and public
#   class-level annotated attributes (recursing into public nested classes);
# - public top-level annotated assignments.
#
# Private modules, private top-level classes, and private members of public
# classes are skipped entirely: they are not part of the API surface.

from __future__ import annotations

import ast
import os
from typing import Iterator

from ._ast_inspection import FUNCTION_DEF_NODES, FunctionType, is_dunder_name


def _is_private_name(name: str) -> bool:
    if not name.startswith("_"):
        return False
    return not is_dunder_name(name)


def is_public_module(filename: str) -> bool:
    """Return True iff the file at ``filename`` is a public module."""
    stem = os.path.basename(filename)[:-3]
    if stem == "__init__":
        return True
    return not _is_private_name(stem)


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


def _statement_annotations(stmt: ast.stmt) -> Iterator[ast.expr]:
    if isinstance(stmt, FUNCTION_DEF_NODES):
        if _is_private_name(stmt.name):
            return
        yield from _function_annotations(stmt)
    elif isinstance(stmt, ast.ClassDef):
        if _is_private_name(stmt.name):
            return
        yield from _class_member_annotations(stmt)
    elif isinstance(stmt, ast.AnnAssign):
        yield from _ann_assign_annotation(stmt)


def _class_member_annotations(node: ast.ClassDef) -> Iterator[ast.expr]:
    for child in node.body:
        yield from _statement_annotations(child)


def _top_level_annotations(tree: ast.Module) -> Iterator[ast.expr]:
    for stmt in tree.body:
        yield from _statement_annotations(stmt)


def iter_public_annotations(tree: ast.Module, filename: str) -> Iterator[ast.expr]:
    """Yield every annotation expression on the public surface of ``tree``.

    ``filename`` selects whether the module itself is public. Private
    modules yield nothing.
    """
    if not is_public_module(filename):
        return
    yield from _top_level_annotations(tree)
