# Helper functions for AST inspection.

from __future__ import annotations

import ast
import re
from typing import Iterable

from ._constants import BAD_NAME_WORDS

FUNCTION_DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
FunctionType = ast.FunctionDef | ast.AsyncFunctionDef
NAMED_DEF_NODES = FUNCTION_DEF_NODES + (ast.ClassDef,)
TUPLE_LIST_NODES = (ast.Tuple, ast.List)


def is_name_id(node: ast.AST, name: str) -> bool:
    """Return True iff ``node`` is ``ast.Name`` with id ``name``."""
    return isinstance(node, ast.Name) and node.id == name


def is_name_in(node: ast.AST, names: Iterable[str]) -> bool:
    """Return True iff ``node`` is ``ast.Name`` whose id is in ``names``."""
    return isinstance(node, ast.Name) and node.id in names


def is_attribute_attr(node: ast.AST, attr: str) -> bool:
    """Return True iff ``node`` is ``ast.Attribute`` with ``.attr`` == ``attr``."""
    return isinstance(node, ast.Attribute) and node.attr == attr


def is_attribute_in(node: ast.AST, attrs: Iterable[str]) -> bool:
    """Return True iff ``node`` is ``ast.Attribute`` whose attr is in ``attrs``."""
    return isinstance(node, ast.Attribute) and node.attr in attrs


def get_base_name(node: ast.expr) -> str | None:
    """Return the base-class name expressed by ``node``, or ``None`` if unknown."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return get_base_name(node.value)
    return None


def class_inherits_from(node: ast.ClassDef, base_name: str) -> bool:
    """Return True iff class ``node`` lists a base whose name equals ``base_name``."""
    for base in node.bases:
        if get_base_name(base) == base_name:
            return True
    return False


def is_dataclass_decorator(node: ast.expr) -> bool:
    """Return True iff ``node`` is a ``@dataclass`` or ``@dataclasses.dataclass``."""
    if is_name_id(node, "dataclass"):
        return True
    if is_attribute_attr(node, "dataclass"):
        return True
    if isinstance(node, ast.Call):
        return is_dataclass_decorator(node.func)
    return False


def get_dataclass_keywords(node: ast.expr) -> dict[str, bool]:
    """Return the constant ``frozen``/``slots``/``kw_only`` kwargs of ``node``."""
    if not isinstance(node, ast.Call):
        return {}
    result: dict[str, bool] = {}
    for keyword in node.keywords:
        if keyword.arg in ("frozen", "slots", "kw_only"):  # noqa: SLD304
            if isinstance(keyword.value, ast.Constant):
                result[keyword.arg] = bool(keyword.value.value)
    return result


def method_accesses_private_state(
    node: FunctionType,
) -> bool:
    """Return True iff method ``node`` reads any ``self._private`` attribute."""
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            if is_name_id(child.value, "self") and child.attr.startswith("_"):
                return True
    return False


def is_method(node: FunctionType) -> bool:
    """Return True iff function ``node`` has ``self`` as its first positional arg."""
    if not node.args.args:
        return False
    first_arg = node.args.args[0]
    return first_arg.arg == "self"


_CM_SM = ("classmethod", "staticmethod")


def is_classmethod_or_staticmethod(
    node: FunctionType,
) -> bool:
    """Return True iff ``node`` is decorated ``@classmethod`` or ``@staticmethod``."""
    for decorator in node.decorator_list:
        if is_name_in(decorator, _CM_SM) or is_attribute_in(decorator, _CM_SM):
            return True
    return False


def is_dunder_method(name: str) -> bool:
    """Return True iff ``name`` is a dunder identifier (``__xxx__``)."""
    return name.startswith("__") and name.endswith("__")


_PROPERTY_SUFFIXES = ("setter", "getter", "deleter")


def is_property_method(node: FunctionType) -> bool:
    """Return True iff ``node`` is ``@property`` or an ``@x.setter``/getter/deleter."""
    for decorator in node.decorator_list:
        if is_name_id(decorator, "property"):
            return True
        if is_attribute_in(decorator, _PROPERTY_SUFFIXES):
            return True
    return False


def get_function_line_count(node: FunctionType) -> int:
    """Return the line span of function ``node``'s body."""
    assert node.body, "Function body cannot be empty in valid Python"
    first_line = node.body[0].lineno
    last_line = node.body[-1].end_lineno or node.body[-1].lineno
    return last_line - first_line + 1


def get_function_arg_count(node: FunctionType) -> int:
    """Return the argument count of function ``node`` (``self``/``cls`` excluded)."""
    args = node.args
    total = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
    if args.args and args.args[0].arg in ("self", "cls"):  # noqa: SLD304
        total -= 1
    return total


def get_class_method_count(node: ast.ClassDef) -> int:
    """Return the non-dunder method count of class ``node``."""
    count = 0
    for child in node.body:
        if isinstance(child, FUNCTION_DEF_NODES):
            if not is_dunder_method(child.name):
                count += 1
    return count


def _add_matching_aliases(
    aliases: list[ast.alias], wanted: tuple[str, ...], target: set[str]
) -> None:
    for alias in aliases:
        if alias.name in wanted:
            target.add(alias.asname or alias.name)


_PATCH_NAMES_WANTED = ("patch", "patch.object")
_ABSTRACT_WANTED = ("abstractmethod",)
_CAST_WANTED = ("cast",)


def collect_imports(tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
    """Return names bound in ``tree`` that alias patch, abstractmethod, and cast."""
    patch_names: set[str] = set()
    abstractmethod_names: set[str] = {"abstractmethod"}
    cast_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module in ("unittest.mock", "mock"):  # noqa: SLD304
            _add_matching_aliases(node.names, _PATCH_NAMES_WANTED, patch_names)
        if node.module == "abc":  # noqa: SLD304
            _add_matching_aliases(node.names, _ABSTRACT_WANTED, abstractmethod_names)
        if node.module == "typing":  # noqa: SLD304
            _add_matching_aliases(node.names, _CAST_WANTED, cast_names)
    return patch_names, abstractmethod_names, cast_names


# Pattern to split identifiers into words:
# - Split on underscores
# - Split on CamelCase boundaries (lowercase followed by uppercase)
_WORD_SPLIT_PATTERN = re.compile(r"_|(?<=[a-z])(?=[A-Z])")


def split_identifier_into_words(name: str) -> list[str]:
    """Split identifier ``name`` into its words and return them.

    Splits on underscores and CamelCase boundaries.

    Examples:
        "DiskUtil" -> ["Disk", "Util"]
        "disk_util" -> ["disk", "util"]
        "Futile" -> ["Futile"]
        "MyHelperClass" -> ["My", "Helper", "Class"]
    """
    return [word for word in _WORD_SPLIT_PATTERN.split(name) if word]


def find_bad_name_word(name: str) -> str | None:
    """Return the first forbidden word in identifier ``name``, or ``None`` if absent."""
    words = split_identifier_into_words(name)
    for word in words:
        if word.lower() in BAD_NAME_WORDS:
            return word.lower()
    return None
