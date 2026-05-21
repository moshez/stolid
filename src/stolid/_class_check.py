# Class-shaped checks: ABC/abstractmethod imports, class-body decorators,
# class bases, dataclass flags, method naming, method state access, and
# class method counts. Owns SLD2xx (ABC), SLD3xx (methods), SLD401
# (inheritance), SLD5xx (dataclass flags), SLD603 (class size), and
# SLD608 (dataclass field count).

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._ast_inspection import (
    FUNCTION_DEF_NODES,
    FunctionType,
    bad_name_errors_as,
    get_base_name,
    is_dataclass_decorator,
    is_dunder_name,
    is_name_among,
)
from ._constants import ALLOWED_BASES, MAX_CLASS_METHODS, MAX_DATACLASS_FIELDS

SLD201 = "SLD201 Import of ABC is prohibited (use Protocol instead)"
SLD202 = "SLD202 Use of @abstractmethod is prohibited (use Protocol instead)"
SLD301 = (
    "SLD301 {} method is prohibited (use @dataclass with default_factory "
    "for attribute initialization; use @classmethod for ergonomic parameter "
    "computation)"
)
SLD302 = "SLD302 Private method '{}' defined (extract to separate class)"
SLD303 = (
    "SLD303 Method '{}' does not access any private state "
    "(convert to module-level function; use functools.singledispatch "
    "if polymorphism is needed)"
)
SLD401 = "SLD401 Class '{}' inherits from concrete class '{}' (use composition)"
SLD501 = "SLD501 Dataclass '{}' missing frozen=True"
SLD502 = "SLD502 Dataclass '{}' missing slots=True"
SLD503 = "SLD503 Dataclass '{}' missing kw_only=True"
SLD504 = "SLD504 Class '{}' is not a @dataclass"
SLD603 = "SLD603 Class '{}' has {} methods (limit: {})"
SLD608 = "SLD608 Dataclass '{}' has {} fields (limit: {})"

_CM_SM = ("classmethod", "staticmethod")
_PROPERTY_NAMES = ("property",)
_PROPERTY_SUFFIXES = ("setter", "getter", "deleter")
_OVERRIDE_NAMES = ("override",)
_DATACLASS_FLAGS = (("frozen", SLD501), ("slots", SLD502), ("kw_only", SLD503))


