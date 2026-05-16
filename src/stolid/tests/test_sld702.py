"""Tests for SLD702: Global names shadowing builtins/typing/stdlib."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, equal_to, has_item

from .code_parser import check_code, get_error_codes


class TestSLD702BuiltinShadow(unittest.TestCase):
    """Tests for SLD702: shadowing builtin names."""

    def test_function_named_after_builtin(self) -> None:
        code = """
        def list():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD702"))

    def test_class_named_after_builtin(self) -> None:
        code = """
        class list:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD702"))

    def test_assign_to_builtin_name(self) -> None:
        code = """
        list = 5
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD702"))

    def test_annotated_assign_to_builtin_name(self) -> None:
        code = """
        list: int = 0
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD702"))

    def test_tuple_unpacking_with_builtin_name(self) -> None:
        code = """
        list, other = 1, 2
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD702"))


class TestSLD702TypingShadow(unittest.TestCase):
    """Tests for SLD702: shadowing typing names."""

    def test_function_named_after_typing(self) -> None:
        code = """
        def List():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD702"))


class TestSLD702StdlibShadow(unittest.TestCase):
    """Tests for SLD702: shadowing stdlib module names."""

    def test_function_named_after_stdlib_module(self) -> None:
        code = """
        def sys():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD702"))

    def test_class_named_after_stdlib_module(self) -> None:
        code = """
        class json:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD702"))


class TestSLD702Allowed(unittest.TestCase):
    """Tests for SLD702: cases that should not trigger."""

    def test_normal_function_name(self) -> None:
        code = """
        def my_function():
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD702" in codes, equal_to(False))

    def test_import_of_stdlib_not_flagged(self) -> None:
        """`import sys` brings in `sys` but isn't a definition."""
        code = """
        import sys
        """
        codes = get_error_codes(code)
        assert_that("SLD702" in codes, equal_to(False))

    def test_from_import_not_flagged(self) -> None:
        """`from typing import List` isn't a definition of List."""
        code = """
        from typing import List
        """
        codes = get_error_codes(code)
        assert_that("SLD702" in codes, equal_to(False))

    def test_nested_function_not_flagged(self) -> None:
        """Functions inside other functions are not module-level."""
        code = """
        def outer():
            def list():
                pass
        """
        codes = get_error_codes(code)
        assert_that("SLD702" in codes, equal_to(False))

    def test_method_not_flagged(self) -> None:
        """Methods inside classes are not module-level definitions."""
        code = """
        class MyClass:
            def list(self):
                return self._items
        """
        codes = get_error_codes(code)
        assert_that("SLD702" in codes, equal_to(False))

    def test_attribute_assign_not_flagged(self) -> None:
        """Assignment to obj.list isn't a module-level Name target."""
        code = """
        config.list = 5
        """
        codes = get_error_codes(code)
        assert_that("SLD702" in codes, equal_to(False))


class TestSLD702ErrorMessage(unittest.TestCase):
    """Tests for SLD702 error message content."""

    def test_message_includes_name_and_builtin(self) -> None:
        code = """
        def list():
            pass
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD702" in msg]
        assert_that(messages[0], contains_string("'list'"))
        assert_that(messages[0], contains_string("builtin"))

    def test_message_for_typing_name(self) -> None:
        code = """
        def Optional():
            pass
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD702" in msg]
        assert_that(messages[0], contains_string("typing.Optional"))

    def test_message_for_stdlib_name(self) -> None:
        code = """
        def os():
            pass
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD702" in msg]
        assert_that(messages[0], contains_string("stdlib module 'os'"))
