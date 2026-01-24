"""Tests for the lint-python-standard flake8 checker."""

from __future__ import annotations

import ast
import textwrap
import unittest

from hamcrest import (
    assert_that,
    contains_string,
    empty,
    equal_to,
    has_item,
)

from ..checker import Checker


def check_code(code: str) -> list[tuple[int, int, str]]:
    """Parse code and return list of (line, col, message) errors."""
    tree = ast.parse(textwrap.dedent(code))
    checker = Checker(tree)
    return [(line, col, msg) for line, col, msg, _ in checker.run()]


def get_error_codes(code: str) -> list[str]:
    """Parse code and return list of error codes only."""
    errors = check_code(code)
    return [msg.split()[0] for _, _, msg in errors]


class TestLPS102PatchProhibited(unittest.TestCase):
    """Tests for LPS102: patch/patch.object is prohibited."""

    def test_import_patch_from_unittest_mock(self) -> None:
        code = """
        from unittest.mock import patch
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS102"))

    def test_import_patch_from_mock(self) -> None:
        code = """
        from mock import patch
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS102"))

    def test_patch_decorator(self) -> None:
        code = """
        from unittest.mock import patch

        @patch("module.thing")
        def test_something():
            pass
        """
        codes = get_error_codes(code)
        # Should have at least one LPS102 for the import
        assert_that(codes, has_item("LPS102"))

    def test_patch_context_manager(self) -> None:
        code = """
        from unittest.mock import patch

        def test_something():
            with patch("module.thing"):
                pass
        """
        codes = get_error_codes(code)
        # Import + context manager usage
        assert_that("LPS102" in codes, equal_to(True))

    def test_patch_object_call(self) -> None:
        code = """
        from unittest.mock import patch

        def test_something():
            patch.object(obj, "attr")
        """
        codes = get_error_codes(code)
        assert_that("LPS102" in codes, equal_to(True))

    def test_unittest_mock_patch_attribute_access(self) -> None:
        code = """
        import unittest.mock

        unittest.mock.patch("thing")
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS102"))

    def test_mock_module_patch_attribute(self) -> None:
        code = """
        import mock

        mock.patch("thing")
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS102"))

    def test_mock_import_allowed(self) -> None:
        """Importing Mock itself is allowed, only patch is prohibited."""
        code = """
        from unittest.mock import Mock, MagicMock
        """
        codes = get_error_codes(code)
        assert_that(codes, empty())

    def test_patch_aliased_import(self) -> None:
        code = """
        from unittest.mock import patch as p

        p("module.thing")
        """
        codes = get_error_codes(code)
        # Import flagged, call flagged
        assert_that("LPS102" in codes, equal_to(True))


class TestLPS201ABCProhibited(unittest.TestCase):
    """Tests for LPS201: ABC import is prohibited."""

    def test_import_abc_from_abc(self) -> None:
        code = """
        from abc import ABC
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS201"))

    def test_import_abc_with_alias(self) -> None:
        code = """
        from abc import ABC as AbstractBaseClass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS201"))

    def test_import_abcmeta_allowed(self) -> None:
        """ABCMeta is not explicitly banned (only ABC is)."""
        code = """
        from abc import ABCMeta
        """
        codes = get_error_codes(code)
        assert_that("LPS201" in codes, equal_to(False))


