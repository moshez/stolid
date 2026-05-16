"""Helper functions for AST inspection."""

from __future__ import annotations

import ast
import re

from ._constants import BAD_NAME_WORDS


def get_base_name(node: ast.expr) -> str | None:
    """Extract the name from a base class node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        # Handle Generic[T], Protocol[T], etc.
        return get_base_name(node.value)
    return None


def class_inherits_from(node: ast.ClassDef, base_name: str) -> bool:
    """Check if a class inherits directly from a base with the given name."""
    for base in node.bases:
        if get_base_name(base) == base_name:
            return True
    return False


def is_dataclass_decorator(node: ast.expr) -> bool:
    """Check if a decorator is @dataclass or @dataclasses.dataclass."""
    if isinstance(node, ast.Name):
        return node.id == "dataclass"
    if isinstance(node, ast.Attribute):
        return node.attr == "dataclass"
    if isinstance(node, ast.Call):
        return is_dataclass_decorator(node.func)
    return False


def get_dataclass_keywords(node: ast.expr) -> dict[str, bool]:
    """Extract keyword arguments from a dataclass decorator."""
    if not isinstance(node, ast.Call):
        return {}
    result: dict[str, bool] = {}
    for keyword in node.keywords:
        if keyword.arg in ("frozen", "slots", "kw_only"):
            if isinstance(keyword.value, ast.Constant):
                result[keyword.arg] = bool(keyword.value.value)
    return result


def method_accesses_private_state(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Check if a method accesses self._private attributes."""
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            if (
                isinstance(child.value, ast.Name)
                and child.value.id == "self"
                and child.attr.startswith("_")
            ):
                return True
    return False


def is_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function definition is a method (has self as first arg)."""
    if not node.args.args:
        return False
    first_arg = node.args.args[0]
    return first_arg.arg == "self"


def is_classmethod_or_staticmethod(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Check if a method has @classmethod or @staticmethod decorator."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            if decorator.id in ("classmethod", "staticmethod"):
                return True
        if isinstance(decorator, ast.Attribute):
            if decorator.attr in ("classmethod", "staticmethod"):
                return True
    return False


def is_dunder_method(name: str) -> bool:
    """Check if a method name is a dunder method (__xxx__)."""
    return name.startswith("__") and name.endswith("__")


def is_property_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a method is a property (has @property or @xxx.setter decorator)."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "property":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr in (
            "setter",
            "getter",
            "deleter",
        ):
            return True
    return False


def get_function_line_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count the number of lines in a function body."""
    assert node.body, "Function body cannot be empty in valid Python"
    first_line = node.body[0].lineno
    last_line = node.body[-1].end_lineno or node.body[-1].lineno
    return last_line - first_line + 1


def get_function_arg_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count the number of arguments in a function (excluding self/cls)."""
    args = node.args
    total = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
    # Exclude self or cls from the count
    if args.args and args.args[0].arg in ("self", "cls"):
        total -= 1
    return total


def get_class_method_count(node: ast.ClassDef) -> int:
    """Count the number of methods in a class (excluding dunders)."""
    count = 0
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not is_dunder_method(child.name):
                count += 1
    return count


def collect_imports(tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
    """Collect names that refer to patch, abstractmethod, or cast."""
    patch_names: set[str] = set()
    abstractmethod_names: set[str] = {"abstractmethod"}
    cast_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module in ("unittest.mock", "mock"):
            for alias in node.names:
                if alias.name in ("patch", "patch.object"):
                    patch_names.add(alias.asname or alias.name)
        if node.module == "abc":
            for alias in node.names:
                if alias.name == "abstractmethod":
                    abstractmethod_names.add(alias.asname or alias.name)
        if node.module == "typing":
            for alias in node.names:
                if alias.name == "cast":
                    cast_names.add(alias.asname or alias.name)
    return patch_names, abstractmethod_names, cast_names


# Pattern to split identifiers into words:
# - Split on underscores
# - Split on CamelCase boundaries (lowercase followed by uppercase)
_WORD_SPLIT_PATTERN = re.compile(r"_|(?<=[a-z])(?=[A-Z])")


def split_identifier_into_words(name: str) -> list[str]:
    """Split an identifier into words by underscores and CamelCase boundaries.

    Examples:
        "DiskUtil" -> ["Disk", "Util"]
        "disk_util" -> ["disk", "util"]
        "Futile" -> ["Futile"]
        "MyHelperClass" -> ["My", "Helper", "Class"]
    """
    return [word for word in _WORD_SPLIT_PATTERN.split(name) if word]


def find_bad_name_word(name: str) -> str | None:
    """Check if an identifier contains a forbidden word at a word boundary.

    Returns the forbidden word if found, None otherwise.
    """
    words = split_identifier_into_words(name)
    for word in words:
        if word.lower() in BAD_NAME_WORDS:
            return word.lower()
    return None
