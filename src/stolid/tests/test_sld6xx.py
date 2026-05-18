"""Tests for SLD6xx error codes (code limits)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, has_item

from .code_parser import (
    assert_absent,
    assert_present,
    check_code,
    get_error_codes,
)


def _function_body(decl: str, n: int) -> str:
    body = [f"    x{i} = {i}" for i in range(n)]
    return decl + "\n" + "\n".join(body) + "\n    return x0\n"


def _method_body(n: int) -> str:
    body = [f"        x{i} = {i}" for i in range(n)]
    return (
        "class MyClass:\n    def long_method(self):\n"
        + "\n".join(body)
        + "\n        return self\n"
    )


def _nested_function(depth: int, body_lines: int) -> str:
    # Build a function whose body sits at ``depth`` indent levels of if-nesting.
    head = "def deeply_nested():\n"
    nesting = "".join("    " * (i + 1) + f"if x{i}:\n" for i in range(depth))
    inner_indent = "    " * (depth + 1)
    body = "\n".join(f"{inner_indent}y{i} = {i}" for i in range(body_lines))
    return head + nesting + body + "\n"


def _bracket_heavy_function(lines: int) -> str:
    # Each body line opens three nested brackets on itself.
    body = "\n".join(f"    r{i} = foo(bar([baz({i})]))" for i in range(lines))
    return "def bracket_heavy():\n" + body + "\n"


_SLD601_PRESENT: list[tuple[str, str]] = [
    ("function_exceeds_limit", _function_body("def long_function():", 35)),
    ("method_exceeds_limit", _method_body(35)),
    ("async_function_exceeds_limit", _function_body("async def long_async():", 35)),
    # 4-deep nesting at ~10 lines blows the weighted budget.
    ("deep_nesting_exceeds_limit", _nested_function(depth=4, body_lines=10)),
    # 3 nested brackets per line gives bracket extra of 2 per line.
    ("bracket_nesting_exceeds_limit", _bracket_heavy_function(20)),
]


_SLD602_PRESENT: list[tuple[str, str]] = [
    ("function_exceeds_limit", "def func(a, b, c, d, e):\n    pass\n"),
    ("kwonly_args_counted", "def func(a, b, *, c, d, e):\n    pass\n"),
    ("posonly_args_counted", "def func(a, b, c, /, d, e):\n    pass\n"),
]


_SLD602_ABSENT: list[tuple[str, str]] = [
    ("function_within_limit", "def func(a, b, c, d):\n    pass\n"),
    (
        "method_self_not_counted",
        "class MyClass:\n    def method(self, a, b, c, d):\n        pass\n",
    ),
    (
        "classmethod_cls_not_counted",
        "class MyClass:\n    @classmethod\n"
        "    def method(cls, a, b, c, d):\n        pass\n",
    ),
]


def _big_class() -> str:
    lines = ["class BigClass:"]
    for i in range(20):
        lines.append(f"    def method{i}(self): pass")
    return "\n".join(lines) + "\n"


_DUNDERS = (
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
)


def _class_with_many_dunders() -> str:
    dunder_lines = [f"    def {d}(self): pass" for d in _DUNDERS]
    method_lines = [f"    def method{i}(self): pass" for i in range(15)]
    return "\n".join(["class MyClass:", *dunder_lines, *method_lines]) + "\n"


def _long_module(n: int) -> str:
    return "\n".join(f"x{i} = {i}" for i in range(n)) + "\n"


def _blank_padded_function(blanks: int) -> str:
    # A short function padded with blank lines that should not be counted.
    head = "def padded():\n    x = 1\n"
    pad = "\n" * blanks
    return head + pad + "    return x\n"


def _comment_padded_function(comments: int) -> str:
    # A short function padded with comment-only lines (each weighs 1 flat).
    head = "def padded():\n    x = 1\n"
    pad = "\n".join("    # noted" for _ in range(comments)) + "\n"
    return head + pad + "    return x\n"


_SLD601_ABSENT: list[tuple[str, str]] = [
    ("short_function", "def short_function():\n    x = 1\n    return x\n"),
    # 200 blank lines weigh 0; the body has 2 real lines.
    ("blank_lines_not_counted", _blank_padded_function(200)),
    # 25 comment lines + 2 real lines = 27, under the budget of 30.
    ("comments_unweighted", _comment_padded_function(25)),
]


_SLD603_ABSENT: list[tuple[str, str]] = [
    (
        "class_within_limit",
        "class MyClass:\n    def method1(self): pass\n"
        "    def method2(self): pass\n    def method3(self): pass\n",
    ),
    ("dunders_not_counted", _class_with_many_dunders()),
]


_SLD604_ABSENT: list[tuple[str, str]] = [
    ("short_module", "x = 1\ny = 2\n"),
]


class TestSLD601FunctionLineLimit(unittest.TestCase):
    """Tests for SLD601: Function exceeds weighted line budget."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD601_PRESENT, "SLD601")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD601_ABSENT, "SLD601")

    def test_message_reports_heaviest_line(self) -> None:
        """Verify the SLD601 message names the heaviest line and its breakdown."""
        code = _nested_function(depth=4, body_lines=10)
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD601" in msg]
        assert_that(messages[0], contains_string("complexity"))
        assert_that(messages[0], contains_string("heaviest line"))
        assert_that(messages[0], contains_string("indent depth"))


class TestSLD602ArgumentLimit(unittest.TestCase):
    """Tests for SLD602: Function exceeds argument limit."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD602_PRESENT, "SLD602")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD602_ABSENT, "SLD602")


class TestSLD603ClassMethodLimit(unittest.TestCase):
    """Tests for SLD603: Class exceeds method limit."""

    def test_class_exceeds_limit(self) -> None:
        """Verify class exceeds limit."""
        assert_that(get_error_codes(_big_class()), has_item("SLD603"))

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD603_ABSENT, "SLD603")


class TestSLD604ModuleLineLimit(unittest.TestCase):
    """Tests for SLD604: Module exceeds line limit."""

    def test_module_exceeds_limit(self) -> None:
        """Verify module exceeds limit."""
        assert_that(get_error_codes(_long_module(450)), has_item("SLD604"))

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD604_ABSENT, "SLD604")

    def test_error_message_includes_line_count(self) -> None:
        """Verify error message includes line count."""
        errors = check_code(_long_module(450))
        messages = [msg for _, _, msg in errors if "SLD604" in msg]
        for expected in ("450", "400"):
            with self.subTest(expected=expected):
                assert_that(messages[0], contains_string(expected))
