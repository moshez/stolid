"""Interestingness scoring for duplicate-detector subtrees.

The score filters out structurally trivial subtrees. A subtree must score at
least :data:`stolid._constants.MIN_CLONE_SCORE` to qualify as a clone.
"""

from __future__ import annotations

import ast
import builtins

from ._duplicate_binders import COMPREHENSION_NODES

_BUILTIN_NAMES: frozenset[str] = frozenset(dir(builtins))


def _call_score(node: ast.Call) -> float:
    func = node.func
    if isinstance(func, ast.Name) and func.id in _BUILTIN_NAMES:
        return 0.0
    return 0.5


_CONTROL_FLOW = (ast.If, ast.For, ast.While, ast.Try, ast.With)
_OPERATIONS = (ast.BinOp, ast.BoolOp, ast.Compare)


def node_score(node: ast.AST) -> float:
    """Return the interestingness contribution of a single AST node."""
    if isinstance(node, ast.Call):
        return _call_score(node)
    if isinstance(node, ast.Attribute):
        return 2.0 if isinstance(node.ctx, ast.Load) else 0.0
    if isinstance(node, _CONTROL_FLOW):
        return 2.0
    if isinstance(node, COMPREHENSION_NODES):
        return 2.0
    if isinstance(node, _OPERATIONS):
        return 1.0
    return 0.0


def subtree_score(node: ast.AST) -> float:
    """Return the summed interestingness score of every descendant of ``node``."""
    return sum(node_score(child) for child in ast.walk(node))
