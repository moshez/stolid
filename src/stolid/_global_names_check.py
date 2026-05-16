"""Check for module-level names that shadow builtins/typing/stdlib."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._constants import SLD702
from ._reserved_names import reserved_name_source


@dataclass(frozen=True, slots=True, kw_only=True)
class GlobalNameError:
    lineno: int
    col_offset: int
    message: str


def _names_from_target(target: ast.expr) -> Iterator[tuple[str, int, int]]:
    if isinstance(target, ast.Name):
        yield target.id, target.lineno, target.col_offset
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _names_from_target(elt)


def _check_name(name: str, lineno: int, col_offset: int) -> Iterator[GlobalNameError]:
    source = reserved_name_source(name)
    if source is not None:
        yield GlobalNameError(
            lineno=lineno,
            col_offset=col_offset,
            message=SLD702.format(name, source),
        )


def check_global_names(tree: ast.Module) -> Iterator[GlobalNameError]:
    """Yield errors for module-level definitions that shadow reserved names."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield from _check_name(node.name, node.lineno, node.col_offset)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for name, lineno, col in _names_from_target(target):
                    yield from _check_name(name, lineno, col)
        elif isinstance(node, ast.AnnAssign):
            for name, lineno, col in _names_from_target(node.target):
                yield from _check_name(name, lineno, col)
