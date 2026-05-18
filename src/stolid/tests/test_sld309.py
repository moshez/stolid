"""Tests for SLD309 (Enum members with identifier-shaped string values)."""

from __future__ import annotations

import unittest

from .code_parser import assert_absent, assert_count, assert_present

_SLD309_PRESENT: list[tuple[str, str]] = [
    (
        "plain_enum_all_identifier_strings",
        "from enum import Enum\n"
        "class K(Enum):\n"
        "    READ = 'read'\n"
        "    WRITE = 'write'\n",
    ),
    (
        "str_enum_all_identifier_strings",
        "from enum import StrEnum\n"
        "class K(StrEnum):\n"
        "    OPEN = 'open'\n"
        "    CLOSED = 'closed'\n",
    ),
    (
        "enum_with_methods_still_fires_on_strings",
        "from enum import Enum\n"
        "class K(Enum):\n"
        "    A = 'one'\n"
        "    B = 'two'\n"
        "    def label(self):\n"
        "        return self.value\n",
    ),
    (
        "qualified_enum_base",
        "import enum\n"
        "class K(enum.Enum):\n"
        "    A = 'first'\n"
        "    B = 'second'\n",
    ),
    (
        "annotated_assignment_in_enum",
        "from enum import Enum\n"
        "class K(Enum):\n"
        "    A: str = 'a_value'\n"
        "    B: str = 'b_value'\n",
    ),
]


_SLD309_ABSENT: list[tuple[str, str]] = [
    (
        "enum_with_auto",
        "from enum import Enum, auto\n"
        "class K(Enum):\n"
        "    READ = auto()\n"
        "    WRITE = auto()\n",
    ),
    (
        "int_enum_with_int_values",
        "from enum import IntEnum\n" "class K(IntEnum):\n" "    A = 1\n" "    B = 2\n",
    ),
    (
        "non_identifier_string_values",
        "from enum import Enum\n"
        "class K(Enum):\n"
        "    RED = '#ff0000'\n"
        "    BLUE = '#0000ff'\n",
    ),
    (
        "mixed_identifier_and_non_identifier",
        "from enum import Enum\n"
        "class K(Enum):\n"
        "    A = 'open'\n"
        "    B = 'hello world'\n",
    ),
    (
        "not_an_enum_class",
        "class K:\n" "    A = 'one'\n" "    B = 'two'\n",
    ),
    (
        "empty_enum",
        "from enum import Enum\n" "class K(Enum):\n" "    pass\n",
    ),
    (
        "enum_with_only_methods",
        "from enum import Enum\n"
        "class K(Enum):\n"
        "    def label(self):\n"
        "        return 'x'\n",
    ),
    (
        "enum_with_tuple_value",
        "from enum import Enum\n" "class K(Enum):\n" "    A = ('one', 1)\n",
    ),
]


class TestSLD309EnumIdentifierValues(unittest.TestCase):
    """SLD309: Enum members whose string values are all valid identifiers."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD309_PRESENT, "SLD309")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD309_ABSENT, "SLD309")

    def test_one_report_per_member(self) -> None:
        """Verify one report per identifier-valued member."""
        cases = [
            (
                "three_members_three_reports",
                "from enum import Enum\n"
                "class K(Enum):\n"
                "    A = 'one'\n"
                "    B = 'two'\n"
                "    C = 'three'\n",
                3,
            ),
        ]
        assert_count(self, cases, "SLD309")
