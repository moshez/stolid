"""Tests for edge cases, error messages, and complex scenarios."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, empty, equal_to, has_item

from ..checker import Checker
from .code_parser import check_code, get_error_codes


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
        assert_that(codes, has_item("SLD301"))

    def test_async_method(self) -> None:
        code = """
        class MyClass:
            async def _private_async(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD302"))

    def test_method_with_public_self_async(self) -> None:
        code = """
        class MyClass:
            async def fetch(self):
                return self.url
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD303"))

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
        # __str__ and __repr__ are dunders so exempt from SLD303
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

    def test_stolid302_includes_method_name(self) -> None:
        code = """
        class MyClass:
            def _my_private_method(self):
                pass
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors]
        assert_that(messages[0], contains_string("_my_private_method"))

    def test_stolid303_includes_method_name(self) -> None:
        code = """
        class MyClass:
            def my_public_method(self):
                return self.value
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD303" in msg]
        assert_that(messages[0], contains_string("my_public_method"))
        assert_that(messages[0], contains_string("functools.singledispatch"))

    def test_stolid401_includes_class_names(self) -> None:
        code = """
        class Parent:
            pass

        class Child(Parent):
            pass
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD401" in msg]
        assert_that(messages[0], contains_string("Child"))
        assert_that(messages[0], contains_string("Parent"))

    def test_stolid501_includes_class_name(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass
        class MyDataClass:
            x: int
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD501" in msg]
        assert_that(messages[0], contains_string("MyDataClass"))


class TestCheckerMetadata(unittest.TestCase):
    """Tests for checker metadata."""

    def test_checker_name(self) -> None:
        assert_that(Checker.name, equal_to("stolid"))

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
        """Property deleters are exempt from SLD303."""
        code = """
        class MyClass:
            @name.deleter
            def name(self):
                del self.first_name
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))
