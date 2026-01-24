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
