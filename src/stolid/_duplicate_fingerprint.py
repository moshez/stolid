# Merkle fingerprint for AST subtrees with scope-aware normalization.
#
# Includes the binder-discovery helpers that determine which names are bound
# in each scope frame (function, lambda, comprehension), so the fingerprint
# and the scope it computes against ship from the same module.

from __future__ import annotations

import ast
import functools
import hashlib
from dataclasses import dataclass
from typing import Iterable, Iterator, MutableSequence

from ._ast_inspection import (
    COMPREHENSION_NODES,
    FOR_LOOP_NODES,
    FUNCTION_DEF_NODES,
    NAMED_DEF_NODES,
    FunctionType,
    iter_args,
    iter_name_targets,
)
from ._duplicate_scope import Frame, ScopeStack

_SCOPE_NODES = NAMED_DEF_NODES + (ast.Lambda,)


def _target_names(target: ast.expr) -> Iterator[str]:
    for name in iter_name_targets(target):
        yield name.id


def _statement_binders(node: ast.AST) -> Iterator[str]:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            yield from _target_names(target)
    elif isinstance(node, ast.AnnAssign):
        yield from _target_names(node.target)
    elif isinstance(node, FOR_LOOP_NODES):
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
        if not isinstance(child, _SCOPE_NODES + COMPREHENSION_NODES):
            yield from _iter_body_nodes(child)


def _arg_names(arguments: ast.arguments) -> Iterator[str]:
    for arg in iter_args(arguments):
        yield arg.arg


def function_binders(node: FunctionType) -> Iterator[str]:
    """Yield the names bound in function ``node``'s frame in source order.

    Args:
        node: The function definition node whose bound names to yield.

    Yields:
        Each name bound in the function's frame, in source order.
    """
    yield from _arg_names(node.args)
    for body_node in _iter_body_nodes(node):
        yield from _statement_binders(body_node)


def lambda_binders(node: ast.Lambda) -> Iterator[str]:
    """Yield the names bound in lambda ``node``'s frame in source order.

    Args:
        node: The lambda node whose bound names to yield.

    Yields:
        Each name bound in the lambda's frame, in source order.
    """
    yield from _arg_names(node.args)


def comprehension_binders(
    node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
) -> Iterator[str]:
    """Yield the names bound in comprehension ``node``'s frame in source order.

    Args:
        node: The comprehension node whose bound names to yield.

    Yields:
        Each name bound in the comprehension's frame, in source order.
    """
    for generator in node.generators:
        yield from _target_names(generator.target)


_KEEP_LITERAL_KEYS: frozenset[tuple[type, object]] = frozenset(
    [
        (int, 0),
        (int, 1),
        (int, -1),
        (str, ""),
        (bytes, b""),
        (type(None), None),
        (bool, True),
        (bool, False),
    ]
)

_TYPE_TOKENS: dict[type, str] = {
    int: "<int>",
    float: "<float>",
    str: "<str>",
    bytes: "<bytes>",
    complex: "<complex>",
}


def _constant_signature(value: object) -> str:
    if (type(value), value) in _KEEP_LITERAL_KEYS:
        return repr(value)
    token = _TYPE_TOKENS.get(type(value))
    if token is not None:
        return token
    return f"<{type(value).__name__}>"


@functools.singledispatch
def _local_signature(node: ast.AST, scope: ScopeStack) -> str:
    del node, scope
    return ""


@_local_signature.register
def _(node: ast.Name, scope: ScopeStack) -> str:
    return scope.normalize(node.id)


@_local_signature.register
def _(node: ast.arg, scope: ScopeStack) -> str:
    return scope.normalize(node.arg)


@_local_signature.register
def _(node: ast.Constant, scope: ScopeStack) -> str:
    del scope
    return _constant_signature(node.value)


@_local_signature.register
def _(node: ast.Attribute, scope: ScopeStack) -> str:
    del scope
    return node.attr


@dataclass(frozen=True, slots=True, kw_only=True)
class Occurrence:
    """A single fingerprinted subtree.

    ``digest`` is the Merkle hash of the subtree, ``node`` is the AST node
    itself, and ``node_count`` is the total number of AST nodes it contains.

    Attributes:
        digest: The Merkle hash of the subtree.
        node: The AST node at the root of this subtree.
        node_count: Total number of AST nodes in the subtree.
    """

    digest: bytes
    node: ast.AST
    node_count: int


def _frame_from_names(names: Iterable[str]) -> Frame:
    frame = Frame()
    for n in names:
        frame.add(n)
    return frame


def _frame_for(node: ast.AST) -> Frame | None:
    if isinstance(node, FUNCTION_DEF_NODES):
        return _frame_from_names(function_binders(node))
    if isinstance(node, ast.Lambda):
        return _frame_from_names(lambda_binders(node))
    if isinstance(node, COMPREHENSION_NODES):
        return _frame_from_names(comprehension_binders(node))
    return None


def _hash_node(node: ast.AST, signature: str, subtree_digests: list[bytes]) -> bytes:
    digest = hashlib.blake2s(digest_size=16)
    digest.update(type(node).__name__.encode())
    digest.update(b"\x00")
    digest.update(signature.encode())
    for child in subtree_digests:
        digest.update(b"\x00")
        digest.update(child)
    return digest.digest()


def fingerprint(
    node: ast.AST,
    # ScopeStack is the duplicate detector's own scope machinery, co-designed
    # with this function and not an interface meant to be swapped; SLD802 does
    # not improve a concrete type that is the contract.
    scope: ScopeStack,  # noqa: SLD802
    collected: MutableSequence[Occurrence],
) -> tuple[bytes, int]:
    """Compute a Merkle hash of ``node`` using the current ``scope``.

    Records every visited subtree (and its digest) into ``collected``.
    Returns the digest and the node count of this subtree.

    Args:
        node: The AST node to fingerprint.
        scope: The current scope stack for name normalization.
        collected: Accumulator for all visited subtree occurrences.

    Returns:
        A tuple of the subtree digest and its total node count.
    """
    frame = _frame_for(node)
    if frame is not None:
        scope.enter(frame)
    subtree_digests: list[bytes] = []
    node_count = 1
    for child in ast.iter_child_nodes(node):
        sub_digest, child_count = fingerprint(child, scope, collected)
        subtree_digests.append(sub_digest)
        node_count += child_count
    signature = _local_signature(node, scope)
    digest = _hash_node(node, signature, subtree_digests)
    if frame is not None:
        scope.exit()
    collected.append(Occurrence(digest=digest, node=node, node_count=node_count))
    return digest, node_count
