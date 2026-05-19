"""Tests for SLD6xx error codes (code limits)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, equal_to, has_item

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


def _dataclass_with_fields(n: int) -> str:
    lines = [
        "from dataclasses import dataclass",
        "",
        "@dataclass(frozen=True, slots=True, kw_only=True)",
        "class Big:",
    ]
    lines.extend(f"    f{i}: int" for i in range(n))
    return "\n".join(lines) + "\n"


_SLD608_PRESENT: list[tuple[str, str]] = [
    ("dataclass_exceeds_limit", _dataclass_with_fields(11)),
]


_SLD608_ABSENT: list[tuple[str, str]] = [
    ("dataclass_within_limit", _dataclass_with_fields(10)),
    (
        "classvar_not_counted",
        "from dataclasses import dataclass\n"
        "from typing import ClassVar\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class Mixed:\n"
        + "\n".join(f"    f{i}: int" for i in range(10))
        + "\n    counter: ClassVar[int] = 0\n"
        + "    flag: ClassVar[bool] = False\n",
    ),
    (
        "non_dataclass_unrestricted",
        "class Plain:\n" + "\n".join(f"    f{i}: int" for i in range(20)) + "\n",
    ),
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


class TestSLD608DataclassFieldLimit(unittest.TestCase):
    """Tests for SLD608: Dataclass exceeds field limit."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD608_PRESENT, "SLD608")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD608_ABSENT, "SLD608")

    def test_error_message_includes_field_count(self) -> None:
        """Verify error message includes field count and limit."""
        errors = check_code(_dataclass_with_fields(12))
        messages = [msg for _, _, msg in errors if "SLD608" in msg]
        for expected in ("12", "10", "Big"):
            with self.subTest(expected=expected):
                assert_that(messages[0], contains_string(expected))


_SLD605_PRESENT: list[tuple[str, str]] = [
    (
        "two_level_direct_nest",
        "with a() as x:\n" "    with b(x) as y:\n" "        do(y)\n",
    ),
    (
        "stuff_between_then_inner_last",
        "with a() as x:\n"
        "    t = step(x)\n"
        "    with b(t) as y:\n"
        "        do(y)\n",
    ),
    (
        "trailing_outside_nest_is_fine",
        "with a() as x:\n" "    with b(x) as y:\n" "        do(y)\n" "print('done')\n",
    ),
    (
        "nested_inside_function_body",
        "def run():\n"
        "    with a() as x:\n"
        "        with b(x) as y:\n"
        "            do(y)\n",
    ),
    (
        "multi_item_outer_still_nests",
        "with a() as x, c() as z:\n" "    with b(x) as y:\n" "        do(y)\n",
    ),
]


_SLD605_ABSENT: list[tuple[str, str]] = [
    ("single_with", "with a() as x:\n    do(x)\n"),
    ("multi_item_with_no_nest", "with a() as x, b() as y:\n    do(x, y)\n"),
    (
        "stuff_after_inner_with",
        "with a() as x:\n" "    with b(x) as y:\n" "        do(y)\n" "    after(x)\n",
    ),
    (
        "inner_with_inside_if_not_last",
        "with a() as x:\n"
        "    if cond(x):\n"
        "        with b(x) as y:\n"
        "            do(y)\n",
    ),
    (
        "async_inner_is_not_sync_nest",
        "async def run():\n"
        "    with a() as x:\n"
        "        async with b(x) as y:\n"
        "            do(y)\n",
    ),
    (
        "siblings_not_nested",
        "with a() as x:\n" "    do(x)\n" "with b() as y:\n" "    do(y)\n",
    ),
]


_SLD605_COUNT: list[tuple[str, str, int]] = [
    (
        "triple_nest_counts_two",
        "with a() as x:\n"
        "    with b(x) as y:\n"
        "        with c(y) as z:\n"
        "            do(z)\n",
        2,
    ),
    (
        "two_independent_nests",
        "with a() as x:\n"
        "    with b(x) as y:\n"
        "        do(y)\n"
        "with c() as p:\n"
        "    with d(p) as q:\n"
        "        do(q)\n",
        2,
    ),
]


class TestSLD605NestedWith(unittest.TestCase):
    """Tests for SLD605: nested ``with`` flattenable to ``ExitStack``."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD605_PRESENT, "SLD605")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD605_ABSENT, "SLD605")

    def test_count(self) -> None:
        """Verify count."""
        for name, code, count in _SLD605_COUNT:
            with self.subTest(name=name):
                assert_that(
                    get_error_codes(code).count("SLD605"),
                    equal_to(count),
                )

    def test_message_mentions_exitstack(self) -> None:
        """Verify the SLD605 message points at contextlib.ExitStack."""
        code = "with a() as x:\n" "    with b(x) as y:\n" "        do(y)\n"
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD605" in msg]
        assert_that(messages[0], contains_string("ExitStack"))
