# Merkle fingerprint for AST subtrees with scope-aware normalization.

from __future__ import annotations

import ast
import functools
import hashlib
from dataclasses import dataclass
from typing import Iterable

from ._ast_inspection import FUNCTION_DEF_NODES
from ._duplicate_binders import (
    COMPREHENSION_NODES,
    comprehension_binders,
    function_binders,
    lambda_binders,
)
from ._duplicate_scope import Frame, ScopeStack

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
    """

    digest: bytes
    node: ast.AST
    node_count: int


def _frame_from_names(names: Iterable[str]) -> Frame:
    frame = Frame()
    for name in names:
        frame.add(name)
    return frame


def _frame_for(node: ast.AST) -> Frame | None:
    if isinstance(node, FUNCTION_DEF_NODES):
        return _frame_from_names(function_binders(node))
    if isinstance(node, ast.Lambda):
        return _frame_from_names(lambda_binders(node))
    if isinstance(node, COMPREHENSION_NODES):
        return _frame_from_names(comprehension_binders(node))
    return None


def _hash_node(node: ast.AST, signature: str, child_digests: list[bytes]) -> bytes:
    digest = hashlib.blake2s(digest_size=16)
    digest.update(type(node).__name__.encode())
    digest.update(b"\x00")
    digest.update(signature.encode())
    for child in child_digests:
        digest.update(b"\x00")
        digest.update(child)
    return digest.digest()


def fingerprint(
    node: ast.AST, scope: ScopeStack, collected: list[Occurrence]
) -> tuple[bytes, int]:
    """Compute a Merkle hash of ``node`` using the current ``scope``.

    Records every visited subtree (and its digest) into ``collected``.
    Returns the digest and the node count of this subtree.
    """
    frame = _frame_for(node)
    if frame is not None:
        scope.enter(frame)
    child_digests: list[bytes] = []
    node_count = 1
    for child in ast.iter_child_nodes(node):
        child_digest, child_count = fingerprint(child, scope, collected)
        child_digests.append(child_digest)
        node_count += child_count
    signature = _local_signature(node, scope)
    digest = _hash_node(node, signature, child_digests)
    if frame is not None:
        scope.exit()
    collected.append(Occurrence(digest=digest, node=node, node_count=node_count))
    return digest, node_count
