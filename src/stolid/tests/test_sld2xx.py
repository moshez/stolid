"""Tests for SLD2xx error codes (ABC and abstractmethod related)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, has_item

from .code_parser import get_error_codes


class TestSLD201ABCProhibited(unittest.TestCase):
    """Tests for SLD201: ABC import is prohibited."""

    def test_import_abc_from_abc(self) -> None:
        code = """
        from abc import ABC
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD201"))

    def test_import_abc_with_alias(self) -> None:
        code = """
        from abc import ABC as AbstractBaseClass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD201"))

    def test_import_abcmeta_allowed(self) -> None:
        """ABCMeta is not explicitly banned (only ABC is)."""
        code = """
        from abc import ABCMeta
        """
        codes = get_error_codes(code)
        assert_that("SLD201" in codes, equal_to(False))


class TestSLD202AbstractMethodProhibited(unittest.TestCase):
    """Tests for SLD202: @abstractmethod is prohibited."""

    def test_import_abstractmethod(self) -> None:
        code = """
        from abc import abstractmethod
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD202"))

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
        lps202_count = codes.count("SLD202")
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
        assert_that(codes, has_item("SLD202"))

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
        assert_that("SLD202" in codes, equal_to(True))

    def test_abstractmethod_on_class_decorator(self) -> None:
        """Test @abstractmethod on class (unusual but should be caught)."""
        code = """
        from abc import abstractmethod

        @abstractmethod
        class MyClass:
            pass
        """
        codes = get_error_codes(code)
        lps202_count = codes.count("SLD202")
        assert_that(lps202_count, equal_to(2))

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
        assert_that(codes, has_item("SLD202"))


class TestSLD203CastProhibited(unittest.TestCase):
    """Tests for SLD203: typing.cast is prohibited."""

    def test_cast_from_typing(self) -> None:
        code = """
        from typing import cast
        x = cast(int, value)
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD203"))

    def test_cast_aliased(self) -> None:
        """cast imported with alias is still flagged."""
        code = """
        from typing import cast as as_type
        x = as_type(int, value)
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD203"))

    def test_cast_via_typing_module(self) -> None:
        """typing.cast attribute access is flagged."""
        code = """
        import typing
        x = typing.cast(int, value)
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD203"))

    def test_non_typing_cast_allowed(self) -> None:
        """A function called cast from somewhere else is not flagged."""
        code = """
        from mylib import cast
        x = cast(value)
        """
        codes = get_error_codes(code)
        assert_that("SLD203" in codes, equal_to(False))

    def test_other_module_cast_attribute_allowed(self) -> None:
        """somemodule.cast (not typing.cast) is not flagged."""
        code = """
        import other
        x = other.cast(int, value)
        """
        codes = get_error_codes(code)
        assert_that("SLD203" in codes, equal_to(False))

    def test_no_cast_usage(self) -> None:
        code = """
        from typing import List
        x: List[int] = []
        """
        codes = get_error_codes(code)
        assert_that("SLD203" in codes, equal_to(False))
