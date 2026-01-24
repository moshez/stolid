"""Tests for SLD4xx error codes (inheritance related)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, has_item

from .code_parser import get_error_codes


class TestSLD401InheritanceProhibited(unittest.TestCase):
    """Tests for SLD401: Inheritance from concrete classes is prohibited."""

    def test_inherit_from_concrete_class(self) -> None:
        code = """
        class Parent:
            pass

        class Child(Parent):
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD401"))

    def test_inherit_from_protocol_allowed(self) -> None:
        code = """
        from typing import Protocol

        class MyProtocol(Protocol):
            def method(self): ...
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_inherit_from_generic_allowed(self) -> None:
        code = """
        from typing import Generic, TypeVar

        T = TypeVar("T")

        class MyClass(Generic[T]):
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_inherit_from_exception_allowed(self) -> None:
        code = """
        class MyError(Exception):
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_inherit_from_base_exception_allowed(self) -> None:
        code = """
        class MyError(BaseException):
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_inherit_from_testcase_allowed(self) -> None:
        code = """
        import unittest

        class MyTest(unittest.TestCase):
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_inherit_from_testcase_name_allowed(self) -> None:
        code = """
        from unittest import TestCase

        class MyTest(TestCase):
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_inherit_from_enum_allowed(self) -> None:
        code = """
        from enum import Enum

        class Color(Enum):
            RED = 1
            GREEN = 2
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_inherit_from_intenum_allowed(self) -> None:
        code = """
        from enum import IntEnum

        class Priority(IntEnum):
            LOW = 1
            HIGH = 2
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_inherit_from_typeddict_allowed(self) -> None:
        code = """
        from typing import TypedDict

        class Movie(TypedDict):
            name: str
            year: int
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_inherit_from_namedtuple_allowed(self) -> None:
        code = """
        from typing import NamedTuple

        class Point(NamedTuple):
            x: int
            y: int
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

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
        assert_that(codes, has_item("SLD401"))

    def test_no_base_class_allowed(self) -> None:
        code = """
        class MyClass:
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_subscripted_generic_allowed(self) -> None:
        code = """
        from typing import Generic, TypeVar

        T = TypeVar("T")

        class Container(Generic[T]):
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))

    def test_base_class_unknown_type(self) -> None:
        """Base class that is not Name, Attribute, or Subscript."""
        code = """
        class MyClass(get_base()):
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD401" in codes, equal_to(False))
