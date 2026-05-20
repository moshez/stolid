"""Tests for SLD7xx error codes (naming conventions)."""

from __future__ import annotations

import unittest

from .code_parser import (
    assert_absent,
    assert_message_contains_all,
    assert_present,
)

_CLASS_PRESENT: list[tuple[str, str]] = [
    ("helper_suffix", "class DiskHelper:\n    pass\n"),
    ("util_suffix", "class DiskUtil:\n    pass\n"),
    ("utils_suffix", "class StringUtils:\n    pass\n"),
    ("manager_suffix", "class ConnectionManager:\n    pass\n"),
    ("manage_suffix", "class DataManage:\n    pass\n"),
    ("help_prefix", "class HelpProvider:\n    pass\n"),
    ("standalone_helper", "class Helper:\n    pass\n"),
    ("helpers_suffix", "class TestHelpers:\n    pass\n"),
    ("managers_suffix", "class TaskManagers:\n    pass\n"),
    ("mixed_case_util", "class MyUTIL:\n    pass\n"),
]


_CLASS_ABSENT: list[tuple[str, str]] = [
    ("futile_no_error", "class Futile:\n    pass\n"),
    ("helpful_no_error", "class Helpful:\n    pass\n"),
    ("utility_no_error", "class Utility:\n    pass\n"),
    ("management_no_error", "class Management:\n    pass\n"),
    ("clean_name", "class DiskReader:\n    pass\n"),
]


_FUNCTION_PRESENT: list[tuple[str, str]] = [
    ("helper_suffix", "def get_helper():\n    pass\n"),
    ("util_suffix", "def string_util():\n    pass\n"),
    ("utils_suffix", "def get_utils():\n    pass\n"),
    ("manager_suffix", "def get_manager():\n    pass\n"),
    ("snake_case_helper_middle", "def create_helper_function():\n    pass\n"),
    ("camel_case_helper_middle", "def createHelperFunction():\n    pass\n"),
    ("async_helper", "async def async_helper():\n    pass\n"),
    ("method_helper", "class MyClass:\n    def my_helper(self):\n        pass\n"),
    ("all_caps_helper", "def ALL_HELPER():\n    pass\n"),
    ("standalone_help", "def help():\n    pass\n"),
]


_FUNCTION_ABSENT: list[tuple[str, str]] = [
    ("helpful_no_error", "def is_helpful():\n    pass\n"),
    ("futile_no_error", "def is_futile():\n    pass\n"),
    ("unhelpful_no_error", "def unhelpful():\n    pass\n"),
    ("utilize_no_error", "def utilize():\n    pass\n"),
    ("clean_function_name", "def read_file():\n    pass\n"),
]


_MODULE_NAME_PRESENT: list[tuple[str, str]] = [
    ("helper", "helper.py"),
    ("util", "string_util.py"),
    ("utils", "utils.py"),
    ("manager", "connection_manager.py"),
    ("helpers", "test_helpers.py"),
    ("managers", "task_managers.py"),
]


_MODULE_NAME_ABSENT: list[tuple[str, str]] = [
    ("futile", "futile.py"),
    ("clean", "reader.py"),
    ("init", "__init__.py"),
    ("no_filename", ""),
    ("non_py_filename", "helper.pyi"),
]


_TRIVIAL_SOURCE = "x = 1"


class TestSLD701ClassNames(unittest.TestCase):
    """Tests for SLD701: forbidden words in class names."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _CLASS_PRESENT, "SLD701")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _CLASS_ABSENT, "SLD701")


class TestSLD701FunctionNames(unittest.TestCase):
    """Tests for SLD701: forbidden words in function names."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _FUNCTION_PRESENT, "SLD701")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _FUNCTION_ABSENT, "SLD701")


class TestSLD701ModuleNames(unittest.TestCase):
    """Tests for SLD701: forbidden words in module names."""

    def test_present(self) -> None:
        """Verify present."""
        for name, filename in _MODULE_NAME_PRESENT:
            assert_present(self, [(name, _TRIVIAL_SOURCE)], "SLD701", filename=filename)

    def test_absent(self) -> None:
        """Verify absent."""
        for name, filename in _MODULE_NAME_ABSENT:
            assert_absent(self, [(name, _TRIVIAL_SOURCE)], "SLD701", filename=filename)


class TestSLD701ErrorMessage(unittest.TestCase):
    """Tests for SLD701 error message content."""

    def test_message_includes_name_and_word(self) -> None:
        """Verify message includes name and word."""
        assert_message_contains_all(
            self,
            "class ConnectionManager:\n    pass\n",
            "SLD701",
            ("ConnectionManager", "manager"),
        )
