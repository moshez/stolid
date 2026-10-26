# Check for module imports not at the top of the module.

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator, TypeGuard

IMPORT_NODES = (ast.Import, ast.ImportFrom)

# Temporal's sandbox requires third-party imports to be wrapped in
# ``with workflow.unsafe.imports_passed_through():`` so they are not
# re-imported inside the workflow sandbox. The block is an import region,
# so the imports directly inside it are exempt, but the block itself must
# still sit with the rest of the header.
PASSTHROUGH_SUFFIX = ("workflow", "unsafe", "imports_passed_through")


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportPlacementError:
    """An import-placement violation.

    ``lineno`` and ``col_offset`` locate the misplaced import.

    Attributes:
        lineno: Line number of the misplaced import.
        col_offset: Column offset of the misplaced import.
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


def _dotted_name(node: ast.expr) -> tuple[str, ...]:
    if isinstance(node, ast.Attribute):
        return _dotted_name(node.value) + (node.attr,)
    if isinstance(node, ast.Name):
        return (node.id,)
    return ()


def _called_name(item: ast.withitem) -> tuple[str, ...]:
    manager = item.context_expr
    if isinstance(manager, ast.Call):
        return _dotted_name(manager.func)
    return ()


def _is_passthrough_item(item: ast.withitem) -> bool:
    called = _called_name(item)
    return called[-len(PASSTHROUGH_SUFFIX) :] == PASSTHROUGH_SUFFIX


def _is_passthrough_block(stmt: ast.stmt) -> TypeGuard[ast.With]:
    if not isinstance(stmt, ast.With):
        return False
    return any(map(_is_passthrough_item, stmt.items))


def _is_import_region(stmt: ast.stmt) -> bool:
    return isinstance(stmt, IMPORT_NODES) or _is_passthrough_block(stmt)


def _is_header_stmt(stmt: ast.stmt, index: int) -> bool:
    if _is_import_region(stmt):
        return True
    return index == 0 and _is_module_docstring(stmt)


def _check_module_body(tree: ast.Module) -> Iterator[ImportPlacementError]:
    seen_non_header = False
    for index, stmt in enumerate(tree.body):
        if _is_import_region(stmt) and seen_non_header:
            yield _error(stmt)
        if not _is_header_stmt(stmt, index):
            seen_non_header = True


def _walk_imports(stmt: ast.stmt) -> Iterator[ImportPlacementError]:
    for child in ast.walk(stmt):
        if isinstance(child, IMPORT_NODES):
            yield _error(child)


def _check_passthrough_body(stmt: ast.With) -> Iterator[ImportPlacementError]:
    for child in stmt.body:
        if isinstance(child, IMPORT_NODES):
            continue
        yield from _walk_imports(child)


def _check_nested_imports(tree: ast.Module) -> Iterator[ImportPlacementError]:
    for stmt in tree.body:
        if isinstance(stmt, IMPORT_NODES):
            continue
        if _is_passthrough_block(stmt):
            yield from _check_passthrough_body(stmt)
            continue
        yield from _walk_imports(stmt)


def check_import_placement(tree: ast.Module) -> Iterator[ImportPlacementError]:
    """Yield errors for imports in ``tree`` that are not at the top of the module.

    A module-level ``with workflow.unsafe.imports_passed_through():`` block
    counts as part of the header: the imports directly inside it are
    exempt, and the block itself is reported only when it comes after
    non-header code.

    Args:
        tree: The module AST to check for misplaced imports.

    Yields:
        One error per import statement not at the top of the module.
    """
    yield from _check_module_body(tree)
    yield from _check_nested_imports(tree)
