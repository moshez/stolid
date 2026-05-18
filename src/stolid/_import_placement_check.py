"""Check for module imports not at the top of the module."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

IMPORT_NODES = (ast.Import, ast.ImportFrom)


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportPlacementError:
    """An import-placement violation.

    ``lineno`` and ``col_offset`` locate the misplaced import.
    """

    lineno: int
    col_offset: int


def _is_module_docstring(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.Expr):
        return False
    if not isinstance(stmt.value, ast.Constant):
        return False
    return isinstance(stmt.value.value, str)


def _error(node: ast.stmt) -> ImportPlacementError:
    return ImportPlacementError(lineno=node.lineno, col_offset=node.col_offset)


def _is_header_stmt(stmt: ast.stmt, index: int) -> bool:
    if isinstance(stmt, IMPORT_NODES):
        return True
    return index == 0 and _is_module_docstring(stmt)


def _check_module_body(tree: ast.Module) -> Iterator[ImportPlacementError]:
    seen_non_header = False
    for index, stmt in enumerate(tree.body):
        if isinstance(stmt, IMPORT_NODES) and seen_non_header:
            yield _error(stmt)
        if not _is_header_stmt(stmt, index):
            seen_non_header = True


def _check_nested_imports(tree: ast.Module) -> Iterator[ImportPlacementError]:
    for stmt in tree.body:
        if isinstance(stmt, IMPORT_NODES):
            continue
        for child in ast.walk(stmt):
            if isinstance(child, IMPORT_NODES):
                yield _error(child)


def check_import_placement(tree: ast.Module) -> Iterator[ImportPlacementError]:
    """Yield errors for imports in ``tree`` that are not at the top of the module."""
    yield from _check_module_body(tree)
    yield from _check_nested_imports(tree)
