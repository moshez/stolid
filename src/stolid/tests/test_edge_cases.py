"""Tests for edge cases, error messages, and complex scenarios."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, empty, equal_to, has_item

from ..checker import Checker
from .code_parser import check_code, get_error_codes

_NESTED_AND_ASYNC_PRESENT: list[tuple[str, str, str]] = [
    (
        "nested_class_init",
        "class Outer:\n    class Inner:\n        def __init__(self):\n"
        "            pass\n",
        "SLD301",
    ),
    (
        "async_private_method",
        "class MyClass:\n    async def _private_async(self):\n        pass\n",
        "SLD302",
    ),
    (
        "async_public_method_no_private_access",
        "class MyClass:\n    async def fetch(self):\n        return self.url\n",
        "SLD303",
    ),
]


_CLEAN_NO_ERRORS: list[tuple[str, str]] = [
    (
        "well_written_class",
        "from dataclasses import dataclass\nfrom typing import Protocol\n\n"
        "class DataProvider(Protocol):\n"
        '    """A provider."""\n'
        "    def get_data(self) -> str:\n"
        '        """Return the data."""\n        ...\n\n'
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class MyService:\n"
        '    """Hold a ``provider``."""\n'
        "    provider: DataProvider\n\n"
        "    def __str__(self) -> str:\n"
        "        return f'MyService({self.provider})'\n\n"
        "    def __repr__(self) -> str:\n        return self.__str__()\n",
    ),
    (
        "protocol_definition",
        "from typing import Protocol\n\n"
        "class DataProvider(Protocol):\n"
        '    """A provider."""\n'
        "    def get_data(self) -> str:\n"
        '        """Return the data."""\n        ...\n',
    ),
    (
        "proper_dataclass",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class Rect:\n"
        '    """Holds ``width`` and ``height``."""\n'
        "    width: int\n    height: int\n",
    ),
    (
        "proper_enum",
        "from enum import Enum\n\n"
        "class Color(Enum):\n"
        '    """Colors of a stoplight."""\n'
        "    RED = 1\n    GREEN = 2\n    BLUE = 3\n",
    ),
    ("empty_file", ""),
    (
        "module_level_function",
        'def my_function() -> None:\n    """Do my thing."""\n    pass\n\n'
        "def _private_function():\n    pass\n",
    ),
    ("import_star", "from typing import *\n"),
]


_ERROR_MESSAGE_CASES: list[tuple[str, str, str, str]] = [
    (
        "sld302_method_name",
        "class MyClass:\n    def _my_private_method(self):\n        pass\n",
        "SLD302",
        "_my_private_method",
    ),
    (
        "sld303_method_name",
        "class MyClass:\n    def my_public_method(self):\n        return self.value\n",
        "SLD303",
        "my_public_method",
    ),
    (
        "sld303_includes_singledispatch_hint",
        "class MyClass:\n    def my_public_method(self):\n        return self.value\n",
        "SLD303",
        "functools.singledispatch",
    ),
    (
        "sld401_class_name_child",
        "class Parent:\n    pass\n\nclass Child(Parent):\n    pass\n",
        "SLD401",
        "Child",
    ),
    (
        "sld401_class_name_parent",
        "class Parent:\n    pass\n\nclass Child(Parent):\n    pass\n",
        "SLD401",
        "Parent",
    ),
    (
        "sld501_class_name",
        "from dataclasses import dataclass\n\n@dataclass\n"
        "class MyDataClass:\n    x: int\n",
        "SLD501",
        "MyDataClass",
    ),
]


_SLD303_EXEMPT: list[tuple[str, str]] = [
    (
        "test_method_on_testcase",
        "import unittest\n\nclass MyTest(unittest.TestCase):\n"
        "    def test_something(self):\n        return 42\n",
    ),
    (
        "test_method_bare_testcase",
        "from unittest import TestCase\n\nclass MyTest(TestCase):\n"
        "    def test_something(self):\n        return 42\n",
    ),
    (
        "protocol_method_stub",
        "from typing import Protocol\n\n"
        "class HTTPClient(Protocol):\n    def get(self, url: str) -> str: ...\n",
    ),
    (
        "protocol_method_public_self",
        "from typing import Protocol\n\n"
        "class HTTPClient(Protocol):\n"
        "    def get(self, url: str) -> str:\n        return self.base + url\n",
    ),
    (
        "deleter_property",
        "class MyClass:\n    @name.deleter\n"
        "    def name(self):\n        del self.first_name\n",
    ),
]


_SLD303_NOT_EXEMPT: list[tuple[str, str]] = [
    (
        "non_test_method_on_testcase",
        "import unittest\n\nclass MyTest(unittest.TestCase):\n"
        "    def helper(self):\n        return 42\n",
    ),
    (
        "test_method_on_non_testcase",
        "class MyClass:\n    def test_something(self):\n        return 42\n",
    ),
]


class TestPresentByCode(unittest.TestCase):
    """Tests that specific code is present for nested/async scenarios."""

    def test_present(self) -> None:
        """Verify present."""
        for name, code, expected in _NESTED_AND_ASYNC_PRESENT:
            with self.subTest(name=name):
                assert_that(get_error_codes(code), has_item(expected))


class TestCleanCode(unittest.TestCase):
    """Tests that well-written code produces no errors."""

    def test_no_errors(self) -> None:
        """Verify no errors."""
        for name, code in _CLEAN_NO_ERRORS:
            with self.subTest(name=name):
                assert_that(get_error_codes(code), empty())


class TestErrorMessages(unittest.TestCase):
    """Tests for error message content."""

    def test_contains_expected(self) -> None:
        """Verify contains expected."""
        for name, code, sld, expected in _ERROR_MESSAGE_CASES:
            with self.subTest(name=name):
                errors = check_code(code)
                messages = [msg for _, _, msg in errors if sld in msg]
                assert_that(messages[0], contains_string(expected))


class TestCheckerMetadata(unittest.TestCase):
    """Tests for checker metadata."""

    def test_attributes(self) -> None:
        """Verify attributes."""
        for attr, expected in [("name", "stolid"), ("version", "0.1.0")]:
            with self.subTest(attr=attr):
                assert_that(getattr(Checker, attr), equal_to(expected))


class TestSLD303Exemptions(unittest.TestCase):
    """Tests for SLD303 exemptions (testcase, protocol, deleter)."""

    def test_exempt(self) -> None:
        """Verify exempt."""
        for name, code in _SLD303_EXEMPT:
            with self.subTest(name=name):
                assert_that("SLD303" in get_error_codes(code), equal_to(False))

    def test_not_exempt(self) -> None:
        """Verify not exempt."""
        for name, code in _SLD303_NOT_EXEMPT:
            with self.subTest(name=name):
                assert_that(get_error_codes(code), has_item("SLD303"))