class TestLPS202AbstractMethodProhibited(unittest.TestCase):
    """Tests for LPS202: @abstractmethod is prohibited."""

    def test_import_abstractmethod(self) -> None:
        code = """
        from abc import abstractmethod
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS202"))

    def test_abstractmethod_decorator_direct(self) -> None:
        code = """
        from abc import abstractmethod

        class MyClass:
            @abstractmethod
            def my_method(self):
                pass
        """
        codes = get_error_codes(code)
        # Import + decorator usage
        lps202_count = codes.count("LPS202")
        assert_that(lps202_count, equal_to(2))

    def test_abstractmethod_via_abc_module(self) -> None:
        code = """
        import abc

        class MyClass:
            @abc.abstractmethod
            def my_method(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS202"))


class TestLPS301InitProhibited(unittest.TestCase):
    """Tests for LPS301: __init__ method is prohibited."""

    def test_init_in_regular_class(self) -> None:
        code = """
        class MyClass:
            def __init__(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS301"))

    def test_dataclass_no_explicit_init(self) -> None:
        """Dataclass without explicit __init__ should not trigger LPS301."""
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        # No explicit __init__ in source, so no LPS301
        assert_that("LPS301" in codes, equal_to(False))

    def test_init_explicitly_in_dataclass_flagged(self) -> None:
        """Explicit __init__ in dataclass should be flagged."""
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int

            def __init__(self):
                pass
        """
        codes = get_error_codes(code)
        # Explicit __init__ is flagged even in dataclass
        assert_that(codes, has_item("LPS301"))

    def test_init_in_testcase_allowed(self) -> None:
        """TestCase subclasses may need __init__ for setup."""
        code = """
        import unittest

        class MyTest(unittest.TestCase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
        """
        # Note: This still triggers LPS301 because we can't easily detect TestCase
        # However, TestCase inheritance is allowed via LPS401
        codes = get_error_codes(code)
        # This triggers LPS301 (no special handling for TestCase __init__)
        assert_that("LPS301" in codes, equal_to(True))


class TestLPS302PrivateMethodsProhibited(unittest.TestCase):
    """Tests for LPS302: Private methods are prohibited."""

    def test_private_method(self) -> None:
        code = """
        class MyClass:
            def _private_method(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS302"))

    def test_double_underscore_private(self) -> None:
        code = """
        class MyClass:
            def __very_private(self):
                pass
        """
        # __xxx (not dunder) is still private
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS302"))

    def test_dunder_methods_allowed(self) -> None:
        code = """
        class MyClass:
            def __str__(self):
                return "MyClass"

            def __repr__(self):
                return "MyClass()"

            def __eq__(self, other):
                return True
        """
        codes = get_error_codes(code)
        assert_that("LPS302" in codes, equal_to(False))

    def test_public_method_allowed(self) -> None:
        code = """
        class MyClass:
            def public_method(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that("LPS302" in codes, equal_to(False))


class TestLPS303MethodOnlyPublicAccess(unittest.TestCase):
    """Tests for LPS303: Method only accessing public members should be a function."""

    def test_method_accesses_only_public(self) -> None:
        code = """
        class MyClass:
            def format(self):
                return f"{self.name}: {self.value}"
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS303"))

    def test_method_accesses_private_allowed(self) -> None:
        code = """
        class MyClass:
            def process(self):
                return self._data + 1
        """
        codes = get_error_codes(code)
        assert_that("LPS303" in codes, equal_to(False))

    def test_method_accesses_mixed(self) -> None:
        """If method accesses both public and private, it's allowed."""
        code = """
        class MyClass:
            def process(self):
                return f"{self.name}: {self._internal}"
        """
        codes = get_error_codes(code)
        assert_that("LPS303" in codes, equal_to(False))

    def test_method_no_self_access_allowed(self) -> None:
        """Method that doesn't access self at all doesn't trigger LPS303."""
        code = """
        class MyClass:
            def compute(self):
                return 42
        """
        codes = get_error_codes(code)
        # No self access means no LPS303 (doesn't access self.anything)
        assert_that("LPS303" in codes, equal_to(False))

    def test_dunder_method_exempt(self) -> None:
        """Dunder methods are exempt from LPS303."""
        code = """
        class MyClass:
            def __str__(self):
                return self.name
        """
        codes = get_error_codes(code)
        assert_that("LPS303" in codes, equal_to(False))

    def test_property_exempt(self) -> None:
        """Property methods are exempt from LPS303."""
        code = """
        class MyClass:
            @property
            def name(self):
                return self.first_name + " " + self.last_name
        """
        codes = get_error_codes(code)
        assert_that("LPS303" in codes, equal_to(False))

    def test_classmethod_exempt(self) -> None:
        """Classmethods don't have self, so they're exempt."""
        code = """
        class MyClass:
            @classmethod
            def create(cls):
                return cls()
        """
        codes = get_error_codes(code)
        assert_that("LPS303" in codes, equal_to(False))

    def test_staticmethod_exempt(self) -> None:
        """Staticmethods don't have self."""
        code = """
        class MyClass:
            @staticmethod
            def helper():
                return 42
        """
        codes = get_error_codes(code)
        assert_that("LPS303" in codes, equal_to(False))

    def test_setter_exempt(self) -> None:
        """Property setters are exempt."""
        code = """
        class MyClass:
            @name.setter
            def name(self, value):
                self.first_name = value
        """
        codes = get_error_codes(code)
        assert_that("LPS303" in codes, equal_to(False))


class TestLPS401InheritanceProhibited(unittest.TestCase):
    """Tests for LPS401: Inheritance from concrete classes is prohibited."""

    def test_inherit_from_concrete_class(self) -> None:
        code = """
        class Parent:
            pass

        class Child(Parent):
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS401"))

    def test_inherit_from_protocol_allowed(self) -> None:
        code = """
        from typing import Protocol

        class MyProtocol(Protocol):
            def method(self): ...
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_inherit_from_generic_allowed(self) -> None:
        code = """
        from typing import Generic, TypeVar

        T = TypeVar("T")

        class MyClass(Generic[T]):
            pass
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_inherit_from_exception_allowed(self) -> None:
        code = """
        class MyError(Exception):
            pass
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_inherit_from_base_exception_allowed(self) -> None:
        code = """
        class MyError(BaseException):
            pass
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_inherit_from_testcase_allowed(self) -> None:
        code = """
        import unittest

        class MyTest(unittest.TestCase):
            pass
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_inherit_from_testcase_name_allowed(self) -> None:
        code = """
        from unittest import TestCase

        class MyTest(TestCase):
            pass
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_inherit_from_enum_allowed(self) -> None:
        code = """
        from enum import Enum

        class Color(Enum):
            RED = 1
            GREEN = 2
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_inherit_from_intenum_allowed(self) -> None:
        code = """
        from enum import IntEnum

        class Priority(IntEnum):
            LOW = 1
            HIGH = 2
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_inherit_from_typeddict_allowed(self) -> None:
        code = """
        from typing import TypedDict

        class Movie(TypedDict):
            name: str
            year: int
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_inherit_from_namedtuple_allowed(self) -> None:
        code = """
        from typing import NamedTuple

        class Point(NamedTuple):
            x: int
            y: int
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_multiple_inheritance_mixed(self) -> None:
        code = """
        from typing import Protocol

        class Concrete:
            pass

        class MyClass(Concrete, Protocol):
            pass
        """
        codes = get_error_codes(code)
        # Concrete is not allowed
        assert_that(codes, has_item("LPS401"))

    def test_no_base_class_allowed(self) -> None:
        code = """
        class MyClass:
            pass
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))

    def test_subscripted_generic_allowed(self) -> None:
        code = """
        from typing import Generic, TypeVar

        T = TypeVar("T")

        class Container(Generic[T]):
            pass
        """
        codes = get_error_codes(code)
        assert_that("LPS401" in codes, equal_to(False))


