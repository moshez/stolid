"""Tests for SLD6xx error codes (code limits)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, equal_to, has_item

from .code_parser import check_code, get_error_codes


class TestSLD601FunctionLineLimit(unittest.TestCase):
    """Tests for SLD601: Function exceeds line limit."""

    def test_function_within_limit(self) -> None:
        code = """
        def short_function():
            x = 1
            return x
        """
        codes = get_error_codes(code)
        assert_that("SLD601" in codes, equal_to(False))

    def test_function_exceeds_limit(self) -> None:
        lines = ["def long_function():"]
        for i in range(35):
            lines.append(f"    x{i} = {i}")
        lines.append("    return x0")
        code = "\n".join(lines)
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD601"))

    def test_method_exceeds_limit(self) -> None:
        lines = ["class MyClass:"]
        lines.append("    def long_method(self):")
        for i in range(35):
            lines.append(f"        x{i} = {i}")
        lines.append("        return self")
        code = "\n".join(lines)
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD601"))

    def test_async_function_exceeds_limit(self) -> None:
        lines = ["async def long_async():"]
        for i in range(35):
            lines.append(f"    x{i} = {i}")
        lines.append("    return x0")
        code = "\n".join(lines)
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD601"))


class TestSLD602ArgumentLimit(unittest.TestCase):
    """Tests for SLD602: Function exceeds argument limit."""

    def test_function_within_limit(self) -> None:
        code = """
        def func(a, b, c, d):
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD602" in codes, equal_to(False))

    def test_function_exceeds_limit(self) -> None:
        code = """
        def func(a, b, c, d, e):
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD602"))

    def test_method_self_not_counted(self) -> None:
        code = """
        class MyClass:
            def method(self, a, b, c, d):
                pass
        """
        codes = get_error_codes(code)
        assert_that("SLD602" in codes, equal_to(False))

    def test_classmethod_cls_not_counted(self) -> None:
        code = """
        class MyClass:
            @classmethod
            def method(cls, a, b, c, d):
                pass
        """
        codes = get_error_codes(code)
        assert_that("SLD602" in codes, equal_to(False))

    def test_kwonly_args_counted(self) -> None:
        code = """
        def func(a, b, *, c, d, e):
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD602"))

    def test_posonly_args_counted(self) -> None:
        code = """
        def func(a, b, c, /, d, e):
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD602"))


class TestSLD603ClassMethodLimit(unittest.TestCase):
    """Tests for SLD603: Class exceeds method limit."""

    def test_class_within_limit(self) -> None:
        code = """
        class MyClass:
            def method1(self): pass
            def method2(self): pass
            def method3(self): pass
        """
        codes = get_error_codes(code)
        assert_that("SLD603" in codes, equal_to(False))

    def test_class_exceeds_limit(self) -> None:
        lines = ["class BigClass:"]
        for i in range(20):
            lines.append(f"    def method{i}(self): pass")
        code = "\n".join(lines)
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD603"))

    def test_dunders_not_counted(self) -> None:
        lines = ["class MyClass:"]
        # Add 15 dunders
        dunders = [
            "__str__",
            "__repr__",
            "__eq__",
            "__ne__",
            "__lt__",
            "__le__",
            "__gt__",
            "__ge__",
            "__hash__",
            "__bool__",
            "__len__",
            "__getitem__",
            "__setitem__",
            "__delitem__",
            "__iter__",
            "__contains__",
            "__call__",
        ]
        for dunder in dunders:
            lines.append(f"    def {dunder}(self): pass")
        # Add exactly 15 regular methods (the limit)
        for i in range(15):
            lines.append(f"    def method{i}(self): pass")
        code = "\n".join(lines)
        codes = get_error_codes(code)
        assert_that("SLD603" in codes, equal_to(False))


class TestSLD604ModuleLineLimit(unittest.TestCase):
    """Tests for SLD604: Module exceeds line limit."""

    def test_module_within_limit(self) -> None:
        code = """
        x = 1
        y = 2
        """
        codes = get_error_codes(code)
        assert_that("SLD604" in codes, equal_to(False))

    def test_module_exceeds_limit(self) -> None:
        lines = []
        for i in range(450):
            lines.append(f"x{i} = {i}")
        code = "\n".join(lines)
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD604"))

    def test_error_message_includes_line_count(self) -> None:
        lines = []
        for i in range(450):
            lines.append(f"x{i} = {i}")
        code = "\n".join(lines)
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD604" in msg]
        assert_that(messages[0], contains_string("450"))
        assert_that(messages[0], contains_string("400"))
