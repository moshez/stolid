"""Tests for SLD702: Global names shadowing builtins/typing/stdlib."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string

from .code_parser import assert_absent, assert_present, check_code

_SLD702_PRESENT: list[tuple[str, str]] = [
    ("function_named_after_builtin", "def list():\n    pass\n"),
    ("class_named_after_builtin", "class list:\n    pass\n"),
    ("assign_to_builtin_name", "list = 5\n"),
    ("annotated_assign_to_builtin_name", "list: int = 0\n"),
    ("tuple_unpacking_with_builtin_name", "list, other = 1, 2\n"),
    ("function_named_after_typing", "def List():\n    pass\n"),
    ("function_named_after_stdlib_module", "def sys():\n    pass\n"),
    ("class_named_after_stdlib_module", "class json:\n    pass\n"),
]


_SLD702_ABSENT: list[tuple[str, str]] = [
    ("normal_function_name", "def my_function():\n    pass\n"),
    ("import_of_stdlib_not_flagged", "import sys\n"),
    ("from_import_not_flagged", "from typing import List\n"),
    (
        "nested_function_not_flagged",
        "def outer():\n    def list():\n        pass\n",
    ),
    (
        "method_not_flagged",
        "class MyClass:\n    def list(self):\n        return self._items\n",
    ),
    ("attribute_assign_not_flagged", "config.list = 5\n"),
]


_SLD702_MESSAGE: list[tuple[str, str, str]] = [
    ("builtin_name", "def list():\n    pass\n", "'list'"),
    ("builtin_marker", "def list():\n    pass\n", "builtin"),
    ("typing_name", "def Optional():\n    pass\n", "typing.Optional"),
    ("stdlib_name", "def os():\n    pass\n", "stdlib module 'os'"),
]


class TestSLD702(unittest.TestCase):
    """Tests for SLD702: shadowing reserved names."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD702_PRESENT, "SLD702")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD702_ABSENT, "SLD702")

    def test_message_content(self) -> None:
        """Verify message content."""
        for name, code, expected in _SLD702_MESSAGE:
            with self.subTest(name=name):
                errors = check_code(code)
                messages = [msg for _, _, msg in errors if "SLD702" in msg]
                assert_that(messages[0], contains_string(expected))
