"""Flake8 plugin enforcing stolid conventions."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._constants import (
    ALLOWED_BASES,
    SLD102,
    SLD201,
    SLD202,
    SLD301,
    SLD302,
    SLD303,
    SLD401,
    SLD501,
    SLD502,
    SLD503,
    SLD601,
    SLD602,
    SLD603,
    SLD604,
    SLD701,
    MAX_CLASS_METHODS,
    MAX_FUNCTION_ARGS,
    MAX_FUNCTION_LINES,
    MAX_MODULE_LINES,
)
from ._ast_inspection import (
    collect_imports,
    find_bad_name_word,
    get_base_name,
    get_class_method_count,
    get_dataclass_keywords,
    get_function_arg_count,
    get_function_line_count,
    is_classmethod_or_staticmethod,
    is_dataclass_decorator,
    is_dunder_method,
    is_method,
    is_property_method,
    method_accesses_private_state,
    method_accesses_self,
)

__all__ = ["Checker"]


@dataclass(frozen=True, slots=True, kw_only=True)
class Error:
    """Represents a lint error."""

    lineno: int
    col_offset: int
    message: str


def _check_node(
    node: ast.AST,
    patch_names: set[str],
    abstractmethod_names: set[str],
) -> Iterator[Error]:
    """Check a single AST node for violations."""
    if isinstance(node, ast.ImportFrom):
        yield from _check_import_from(node)
    elif isinstance(node, ast.Attribute):
        yield from _check_attribute(node)
    elif isinstance(node, ast.Name):
        yield from _check_name(node)
    elif isinstance(node, ast.ClassDef):
        yield from _check_class(node, abstractmethod_names)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        yield from _check_function(node)
    elif isinstance(node, ast.Call):
        yield from _check_call(node, patch_names)
    elif isinstance(node, ast.With):
        yield from _check_with(node, patch_names)


def _check_import_from(node: ast.ImportFrom) -> Iterator[Error]:
    """Check ImportFrom statements."""
    if node.module in ("unittest.mock", "mock"):
        for alias in node.names:
            if alias.name == "patch":
                yield Error(
                    lineno=node.lineno, col_offset=node.col_offset, message=SLD102
                )

    if node.module == "abc":
        for alias in node.names:
            if alias.name == "ABC":
                yield Error(
                    lineno=node.lineno, col_offset=node.col_offset, message=SLD201
                )
            if alias.name == "abstractmethod":
                yield Error(
                    lineno=node.lineno, col_offset=node.col_offset, message=SLD202
                )


def _check_attribute(node: ast.Attribute) -> Iterator[Error]:
    """Check attribute access for patch usage."""
    if node.attr == "patch":
        if isinstance(node.value, ast.Attribute):
            if node.value.attr == "mock":
                yield Error(
                    lineno=node.lineno, col_offset=node.col_offset, message=SLD102
                )
        elif isinstance(node.value, ast.Name):  # pragma: no branch
            if node.value.id == "mock":
                yield Error(
                    lineno=node.lineno, col_offset=node.col_offset, message=SLD102
                )


def _check_name(node: ast.Name) -> Iterator[Error]:
    """Check name references."""
    return
    yield  # Make this a generator


def _check_call(node: ast.Call, patch_names: set[str]) -> Iterator[Error]:
    """Check function calls."""
    if isinstance(node.func, ast.Name):
        if node.func.id in patch_names:
            yield Error(lineno=node.lineno, col_offset=node.col_offset, message=SLD102)
    elif isinstance(node.func, ast.Attribute):  # pragma: no branch
        if node.func.attr == "object":
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id in patch_names:
                    yield Error(
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        message=SLD102,
                    )
            elif isinstance(node.func.value, ast.Attribute):  # pragma: no branch
                if node.func.value.attr == "patch":
                    yield Error(
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        message=SLD102,
                    )


def _check_with(node: ast.With, patch_names: set[str]) -> Iterator[Error]:
    """Check with statements for patch context managers."""
    for item in node.items:
        if isinstance(item.context_expr, ast.Call):
            call = item.context_expr
            if isinstance(call.func, ast.Name):
                if call.func.id in patch_names:
                    yield Error(
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        message=SLD102,
                    )


def _check_bad_name(name: str, lineno: int, col_offset: int) -> Iterator[Error]:
    """Check if a name contains a forbidden word."""
    bad_word = find_bad_name_word(name)
    if bad_word is not None:
        yield Error(
            lineno=lineno,
            col_offset=col_offset,
            message=SLD701.format(name, bad_word),
        )


def _check_class_decorators(
    node: ast.ClassDef,
    abstractmethod_names: set[str],
) -> Iterator[Error]:
    """Check class decorators for violations."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id in abstractmethod_names:
            yield Error(
                lineno=decorator.lineno,
                col_offset=decorator.col_offset,
                message=SLD202,
            )


def _check_class_bases(node: ast.ClassDef) -> Iterator[Error]:
    """Check class base classes for inheritance violations."""
    for base in node.bases:
        base_name = get_base_name(base)
        if base_name is not None and base_name not in ALLOWED_BASES:
            yield Error(
                lineno=base.lineno,
                col_offset=base.col_offset,
                message=SLD401.format(node.name, base_name),
            )


