"""Flake8 plugin enforcing lint-python-standard conventions."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

__all__ = ["Checker"]

# Error codes and messages
LPS102 = "LPS102 Use of patch/patch.object is prohibited (use dependency injection)"
LPS201 = "LPS201 Import of ABC is prohibited (use Protocol instead)"
LPS202 = "LPS202 Use of @abstractmethod is prohibited (use Protocol instead)"
LPS301 = (
    "LPS301 __init__ method is prohibited (use @dataclass with default_factory "
    "for attribute initialization; use @classmethod for ergonomic parameter "
    "computation)"
)
LPS302 = "LPS302 Private method '{}' defined (extract to separate class)"
LPS303 = (
    "LPS303 Method '{}' only accesses public members of self "
    "(convert to module-level function; use functools.singledispatch "
    "if polymorphism is needed)"
)
LPS401 = "LPS401 Class '{}' inherits from concrete class '{}' (use composition)"
LPS501 = "LPS501 Dataclass '{}' missing frozen=True"
LPS502 = "LPS502 Dataclass '{}' missing slots=True"
LPS503 = "LPS503 Dataclass '{}' missing kw_only=True"

# Allowed base classes for inheritance
ALLOWED_BASES: frozenset[str] = frozenset(
    {
        # typing
        "Protocol",
        "Generic",
        # exceptions
        "Exception",
        "BaseException",
        # testing
        "TestCase",
        # enums
        "Enum",
        "IntEnum",
        "StrEnum",
        "Flag",
        "IntFlag",
        # other acceptable patterns
        "TypedDict",
        "NamedTuple",
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class Error:
    """Represents a lint error."""

    lineno: int
    col_offset: int
    message: str


def _get_base_name(node: ast.expr) -> str | None:
    """Extract the name from a base class node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        # Handle Generic[T], Protocol[T], etc.
        return _get_base_name(node.value)
    return None


def _is_dataclass_decorator(node: ast.expr) -> bool:
    """Check if a decorator is @dataclass or @dataclasses.dataclass."""
    if isinstance(node, ast.Name):
        return node.id == "dataclass"
    if isinstance(node, ast.Attribute):
        return node.attr == "dataclass"
    if isinstance(node, ast.Call):
        return _is_dataclass_decorator(node.func)
    return False


def _get_dataclass_keywords(node: ast.expr) -> dict[str, bool]:
    """Extract keyword arguments from a dataclass decorator."""
    if not isinstance(node, ast.Call):
        return {}
    result: dict[str, bool] = {}
    for keyword in node.keywords:
        if keyword.arg in ("frozen", "slots", "kw_only"):
            if isinstance(keyword.value, ast.Constant):
                result[keyword.arg] = bool(keyword.value.value)
    return result


