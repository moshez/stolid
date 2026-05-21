"""Tests for SLD704: 'is_'-prefixed functions/methods must return bool."""

from __future__ import annotations

import unittest

from .code_parser import (
    assert_absent,
    assert_message_contains_all,
    assert_present,
)

_PRESENT: list[tuple[str, str]] = [
    (
        "function_returns_str",
        "def is_ready() -> str:\n    return 'yes'\n",
    ),
    (
        "function_returns_int",
        "def is_count() -> int:\n    return 1\n",
    ),
    (
        "function_returns_none",
        "def is_ready() -> None:\n    return\n",
    ),
    (
        "async_function_returns_str",
        "async def is_ready() -> str:\n    return 'yes'\n",
    ),
    (
        "method_returns_str",
        ("class Job:\n" "    def is_ready(self) -> str:\n" "        return 'yes'\n"),
    ),
    (
        "private_function_returns_str",
        "def _is_ready() -> str:\n    return 'yes'\n",
    ),
    (
        "double_underscore_function_returns_str",
        "def __is_ready() -> str:\n    return 'yes'\n",
    ),
    (
        "optional_bool_return",
        (
            "from typing import Optional\n"
            "def is_ready() -> Optional[bool]:\n"
            "    return None\n"
        ),
    ),
    (
        "union_bool_return",
        "def is_ready() -> bool | None:\n    return None\n",
    ),
    (
        "literal_int_return",
        (
            "from typing import Literal\n"
            "def is_ready() -> Literal[0, 1]:\n"
            "    return 1\n"
        ),
    ),
    (
        "classmethod_returns_str",
        (
            "class Job:\n"
            "    @classmethod\n"
            "    def is_open(cls) -> str:\n"
            "        return 'yes'\n"
        ),
    ),
    (
        "staticmethod_returns_str",
        (
            "class Job:\n"
            "    @staticmethod\n"
            "    def is_open() -> str:\n"
            "        return 'yes'\n"
        ),
    ),
    (
        "property_returns_str",
        (
            "class Job:\n"
            "    @property\n"
            "    def is_open(self) -> str:\n"
            "        return 'yes'\n"
        ),
    ),
]


_ABSENT: list[tuple[str, str]] = [
    (
        "function_returns_bool",
        "def is_ready() -> bool:\n    return True\n",
    ),
    (
        "function_returns_typeguard",
        (
            "from typing import TypeGuard\n"
            "def is_str(x: object) -> TypeGuard[str]:\n"
            "    return isinstance(x, str)\n"
        ),
    ),
    (
        "function_returns_typing_typeguard",
        (
            "import typing\n"
            "def is_str(x: object) -> typing.TypeGuard[str]:\n"
            "    return isinstance(x, str)\n"
        ),
    ),
    (
        "function_returns_typeis",
        (
            "from typing import TypeIs\n"
            "def is_str(x: object) -> TypeIs[str]:\n"
            "    return isinstance(x, str)\n"
        ),
    ),
    (
        "function_returns_builtins_bool",
        "def is_ready() -> builtins.bool:\n    return True\n",
    ),
    (
        "function_no_annotation",
        "def is_ready():\n    return True\n",
    ),
    (
        "non_predicate_name",
        "def fetch() -> str:\n    return 'x'\n",
    ),
    (
        "isolate_not_predicate",
        "def isolate() -> str:\n    return 'x'\n",
    ),
    (
        "island_not_predicate",
        "def island() -> str:\n    return 'x'\n",
    ),
    (
        "no_content_after_is_prefix",
        "def is_() -> str:\n    return 'x'\n",
    ),
    (
        "method_returns_bool",
        ("class Job:\n" "    def is_ready(self) -> bool:\n" "        return True\n"),
    ),
    (
        "private_method_returns_bool",
        ("class Job:\n" "    def _is_ready(self) -> bool:\n" "        return True\n"),
    ),
    (
        "dunder_init_no_predicate",
        (
            "class Job:\n"
            "    def __init__(self) -> None:\n"
            "        self.ready = True\n"
        ),
    ),
]


class TestSLD704(unittest.TestCase):
    """Tests for SLD704: 'is_'-prefixed names must return bool."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _PRESENT, "SLD704")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _ABSENT, "SLD704")

    def test_message_includes_name(self) -> None:
        """Verify the message includes the offending function name."""
        assert_message_contains_all(
            self,
            "def is_ready() -> str:\n    return 'yes'\n",
            "SLD704",
            ("is_ready",),
        )