def _check_dataclass_flags(
    node: ast.ClassDef, keywords: dict[str, bool]
) -> Iterator[Error]:
    """Check dataclass decorator flags."""
    if not keywords.get("frozen", False):
        yield Error(
            lineno=node.lineno,
            col_offset=node.col_offset,
            message=SLD501.format(node.name),
        )
    if not keywords.get("slots", False):
        yield Error(
            lineno=node.lineno,
            col_offset=node.col_offset,
            message=SLD502.format(node.name),
        )
    if not keywords.get("kw_only", False):
        yield Error(
            lineno=node.lineno,
            col_offset=node.col_offset,
            message=SLD503.format(node.name),
        )


def _check_class(node: ast.ClassDef, abstractmethod_names: set[str]) -> Iterator[Error]:
    """Check class definitions."""
    is_dataclass = False
    dataclass_keywords: dict[str, bool] = {}

    for decorator in node.decorator_list:
        if is_dataclass_decorator(decorator):
            is_dataclass = True
            dataclass_keywords = get_dataclass_keywords(decorator)

    yield from _check_bad_name(node.name, node.lineno, node.col_offset)
    yield from _check_class_decorators(node, abstractmethod_names)
    yield from _check_class_bases(node)

    if is_dataclass:
        yield from _check_dataclass_flags(node, dataclass_keywords)

    method_count = get_class_method_count(node)
    if method_count > MAX_CLASS_METHODS:
        yield Error(
            lineno=node.lineno,
            col_offset=node.col_offset,
            message=SLD603.format(node.name, method_count, MAX_CLASS_METHODS),
        )

    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield from _check_method_in_class(child, abstractmethod_names)


def _check_abstractmethod_decorator(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    abstractmethod_names: set[str],
) -> Iterator[Error]:
    """Check method decorators for @abstractmethod."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id in abstractmethod_names:
            yield Error(
                lineno=decorator.lineno,
                col_offset=decorator.col_offset,
                message=SLD202,
            )
        elif (
            isinstance(decorator, ast.Attribute) and decorator.attr == "abstractmethod"
        ):
            yield Error(
                lineno=decorator.lineno,
                col_offset=decorator.col_offset,
                message=SLD202,
            )


def _check_method_naming(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterator[Error]:
    """Check method naming conventions."""
    if node.name == "__init__":
        yield Error(lineno=node.lineno, col_offset=node.col_offset, message=SLD301)
    if node.name.startswith("_") and not is_dunder_method(node.name):
        yield Error(
            lineno=node.lineno,
            col_offset=node.col_offset,
            message=SLD302.format(node.name),
        )


def _check_method_in_class(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    abstractmethod_names: set[str],
) -> Iterator[Error]:
    """Check a method within a class context."""
    yield from _check_abstractmethod_decorator(node, abstractmethod_names)

    if not is_method(node) or is_classmethod_or_staticmethod(node):
        return

    yield from _check_method_naming(node)

    if is_dunder_method(node.name) or is_property_method(node):
        return

    if method_accesses_self(node) and not method_accesses_private_state(node):
        yield Error(
            lineno=node.lineno,
            col_offset=node.col_offset,
            message=SLD303.format(node.name),
        )


def _check_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Iterator[Error]:
    """Check function definitions for limit violations."""
    yield from _check_bad_name(node.name, node.lineno, node.col_offset)

    line_count = get_function_line_count(node)
    if line_count > MAX_FUNCTION_LINES:
        yield Error(
            lineno=node.lineno,
            col_offset=node.col_offset,
            message=SLD601.format(node.name, line_count, MAX_FUNCTION_LINES),
        )

    arg_count = get_function_arg_count(node)
    if arg_count > MAX_FUNCTION_ARGS:
        yield Error(
            lineno=node.lineno,
            col_offset=node.col_offset,
            message=SLD602.format(node.name, arg_count, MAX_FUNCTION_ARGS),
        )


def _get_module_name_from_filename(filename: str) -> str | None:
    """Extract module name from filename for bad name checking."""
    import os

    if not filename:
        return None
    basename = os.path.basename(filename)
    if basename.endswith(".py"):
        module_name = basename[:-3]
        # Skip __init__ and other special files
        if module_name.startswith("__"):
            return None
        return module_name
    return None


@dataclass(slots=True)
class Checker:  # noqa: SLD501 SLD503
    """Flake8 checker for stolid conventions."""

    name = "stolid"
    version = "0.1.0"

    tree: ast.AST
    lines: list[str]
    filename: str = ""

    def run(self) -> Iterator[tuple[int, int, str, type]]:  # noqa: SLD303
        """Run all checks and yield errors."""
        if len(self.lines) > MAX_MODULE_LINES:
            yield (
                1,
                0,
                SLD604.format(len(self.lines), MAX_MODULE_LINES),
                type(self),
            )

        # Check module name
        module_name = _get_module_name_from_filename(self.filename)
        if module_name is not None:
            for error in _check_bad_name(module_name, 1, 0):
                yield (error.lineno, error.col_offset, error.message, type(self))

        patch_names, abstractmethod_names = collect_imports(self.tree)
        for node in ast.walk(self.tree):
            for error in _check_node(node, patch_names, abstractmethod_names):
                yield (error.lineno, error.col_offset, error.message, type(self))