@dataclass(frozen=True, slots=True, kw_only=True)
class ClassError:
    """A class-rule violation.

    ``lineno`` and ``col_offset`` locate the offending node; ``message``
    is the formatted SLD2xx/SLD3xx/SLD4xx/SLD5xx/SLD603/SLD608 diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


def _error(node: ast.stmt | ast.expr, message: str) -> ClassError:
    return ClassError(lineno=node.lineno, col_offset=node.col_offset, message=message)


def _class_inherits_from(node: ast.ClassDef, base_name: str) -> bool:
    for base in node.bases:
        if get_base_name(base) == base_name:
            return True
    return False


def _get_class_method_count(node: ast.ClassDef) -> int:
    count = 0
    for child in node.body:
        if isinstance(child, FUNCTION_DEF_NODES):
            if not is_dunder_name(child.name):
                count += 1
    return count


def _get_dataclass_field_count(node: ast.ClassDef) -> int:
    count = 0
    for child in node.body:
        if isinstance(child, ast.AnnAssign):
            if get_base_name(child.annotation) != "ClassVar":
                count += 1
    return count


def _get_dataclass_keywords(node: ast.expr) -> dict[str, bool]:
    if not isinstance(node, ast.Call):
        return {}
    result: dict[str, bool] = {}
    for keyword in node.keywords:
        if keyword.arg in ("frozen", "slots", "kw_only"):  # noqa: SLD304
            if isinstance(keyword.value, ast.Constant):
                result[keyword.arg] = bool(keyword.value.value)
    return result


def _is_method(node: FunctionType) -> bool:
    if not node.args.args:
        return False
    return node.args.args[0].arg == "self"


def _has_decorator(
    node: FunctionType, names: tuple[str, ...], attrs: tuple[str, ...]
) -> bool:
    for decorator in node.decorator_list:
        if is_name_among(decorator, names):
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr in attrs:
            return True
    return False


def _is_classmethod_or_staticmethod(node: FunctionType) -> bool:
    return _has_decorator(node, _CM_SM, _CM_SM)


def _is_property_method(node: FunctionType) -> bool:
    return _has_decorator(node, _PROPERTY_NAMES, _PROPERTY_SUFFIXES)


def _is_override_method(node: FunctionType) -> bool:
    return _has_decorator(node, _OVERRIDE_NAMES, _OVERRIDE_NAMES)


def _method_accesses_private_state(node: FunctionType) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            value = child.value
            if isinstance(value, ast.Name) and value.id == "self":
                if child.attr.startswith("_"):
                    return True
    return False


def check_abc_import(node: ast.ImportFrom) -> Iterator[ClassError]:
    """Yield SLD201/SLD202 for forbidden ``from abc import`` patterns in ``node``."""
    if node.module != "abc":
        return
    for alias in node.names:
        if alias.name == "ABC":  # noqa: SLD304
            yield _error(node, SLD201)
        if alias.name == "abstractmethod":  # noqa: SLD304
            yield _error(node, SLD202)


def _name_decorator_errors(
    decoration_list: list[ast.expr], names: set[str], template: str
) -> Iterator[ClassError]:
    for decorator in decoration_list:
        if is_name_among(decorator, names):
            yield _error(decorator, template)


def check_abstract_decorators(
    decoration_list: list[ast.expr], names: set[str]
) -> Iterator[ClassError]:
    """Yield SLD202 for @abstractmethod use in ``decoration_list``.

    ``names`` are the module-local bindings that refer to
    ``abstractmethod`` (e.g. when imported under an alias).
    """
    yield from _name_decorator_errors(decoration_list, names, SLD202)
    for decorator in decoration_list:
        if isinstance(decorator, ast.Attribute) and decorator.attr == "abstractmethod":
            yield _error(decorator, SLD202)


def _check_class_bases(node: ast.ClassDef) -> Iterator[ClassError]:
    for base in node.bases:
        base_name = get_base_name(base)
        if base_name is not None and base_name not in ALLOWED_BASES:
            yield _error(base, SLD401.format(node.name, base_name))


def _check_dataclass_flags(
    node: ast.ClassDef, keywords: dict[str, bool]
) -> Iterator[ClassError]:
    for flag, template in _DATACLASS_FLAGS:
        if not keywords.get(flag, False):
            yield _error(node, template.format(node.name))


def _check_method_naming(node: FunctionType) -> Iterator[ClassError]:
    if node.name in ("__init__", "__post_init__"):  # noqa: SLD304
        yield _error(node, SLD301.format(node.name))
    if node.name.startswith("_") and not is_dunder_name(node.name):
        yield _error(node, SLD302.format(node.name))


def _check_sld303_for_method(node: FunctionType) -> Iterator[ClassError]:
    # Emit SLD303 if ``node`` -- already a regular method that is neither
    # a dunder, a property, nor explicitly @override -- touches no private
    # state. @override signals the author chose method-form deliberately.
    if is_dunder_name(node.name) or _is_property_method(node):
        return
    if _is_override_method(node):
        return
    if not _method_accesses_private_state(node):
        yield _error(node, SLD303.format(node.name))


def _check_class_method_bodies(
    node: ast.ClassDef, abstractmethod_names: set[str]
) -> Iterator[ClassError]:
    is_protocol = _class_inherits_from(node, "Protocol")
    is_testcase = _class_inherits_from(node, "TestCase")
    for child in node.body:
        if not isinstance(child, FUNCTION_DEF_NODES):
            continue
        yield from check_abstract_decorators(child.decorator_list, abstractmethod_names)
        if not _is_method(child) or _is_classmethod_or_staticmethod(child):
            continue
        yield from _check_method_naming(child)
        if is_protocol:
            continue
        if is_testcase and child.name.startswith("test_"):
            continue
        yield from _check_sld303_for_method(child)


def _dataclass_flags(node: ast.ClassDef) -> dict[str, bool] | None:
    # Return decorator keyword flags if ``node`` is a dataclass, else None.
    for decorator in node.decorator_list:
        if is_dataclass_decorator(decorator):
            return _get_dataclass_keywords(decorator)
    return None


def _has_allowed_base(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if get_base_name(base) in ALLOWED_BASES:
            return True
    return False


def check_class(
    node: ast.ClassDef, abstractmethod_names: set[str]
) -> Iterator[ClassError]:
    """Yield SLD3xx/SLD4xx/SLD5xx/SLD603/SLD608/SLD701 violations for class ``node``.

    ``abstractmethod_names`` is the set of module-local bindings that
    refer to ``abstractmethod`` (used by the SLD202 decorator check).
    """
    yield from bad_name_errors_as(node.name, node.lineno, node.col_offset, ClassError)
    yield from check_abstract_decorators(node.decorator_list, abstractmethod_names)
    yield from _check_class_bases(node)
    flags = _dataclass_flags(node)
    if flags is not None:
        yield from _check_dataclass_flags(node, flags)
        field_count = _get_dataclass_field_count(node)
        if field_count > MAX_DATACLASS_FIELDS:
            yield _error(
                node, SLD608.format(node.name, field_count, MAX_DATACLASS_FIELDS)
            )
    elif not _has_allowed_base(node):
        yield _error(node, SLD504.format(node.name))
    method_count = _get_class_method_count(node)
    if method_count > MAX_CLASS_METHODS:
        yield _error(node, SLD603.format(node.name, method_count, MAX_CLASS_METHODS))
    yield from _check_class_method_bodies(node, abstractmethod_names)