class TestLPS501FrozenDataclass(unittest.TestCase):
    """Tests for LPS501: Dataclass missing frozen=True."""

    def test_dataclass_no_frozen(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS501"))

    def test_dataclass_frozen_false(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=False, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS501"))

    def test_dataclass_frozen_true(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that("LPS501" in codes, equal_to(False))


class TestLPS502SlotsDataclass(unittest.TestCase):
    """Tests for LPS502: Dataclass missing slots=True."""

    def test_dataclass_no_slots(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS502"))

    def test_dataclass_slots_false(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=False, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS502"))

    def test_dataclass_slots_true(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that("LPS502" in codes, equal_to(False))


class TestLPS503KwOnlyDataclass(unittest.TestCase):
    """Tests for LPS503: Dataclass missing kw_only=True."""

    def test_dataclass_no_kw_only(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS503"))

    def test_dataclass_kw_only_false(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=False)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS503"))

    def test_dataclass_kw_only_true(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that("LPS503" in codes, equal_to(False))


class TestDataclassVariants(unittest.TestCase):
    """Tests for dataclass decorator variants."""

    def test_dataclasses_module_prefix(self) -> None:
        code = """
        import dataclasses

        @dataclasses.dataclass
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        # Should detect missing frozen, slots, kw_only
        assert_that(codes, has_item("LPS501"))
        assert_that(codes, has_item("LPS502"))
        assert_that(codes, has_item("LPS503"))

    def test_dataclass_with_all_flags(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        lps50x = [c for c in codes if c.startswith("LPS50")]
        assert_that(lps50x, empty())


class TestComplexScenarios(unittest.TestCase):
    """Tests for complex/edge case scenarios."""

    def test_nested_class(self) -> None:
        code = """
        class Outer:
            class Inner:
                def __init__(self):
                    pass
        """
        codes = get_error_codes(code)
        # Both Outer and Inner have __init__ issues
        assert_that(codes, has_item("LPS301"))

    def test_async_method(self) -> None:
        code = """
        class MyClass:
            async def _private_async(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS302"))

    def test_method_with_public_self_async(self) -> None:
        code = """
        class MyClass:
            async def fetch(self):
                return self.url
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS303"))

    def test_clean_code_no_errors(self) -> None:
        """A well-written class following all conventions."""
        code = """
        from dataclasses import dataclass
        from typing import Protocol

        class DataProvider(Protocol):
            def get_data(self) -> str: ...

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyService:
            provider: DataProvider

            def __str__(self) -> str:
                return f"MyService({self.provider})"

            def __repr__(self) -> str:
                return self.__str__()
        """
        codes = get_error_codes(code)
        # Protocol definition is fine, dataclass is properly configured
        # __str__ and __repr__ are dunders so exempt from LPS303
        assert_that(codes, empty())

    def test_clean_protocol_no_errors(self) -> None:
        """A Protocol definition should not trigger errors."""
        code = """
        from typing import Protocol

        class DataProvider(Protocol):
            def get_data(self) -> str: ...
        """
        codes = get_error_codes(code)
        assert_that(codes, empty())

    def test_clean_dataclass_no_errors(self) -> None:
        """A properly configured dataclass should not trigger errors."""
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class Point:
            x: int
            y: int
        """
        codes = get_error_codes(code)
        assert_that(codes, empty())

    def test_proper_enum_no_errors(self) -> None:
        """An Enum should not trigger errors."""
        code = """
        from enum import Enum

        class Color(Enum):
            RED = 1
            GREEN = 2
            BLUE = 3
        """
        codes = get_error_codes(code)
        assert_that(codes, empty())


class TestErrorMessages(unittest.TestCase):
    """Tests for error message content."""

    def test_lps302_includes_method_name(self) -> None:
        code = """
        class MyClass:
            def _my_private_method(self):
                pass
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors]
        assert_that(messages[0], contains_string("_my_private_method"))

    def test_lps303_includes_method_name(self) -> None:
        code = """
        class MyClass:
            def my_public_method(self):
                return self.value
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "LPS303" in msg]
        assert_that(messages[0], contains_string("my_public_method"))
        assert_that(messages[0], contains_string("functools.singledispatch"))

    def test_lps401_includes_class_names(self) -> None:
        code = """
        class Parent:
            pass

        class Child(Parent):
            pass
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "LPS401" in msg]
        assert_that(messages[0], contains_string("Child"))
        assert_that(messages[0], contains_string("Parent"))

    def test_lps501_includes_class_name(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass
        class MyDataClass:
            x: int
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "LPS501" in msg]
        assert_that(messages[0], contains_string("MyDataClass"))


class TestCheckerMetadata(unittest.TestCase):
    """Tests for checker metadata."""

    def test_checker_name(self) -> None:
        assert_that(Checker.name, equal_to("lint-python-standard"))

    def test_checker_version(self) -> None:
        assert_that(Checker.version, equal_to("0.1.0"))


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and boundary conditions."""

    def test_empty_file(self) -> None:
        code = ""
        codes = get_error_codes(code)
        assert_that(codes, empty())

    def test_module_level_function(self) -> None:
        """Module-level functions should not trigger any errors."""
        code = """
        def my_function():
            pass

        def _private_function():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, empty())

    def test_class_with_only_class_variables(self) -> None:
        code = """
        class Constants:
            VALUE = 42
            NAME = "test"
        """
        codes = get_error_codes(code)
        assert_that(codes, empty())

    def test_import_star_not_flagged(self) -> None:
        """import * shouldn't cause issues."""
        code = """
        from typing import *
        """
        codes = get_error_codes(code)
        assert_that(codes, empty())

    def test_deleter_property_exempt(self) -> None:
        """Property deleters are exempt from LPS303."""
        code = """
        class MyClass:
            @name.deleter
            def name(self):
                del self.first_name
        """
        codes = get_error_codes(code)
        assert_that("LPS303" in codes, equal_to(False))


class TestCoverageEdgeCases(unittest.TestCase):
    """Tests to cover edge cases for 100% coverage."""

    def test_patch_object_via_mock_module_attribute(self) -> None:
        """Test mock.patch.object() detection via attribute chain."""
        code = """
        import unittest.mock

        unittest.mock.patch.object(obj, "attr")
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS102"))

    def test_with_statement_non_call(self) -> None:
        """With statement with non-Call context expression."""
        code = """
        class MyClass:
            pass

        with some_context:
            pass
        """
        codes = get_error_codes(code)
        # Should not crash, no LPS102
        assert_that("LPS102" in codes, equal_to(False))

    def test_with_statement_call_non_name(self) -> None:
        """With statement with Call but func is not Name."""
        code = """
        with obj.method():
            pass
        """
        codes = get_error_codes(code)
        # Should not crash
        assert_that("LPS102" in codes, equal_to(False))

    def test_classmethod_via_attribute(self) -> None:
        """Test @builtins.classmethod detection."""
        code = """
        import builtins

        class MyClass:
            @builtins.classmethod
            def create(cls):
                return cls()
        """
        codes = get_error_codes(code)
        # Should not trigger LPS303 since it's a classmethod
        assert_that("LPS303" in codes, equal_to(False))

    def test_staticmethod_via_attribute(self) -> None:
        """Test @module.staticmethod detection."""
        code = """
        import builtins

        class MyClass:
            @builtins.staticmethod
            def helper():
                return 42
        """
        codes = get_error_codes(code)
        assert_that("LPS303" in codes, equal_to(False))

    def test_dataclass_with_non_constant_kwarg(self) -> None:
        """Dataclass with non-constant keyword argument value."""
        code = """
        from dataclasses import dataclass

        FROZEN = True

        @dataclass(frozen=FROZEN, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        # frozen=FROZEN is not a Constant, so frozen is not detected as True
        assert_that(codes, has_item("LPS501"))

    def test_dataclass_with_extra_kwargs(self) -> None:
        """Dataclass with extra keyword arguments."""
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True, order=True, eq=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        # Should pass - all required kwargs present
        lps50x = [c for c in codes if c.startswith("LPS50")]
        assert_that(lps50x, empty())

    def test_non_dataclass_decorator_call(self) -> None:
        """Class with non-dataclass decorator that is a Call."""
        code = """
        def my_decorator(cls):
            return cls

        @my_decorator
        class MyClass:
            pass
        """
        codes = get_error_codes(code)
        # Should not trigger dataclass checks
        assert_that("LPS501" in codes, equal_to(False))

    def test_base_class_unknown_type(self) -> None:
        """Base class that is not Name, Attribute, or Subscript."""
        code = """
        class MyClass(get_base()):
            pass
        """
        codes = get_error_codes(code)
        # Call as base class - _get_base_name returns None, no LPS401
        assert_that("LPS401" in codes, equal_to(False))

    def test_patch_attribute_not_mock(self) -> None:
        """Attribute named 'patch' but not on mock module."""
        code = """
        class MyPatcher:
            patch = None

        obj = MyPatcher()
        obj.patch
        """
        codes = get_error_codes(code)
        assert_that("LPS102" in codes, equal_to(False))

    def test_attribute_patch_on_non_mock_name(self) -> None:
        """xxx.patch where xxx is not 'mock'."""
        code = """
        something.patch("value")
        """
        codes = get_error_codes(code)
        assert_that("LPS102" in codes, equal_to(False))

    def test_call_with_attribute_func_not_object(self) -> None:
        """Call with attribute func but not 'object' attr."""
        code = """
        from unittest.mock import patch

        patch.dict({})
        """
        codes = get_error_codes(code)
        # Import triggers LPS102, but patch.dict is not patch.object
        # Count should be 1 (just the import)
        lps102_count = codes.count("LPS102")
        assert_that(lps102_count, equal_to(1))

    def test_patch_object_with_non_patch_name(self) -> None:
        """xxx.object() where xxx is not a patch name."""
        code = """
        something.object(1, 2)
        """
        codes = get_error_codes(code)
        assert_that("LPS102" in codes, equal_to(False))

    def test_abstractmethod_aliased(self) -> None:
        """abstractmethod imported with alias."""
        code = """
        from abc import abstractmethod as am

        class MyClass:
            @am
            def method(self):
                pass
        """
        codes = get_error_codes(code)
        # Import triggers LPS202, decorator also triggers
        assert_that("LPS202" in codes, equal_to(True))

    def test_class_with_multiple_decorators(self) -> None:
        """Class with multiple decorators including dataclass."""
        code = """
        from dataclasses import dataclass

        def log_class(cls):
            return cls

        @log_class
        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        lps50x = [c for c in codes if c.startswith("LPS50")]
        assert_that(lps50x, empty())

    def test_method_in_class_not_method(self) -> None:
        """Function in class without self parameter."""
        code = """
        class MyClass:
            def not_a_method():
                pass
        """
        codes = get_error_codes(code)
        # Not a method (no self), so no LPS301/302/303
        assert_that("LPS301" in codes, equal_to(False))
        assert_that("LPS302" in codes, equal_to(False))
        assert_that("LPS303" in codes, equal_to(False))

    def test_async_method_with_private_access(self) -> None:
        """Async method accessing private state."""
        code = """
        class MyClass:
            async def fetch(self):
                return self._data
        """
        codes = get_error_codes(code)
        # Accesses private state, so no LPS303
        assert_that("LPS303" in codes, equal_to(False))

    def test_abstractmethod_decorator_with_import_abc(self) -> None:
        """@abc.abstractmethod when abc module is imported."""
        code = """
        import abc

        class MyInterface:
            @abc.abstractmethod
            def method(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS202"))

    def test_call_func_is_attribute_not_object(self) -> None:
        """Call where func is Attribute but attr is not 'object'."""
        code = """
        from unittest.mock import patch

        x = patch.something("module")
        """
        codes = get_error_codes(code)
        # Only import should trigger
        lps102_count = codes.count("LPS102")
        assert_that(lps102_count, equal_to(1))

    def test_import_patch_among_multiple(self) -> None:
        """Import patch among other imports from unittest.mock."""
        code = """
        from unittest.mock import Mock, patch, MagicMock
        """
        codes = get_error_codes(code)
        # Only patch should trigger LPS102
        lps102_count = codes.count("LPS102")
        assert_that(lps102_count, equal_to(1))

    def test_staticmethod_via_attribute_with_self(self) -> None:
        """Test @module.staticmethod on a method with self param.

        This covers the branch in _is_classmethod_or_staticmethod for Attribute.
        """
        code = """
        class MyClass:
            @types.staticmethod
            def helper(self):
                return self.value
        """
        codes = get_error_codes(code)
        # Should not trigger LPS302 or LPS303 since it's a staticmethod
        assert_that("LPS302" in codes, equal_to(False))
        assert_that("LPS303" in codes, equal_to(False))

    def test_classmethod_via_attribute_with_self(self) -> None:
        """Test @module.classmethod on a method with self param.

        This covers the branch in _is_classmethod_or_staticmethod for Attribute.
        """
        code = """
        class MyClass:
            @functools.classmethod
            def create(self):
                return self
        """
        codes = get_error_codes(code)
        # Should skip classmethod/staticmethod check
        assert_that("LPS303" in codes, equal_to(False))

    def test_abstractmethod_on_class_decorator(self) -> None:
        """Test @abstractmethod on class (unusual but should be caught)."""
        code = """
        from abc import abstractmethod

        @abstractmethod
        class MyClass:
            pass
        """
        codes = get_error_codes(code)
        # Should have at least 2 LPS202 - import and decorator
        lps202_count = codes.count("LPS202")
        assert_that(lps202_count, equal_to(2))

    def test_decorator_not_name_or_attribute_or_call(self) -> None:
        """Decorator that is not Name, Attribute, or Call."""
        code = """
        class MyClass:
            @(some_list[0])
            def method(self):
                return self.value
        """
        codes = get_error_codes(code)
        # Subscript decorator should not crash
        # Method still triggers LPS303
        assert_that("LPS303" in codes, equal_to(True))

    def test_attribute_patch_on_nested_attribute(self) -> None:
        """Test deeply nested attribute access for patch."""
        code = """
        import unittest

        unittest.mock.patch("thing")
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("LPS102"))

    def test_call_object_on_non_patch_attribute(self) -> None:
        """Test xxx.object() where xxx is not patch."""
        code = """
        factory.object(MyClass)
        """
        codes = get_error_codes(code)
        assert_that("LPS102" in codes, equal_to(False))

    def test_with_non_patch_function_call(self) -> None:
        """Test with statement calling function that's not patch."""
        code = """
        from unittest.mock import patch

        with open("file.txt"):
            pass
        """
        codes = get_error_codes(code)
        # Only the import should trigger
        lps102_count = codes.count("LPS102")
        assert_that(lps102_count, equal_to(1))

    def test_decorator_that_is_not_dataclass_but_is_call(self) -> None:
        """Test that random Call decorators don't trigger dataclass checks."""
        code = """
        @some_random_decorator()
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        # Should NOT have LPS501/502/503 since it's not a dataclass
        assert_that("LPS501" in codes, equal_to(False))
        assert_that("LPS502" in codes, equal_to(False))
        assert_that("LPS503" in codes, equal_to(False))

    def test_method_decorator_attribute_not_abstractmethod(self) -> None:
        """Decorator that is Attribute but not abstractmethod."""
        code = """
        class MyClass:
            @some_module.some_decorator
            def method(self):
                return self.value
        """
        codes = get_error_codes(code)
        # Should trigger LPS303 (public access only)
        assert_that(codes, has_item("LPS303"))

    def test_patch_object_via_attribute_value_name_not_patch(self) -> None:
        """Test xxx.object() where xxx is Name but not in patch_names."""
        code = """
        something.object(obj, "attr")
        """
        codes = get_error_codes(code)
        assert_that("LPS102" in codes, equal_to(False))

    def test_patch_object_via_deeply_nested_attribute(self) -> None:
        """Test a.b.patch.object() detection."""
        code = """
        import unittest

        unittest.mock.patch.object(obj, "attr")
        """
        codes = get_error_codes(code)
        # Should detect patch.object
        assert_that(codes, has_item("LPS102"))

    def test_staticmethod_name_with_self_param(self) -> None:
        """Test @staticmethod (Name) on method with self parameter.

        This is unusual but valid Python - covers line 133 in
        _is_classmethod_or_staticmethod.
        """
        code = """
        class MyClass:
            @staticmethod
            def method(self):
                return self
        """
        codes = get_error_codes(code)
        # Should not trigger LPS303 since it's detected as staticmethod
        assert_that("LPS303" in codes, equal_to(False))

    def test_classmethod_name_with_self_param(self) -> None:
        """Test @classmethod (Name) on method with self parameter.

        Unusual but valid - covers line 133 branch.
        """
        code = """
        class MyClass:
            @classmethod
            def method(self):
                return self
        """
        codes = get_error_codes(code)
        # Should not trigger LPS303 since it's detected as classmethod
        assert_that("LPS303" in codes, equal_to(False))

    def test_class_decorator_is_subscript(self) -> None:
        """Class decorator that is a Subscript (not Name/Attribute/Call).

        Covers line 83 in _is_dataclass_decorator returning False.
        """
        code = """
        decorators = [lambda x: x]

        @decorators[0]
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        # Should NOT trigger dataclass checks since decorator is Subscript
        assert_that("LPS501" in codes, equal_to(False))
        assert_that("LPS502" in codes, equal_to(False))
        assert_that("LPS503" in codes, equal_to(False))

    def test_attribute_patch_nested_not_mock(self) -> None:
        """Test foo.bar.patch where bar is not 'mock'.

        Covers branch 257->exit in _check_attribute.
        """
        code = """
        foo.bar.patch
        """
        codes = get_error_codes(code)
        # node.attr == "patch", node.value is Attribute, but node.value.attr != "mock"
        assert_that("LPS102" in codes, equal_to(False))

    def test_call_func_attribute_not_object(self) -> None:
        """Test func.something() where attr is not 'object'.

        Covers branch 288->exit in _check_call.
        """
        code = """
        from unittest.mock import patch

        result = patch.dict({})
        """
        codes = get_error_codes(code)
        # func is Attribute with attr="dict", not "object"
        # Only the import triggers
        lps102_count = codes.count("LPS102")
        assert_that(lps102_count, equal_to(1))

    def test_call_object_func_value_attribute_not_patch(self) -> None:
        """Test xxx.yyy.object() where yyy is not 'patch'.

        Covers branches 298->exit and 299->exit in _check_call.
        """
        code = """
        foo.bar.object(thing)
        """
        codes = get_error_codes(code)
        # func.attr == "object", func.value is Attribute, but func.value.attr != "patch"
        assert_that("LPS102" in codes, equal_to(False))

    def test_call_object_func_value_name_not_patch(self) -> None:
        """Test notpatch.object() - func.value is Name but not in patch_names.

        Covers branch 291->292 false path in _check_call.
        """
        code = """
        factory.object(MyClass)
        """
        codes = get_error_codes(code)
        # func.attr == "object", func.value is Name "factory", not in patch_names
        assert_that("LPS102" in codes, equal_to(False))
