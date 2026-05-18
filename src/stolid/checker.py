"""Flake8 plugin enforcing stolid conventions."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from typing import Iterator

from ._constants import (
    ALLOWED_BASES,
    SLD102,
    SLD201,
    SLD202,
    SLD203,
    SLD301,
    SLD302,
    SLD303,
    SLD401,
    SLD501,
    SLD502,
    SLD503,
    SLD602,
    SLD603,
    SLD604,
    SLD701,
    MAX_CLASS_METHODS,
    MAX_FUNCTION_ARGS,
    MAX_FUNCTION_LINES,
    MAX_MODULE_LINES,
)
from ._docstring_check import check_docstrings
from ._global_names_check import check_global_names
from ._string_enum_check import check_string_enum
from ._check_runner import (
    CheckContext,
    ErrorLike,
    build_context,
    format_sld601,
    import_placement_errors,
    privacy_errors,
)
from ._ast_inspection import (
    FUNCTION_DEF_NODES,
    FunctionType,
    class_inherits_from,
    find_bad_name_word,
    get_base_name,
    get_class_method_count,
    get_dataclass_keywords,
    get_function_arg_count,
    get_function_complexity,
    is_attribute_attr,
    is_classmethod_or_staticmethod,
    is_dataclass_decorator,
    is_dunder_method,
    is_method,
    is_name_id,
    is_name_in,
    is_property_method,
    method_accesses_private_state,
)

__all__ = ["Checker"]


@dataclass(frozen=True, slots=True, kw_only=True)
class Error:
    """A lint error: ``lineno``/``col_offset`` locate it; ``message`` describes it."""

    lineno: int
    col_offset: int
    message: str


def _error(node: ast.stmt | ast.expr, message: str) -> Error:
    return Error(lineno=node.lineno, col_offset=node.col_offset, message=message)


def _name_decorator_errors(
    decorators: list[ast.expr], names: set[str], code: str
) -> Iterator[Error]:
    # Yield SLD202-style errors for decorators that are Names in ``names``.
    for decorator in decorators:
        if is_name_in(decorator, names):
            yield _error(decorator, code)


def _check_node_name(
    node: ast.ClassDef | FunctionType,
) -> Iterator[Error]:
    return _check_bad_name(node.name, node.lineno, node.col_offset)


def _check_node(node: ast.AST, ctx: CheckContext) -> Iterator[Error]:
    # Check a single AST node for violations.
    if isinstance(node, ast.ImportFrom):
        yield from _check_import_from(node)
    elif isinstance(node, ast.Attribute):
        yield from _check_attribute(node)
    elif isinstance(node, ast.ClassDef):
        yield from _check_class(node, ctx.abstractmethod_names)
    elif isinstance(node, FUNCTION_DEF_NODES):
        yield from _check_function(node, ctx.lines, ctx.bracket_depths)
    elif isinstance(node, ast.Call):
        yield from _check_call(node, ctx.patch_names, ctx.cast_names)
    elif isinstance(node, ast.With):
        yield from _check_with(node, ctx.patch_names)


def _check_import_from(node: ast.ImportFrom) -> Iterator[Error]:
    # Check ImportFrom statements.
    if node.module in ("unittest.mock", "mock"):  # noqa: SLD304
        for alias in node.names:
            if alias.name == "patch":  # noqa: SLD304 SLD306
                yield _error(node, SLD102)

    if node.module == "abc":  # noqa: SLD304
        for alias in node.names:
            if alias.name == "ABC":  # noqa: SLD304
                yield _error(node, SLD201)
            if alias.name == "abstractmethod":  # noqa: SLD304
                yield _error(node, SLD202)


def _check_attribute(node: ast.Attribute) -> Iterator[Error]:
    # Check attribute access for patch usage.
    if node.attr != "patch":  # noqa: SLD306
        return
    value = node.value
    if is_attribute_attr(value, "mock"):
        yield _error(node, SLD102)
    elif is_name_id(value, "mock"):  # pragma: no branch
        yield _error(node, SLD102)


def _check_call(
    node: ast.Call, patch_names: set[str], cast_names: set[str]
) -> Iterator[Error]:
    # Check function calls.
    if isinstance(node.func, ast.Name):
        if node.func.id in patch_names:
            yield _error(node, SLD102)
        elif node.func.id in cast_names:
            yield _error(node, SLD203)
    elif isinstance(node.func, ast.Attribute):  # pragma: no branch
        yield from _check_call_attribute(node, patch_names)


def _check_call_attribute(node: ast.Call, patch_names: set[str]) -> Iterator[Error]:
    # Check Call nodes whose func is an Attribute (patch.object, typing.cast).
    func = node.func
    assert isinstance(func, ast.Attribute)
    if func.attr == "cast":  # noqa: SLD304
        if is_name_id(func.value, "typing"):
            yield _error(node, SLD203)
        return
    if func.attr != "object":  # noqa: SLD304
        return
    if isinstance(func.value, ast.Name):
        if func.value.id in patch_names:
            yield _error(node, SLD102)
    elif isinstance(func.value, ast.Attribute):  # pragma: no branch
        if func.value.attr == "patch":  # noqa: SLD306
            yield _error(node, SLD102)


def _check_with(node: ast.With, patch_names: set[str]) -> Iterator[Error]:
    # Check with statements for patch context managers.
    for item in node.items:
        call = item.context_expr
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
            continue
        if call.func.id in patch_names:
            yield _error(node, SLD102)


def _check_bad_name(name: str, lineno: int, col_offset: int) -> Iterator[Error]:
    # Check if a name contains a forbidden word.
    bad_word = find_bad_name_word(name)
    if bad_word is not None:
        yield Error(
            lineno=lineno,
            col_offset=col_offset,
            message=SLD701.format(name, bad_word),
        )


def _check_class_bases(node: ast.ClassDef) -> Iterator[Error]:
    # Check class base classes for inheritance violations.
    for base in node.bases:
        base_name = get_base_name(base)
        if base_name is not None and base_name not in ALLOWED_BASES:
            yield _error(base, SLD401.format(node.name, base_name))


_DATACLASS_FLAGS = (("frozen", SLD501), ("slots", SLD502), ("kw_only", SLD503))


def _check_dataclass_flags(
    node: ast.ClassDef, keywords: dict[str, bool]
) -> Iterator[Error]:
    # Check dataclass decorator flags.
    for flag, code in _DATACLASS_FLAGS:
        if not keywords.get(flag, False):
            yield _error(node, code.format(node.name))


def _check_class(node: ast.ClassDef, abstractmethod_names: set[str]) -> Iterator[Error]:
    # Check class definitions.
    is_dataclass = False
    dataclass_keywords: dict[str, bool] = {}

    for decorator in node.decorator_list:
        if is_dataclass_decorator(decorator):
            is_dataclass = True
            dataclass_keywords = get_dataclass_keywords(decorator)

    yield from _check_node_name(node)
    yield from _check_abstract_decorators(node.decorator_list, abstractmethod_names)
    yield from _check_class_bases(node)

    if is_dataclass:
        yield from _check_dataclass_flags(node, dataclass_keywords)

    method_count = get_class_method_count(node)
    if method_count > MAX_CLASS_METHODS:
        yield _error(node, SLD603.format(node.name, method_count, MAX_CLASS_METHODS))

    yield from _check_class_method_bodies(node, abstractmethod_names)


def _check_class_method_bodies(
    node: ast.ClassDef, abstractmethod_names: set[str]
) -> Iterator[Error]:
    # Check method bodies of a class.
    is_testcase = class_inherits_from(node, "TestCase")
    is_protocol = class_inherits_from(node, "Protocol")
    for child in node.body:
        if isinstance(child, FUNCTION_DEF_NODES):
            yield from _check_method_in_class(
                child,
                abstractmethod_names,
                is_testcase=is_testcase,
                is_protocol=is_protocol,
            )


def _check_abstract_decorators(
    decorators: list[ast.expr], names: set[str]
) -> Iterator[Error]:
    # Yield SLD202 for both Name and Attribute-form @abstractmethod decorators.
    yield from _name_decorator_errors(decorators, names, SLD202)
    for decorator in decorators:
        if is_attribute_attr(decorator, "abstractmethod"):
            yield _error(decorator, SLD202)


def _check_method_naming(
    node: FunctionType,
) -> Iterator[Error]:
    # Check method naming conventions.
    if node.name in ("__init__", "__post_init__"):  # noqa: SLD304
        yield _error(node, SLD301.format(node.name))
    if node.name.startswith("_") and not is_dunder_method(node.name):
        yield _error(node, SLD302.format(node.name))


def _check_method_in_class(
    node: FunctionType,
    abstractmethod_names: set[str],
    is_testcase: bool = False,
    is_protocol: bool = False,
) -> Iterator[Error]:
    # Check a method within a class context.
    yield from _check_abstract_decorators(node.decorator_list, abstractmethod_names)

    if not is_method(node) or is_classmethod_or_staticmethod(node):
        return

    yield from _check_method_naming(node)

    if is_dunder_method(node.name) or is_property_method(node):
        return

    if is_protocol:
        return

    if is_testcase and node.name.startswith("test_"):
        return

    if not method_accesses_private_state(node):
        yield _error(node, SLD303.format(node.name))


def _check_function(
    node: FunctionType, lines: list[str], bracket_depths: dict[int, int]
) -> Iterator[Error]:
    # Check function definitions for limit violations.
    yield from _check_node_name(node)
    complexity = get_function_complexity(node, lines, bracket_depths)
    if complexity.weight > MAX_FUNCTION_LINES:
        yield _error(node, format_sld601(node.name, complexity))
    arg_count = get_function_arg_count(node)
    if arg_count > MAX_FUNCTION_ARGS:
        yield _error(node, SLD602.format(node.name, arg_count, MAX_FUNCTION_ARGS))


def _get_module_name_from_filename(filename: str) -> str | None:
    # Extract module name from filename for bad name checking.
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


def _module_level_errors(lines: list[str], filename: str) -> Iterator[Error]:
    # Yield errors derived from the module's lines or filename.
    if len(lines) > MAX_MODULE_LINES:
        yield Error(
            lineno=1,
            col_offset=0,
            message=SLD604.format(len(lines), MAX_MODULE_LINES),
        )
    module_name = _get_module_name_from_filename(filename)
    if module_name is not None:
        yield from _check_bad_name(module_name, 1, 0)


def _all_errors(
    tree: ast.Module, lines: list[str], filename: str
) -> Iterator[ErrorLike]:
    yield from _module_level_errors(lines, filename)
    yield from check_global_names(tree)
    yield from import_placement_errors(tree)
    yield from check_string_enum(tree)
    yield from check_docstrings(tree, filename)
    yield from privacy_errors(tree)
    ctx = build_context(tree, lines)
    for node in ast.walk(tree):
        yield from _check_node(node, ctx)


@dataclass(slots=True)
class Checker:  # noqa: SLD501 SLD503
    """Flake8 checker for stolid: parsed ``tree``, source ``lines``, ``filename``."""

    name = "stolid"
    version = "0.1.0"

    tree: ast.Module
    lines: list[str]
    filename: str = ""

    def run(self) -> Iterator[tuple[int, int, str, type]]:  # noqa: SLD303
        """Run all stolid checks and yield ``(line, col, message, type)`` tuples."""
        cls = type(self)
        for err in _all_errors(self.tree, self.lines, self.filename):
            yield (err.lineno, err.col_offset, err.message, cls)