def _method_accesses_private_state(
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


def _method_accesses_self(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a method accesses self at all."""
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            if isinstance(child.value, ast.Name) and child.value.id == "self":
                return True
    return False


def _is_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function definition is a method (has self as first arg)."""
    if not node.args.args:
        return False
    first_arg = node.args.args[0]
    return first_arg.arg == "self"


def _is_classmethod_or_staticmethod(
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


def _is_dunder_method(name: str) -> bool:
    """Check if a method name is a dunder method (__xxx__)."""
    return name.startswith("__") and name.endswith("__")


def _is_property_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
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


class Checker:
    """Flake8 checker for lint-python-standard conventions.

    Note: This class intentionally uses __init__ and private methods
    because flake8's plugin API requires this structure.
    """

    name = "lint-python-standard"
    version = "0.1.0"

    def __init__(self, tree: ast.AST) -> None:  # noqa: LPS301
        self._tree = tree
        self._patch_names: set[str] = set()
        self._abstractmethod_names: set[str] = set()

    def run(self) -> Iterator[tuple[int, int, str, type]]:
        """Run all checks and yield errors."""
        errors = list(self._collect_errors())
        for error in errors:
            yield (error.lineno, error.col_offset, error.message, type(self))

    def _collect_errors(self) -> Iterator[Error]:  # noqa: LPS302
        """Collect all errors from the AST."""
        # First pass: collect imported names for patch and abstractmethod
        self._collect_imports()

        # Second pass: check all nodes
        for node in ast.walk(self._tree):
            yield from self._check_node(node)

    def _collect_imports(self) -> None:  # noqa: LPS302
        """Collect names that refer to patch or abstractmethod."""
        for node in ast.walk(self._tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "unittest.mock" or node.module == "mock":
                    for alias in node.names:
                        if alias.name in ("patch", "patch.object"):
                            name = alias.asname if alias.asname else alias.name
                            self._patch_names.add(name)
                if node.module == "abc":
                    for alias in node.names:
                        if alias.name == "abstractmethod":
                            name = alias.asname if alias.asname else alias.name
                            self._abstractmethod_names.add(name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("unittest.mock", "mock"):
                        # import unittest.mock or import mock
                        # patch would be accessed as unittest.mock.patch
                        pass  # Handled via attribute access

    def _check_node(self, node: ast.AST) -> Iterator[Error]:  # noqa: LPS302
        """Check a single AST node for violations."""
        if isinstance(node, ast.ImportFrom):
            yield from self._check_import_from(node)
        elif isinstance(node, ast.Attribute):
            yield from self._check_attribute(node)
        elif isinstance(node, ast.Name):
            yield from self._check_name(node)
        elif isinstance(node, ast.ClassDef):
            yield from self._check_class(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield from self._check_function(node)
        elif isinstance(node, ast.Call):
            yield from self._check_call(node)
        elif isinstance(node, ast.With):
            yield from self._check_with(node)

    def _check_import_from(  # noqa: LPS302
        self, node: ast.ImportFrom
    ) -> Iterator[Error]:
        """Check ImportFrom statements."""
        # LPS102: Check for patch imports
        if node.module in ("unittest.mock", "mock"):
            for alias in node.names:
                if alias.name == "patch":
                    yield Error(
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        message=LPS102,
                    )

        # LPS201: Check for ABC imports
        if node.module == "abc":
            for alias in node.names:
                if alias.name == "ABC":
                    yield Error(
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        message=LPS201,
                    )
                # LPS202: Check for abstractmethod imports
                if alias.name == "abstractmethod":
                    yield Error(
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        message=LPS202,
                    )

    def _check_attribute(self, node: ast.Attribute) -> Iterator[Error]:  # noqa: LPS302
        """Check attribute access for patch usage."""
        # Check for mock.patch, unittest.mock.patch
        if node.attr == "patch":
            if isinstance(node.value, ast.Attribute):
                if node.value.attr == "mock":
                    yield Error(
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        message=LPS102,
                    )
            elif isinstance(node.value, ast.Name):  # pragma: no branch
                if node.value.id == "mock":
                    yield Error(
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        message=LPS102,
                    )

    def _check_name(self, node: ast.Name) -> Iterator[Error]:  # noqa: LPS302
        """Check name references."""
        # LPS102: Check for patch usage as decorator or call
        # This is handled by decorator/call checks, so nothing to yield here
        return
        yield  # Make this a generator

    def _check_call(self, node: ast.Call) -> Iterator[Error]:  # noqa: LPS302
        """Check function calls."""
        # LPS102: Check for patch() calls
        if isinstance(node.func, ast.Name):
            if node.func.id in self._patch_names:
                yield Error(
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    message=LPS102,
                )
        elif isinstance(node.func, ast.Attribute):  # pragma: no branch
            # Check for patch.object()
            if node.func.attr == "object":
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id in self._patch_names:
                        yield Error(
                            lineno=node.lineno,
                            col_offset=node.col_offset,
                            message=LPS102,
                        )
                elif isinstance(node.func.value, ast.Attribute):  # pragma: no branch
                    if node.func.value.attr == "patch":
                        yield Error(
                            lineno=node.lineno,
                            col_offset=node.col_offset,
                            message=LPS102,
                        )

    def _check_with(self, node: ast.With) -> Iterator[Error]:  # noqa: LPS302
        """Check with statements for patch context managers."""
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                call = item.context_expr
                if isinstance(call.func, ast.Name):
                    if call.func.id in self._patch_names:
                        yield Error(
                            lineno=node.lineno,
                            col_offset=node.col_offset,
                            message=LPS102,
                        )

    def _check_class(self, node: ast.ClassDef) -> Iterator[Error]:  # noqa: LPS302
        """Check class definitions."""
        is_dataclass = False
        dataclass_keywords: dict[str, bool] = {}

        # Check decorators
        for decorator in node.decorator_list:
            if _is_dataclass_decorator(decorator):
                is_dataclass = True
                dataclass_keywords = _get_dataclass_keywords(decorator)

            # LPS202: Check for @abstractmethod (unusual on class, but check)
            if isinstance(decorator, ast.Name):
                if decorator.id in self._abstractmethod_names:
                    yield Error(
                        lineno=decorator.lineno,
                        col_offset=decorator.col_offset,
                        message=LPS202,
                    )

        # LPS401: Check base classes
        for base in node.bases:
            base_name = _get_base_name(base)
            if base_name is not None and base_name not in ALLOWED_BASES:
                yield Error(
                    lineno=base.lineno,
                    col_offset=base.col_offset,
                    message=LPS401.format(node.name, base_name),
                )

        # LPS501/502/503: Check dataclass flags
        if is_dataclass:
            if not dataclass_keywords.get("frozen", False):
                yield Error(
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    message=LPS501.format(node.name),
                )
            if not dataclass_keywords.get("slots", False):
                yield Error(
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    message=LPS502.format(node.name),
                )
            if not dataclass_keywords.get("kw_only", False):
                yield Error(
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    message=LPS503.format(node.name),
                )

        # Check methods within the class
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from self._check_method_in_class(child, is_dataclass)

    def _check_method_in_class(  # noqa: LPS302
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_dataclass: bool,
    ) -> Iterator[Error]:
        """Check a method within a class context."""
        # LPS202: Check for @abstractmethod decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if (
                    decorator.id in self._abstractmethod_names
                    or decorator.id == "abstractmethod"
                ):
                    yield Error(
                        lineno=decorator.lineno,
                        col_offset=decorator.col_offset,
                        message=LPS202,
                    )
            elif isinstance(decorator, ast.Attribute):
                if decorator.attr == "abstractmethod":
                    yield Error(
                        lineno=decorator.lineno,
                        col_offset=decorator.col_offset,
                        message=LPS202,
                    )

        # Skip non-methods
        if not _is_method(node):
            return

        # Skip classmethods/staticmethods
        if _is_classmethod_or_staticmethod(node):
            return

        # LPS301: Check for __init__ (always flagged - dataclass generates it)
        if node.name == "__init__":
            yield Error(
                lineno=node.lineno,
                col_offset=node.col_offset,
                message=LPS301,
            )

        # LPS302: Check for private methods (excluding dunders)
        if node.name.startswith("_") and not _is_dunder_method(node.name):
            yield Error(
                lineno=node.lineno,
                col_offset=node.col_offset,
                message=LPS302.format(node.name),
            )

        # LPS303: Check if method only accesses public members
        # Skip dunders, properties
        if _is_dunder_method(node.name):
            return
        if _is_property_method(node):
            return

        if _method_accesses_self(node) and not _method_accesses_private_state(node):
            yield Error(
                lineno=node.lineno,
                col_offset=node.col_offset,
                message=LPS303.format(node.name),
            )

    def _check_function(  # noqa: LPS302
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> Iterator[Error]:
        """Check function definitions at module level."""
        # Module-level functions are fine, we only check methods in _check_class
        return
        yield  # Make this a generator
