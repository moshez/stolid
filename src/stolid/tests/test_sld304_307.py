"""Tests for SLD304-SLD307 (stringly-typed code that should use an enum)."""

from __future__ import annotations

import unittest

from .code_parser import assert_absent, assert_count, assert_present

_SLD304_PRESENT: list[tuple[str, str]] = [
    (
        "two_equality_comparisons",
        "def f(x):\n"
        "    if x == 'open':\n"
        "        return 1\n"
        "    if x == 'closed':\n"
        "        return 2\n",
    ),
    (
        "or_chain",
        "def f(x):\n" "    if x == 'open' or x == 'closed':\n" "        return 1\n",
    ),
    (
        "in_tuple_of_strings",
        "def f(x):\n"
        "    if x in ('open', 'closed', 'pending'):\n"
        "        return 1\n",
    ),
    (
        "in_set_of_strings",
        "def f(x):\n" "    if x in {'open', 'closed'}:\n" "        return 1\n",
    ),
    (
        "ne_and_eq",
        "def f(x):\n" "    if x != 'open' and x == 'closed':\n" "        return 1\n",
    ),
    (
        "attribute_expression",
        "def f(obj):\n"
        "    if obj.status == 'open':\n"
        "        return 1\n"
        "    if obj.status == 'closed':\n"
        "        return 2\n",
    ),
    (
        "module_scope",
        "import sys\nif sys.platform == 'linux' or sys.platform == 'darwin':\n"
        "    pass\n",
    ),
    (
        "string_on_left",
        "def f(x):\n"
        "    if 'open' == x:\n"
        "        return 1\n"
        "    if 'closed' == x:\n"
        "        return 2\n",
    ),
]


_SLD304_ABSENT: list[tuple[str, str]] = [
    (
        "single_equality",
        "def f(x):\n" "    if x == 'open':\n" "        return 1\n",
    ),
    (
        "different_names",
        "def f(x, y):\n"
        "    if x == 'open':\n"
        "        return 1\n"
        "    if y == 'closed':\n"
        "        return 2\n",
    ),
    (
        "across_functions",
        "def f(x):\n"
        "    return x == 'open'\n"
        "def g(x):\n"
        "    return x == 'closed'\n",
    ),
    (
        "in_mixed_collection",
        "def f(x):\n" "    if x in ('open', 1):\n" "        return 1\n",
    ),
    (
        "same_string_twice",
        "def f(x):\n"
        "    if x == 'open':\n"
        "        return 1\n"
        "    if x == 'open':\n"
        "        return 2\n",
    ),
    (
        "non_string_equality",
        "def f(x, y):\n" "    if x == y:\n" "        return 1\n",
    ),
    (
        "non_eq_operator",
        "def f(x):\n" "    if x < 'open' and x > 'closed':\n" "        return 1\n",
    ),
    (
        "call_in_membership",
        "def f():\n" "    if get_x() in ('open', 'closed'):\n" "        return 1\n",
    ),
    (
        "membership_against_variable",
        "def f(x, choices):\n" "    if x in choices:\n" "        return 1\n",
    ),
    (
        "non_literal_subscript",
        "def f(d):\n" "    return d['a'] + d['b']\n",
    ),
    (
        "called_subscript_value",
        "from typing import Literal\n" "def f():\n" "    return get_type()[0]\n",
    ),
]


_SLD305_PRESENT: list[tuple[str, str]] = [
    (
        "match_two_string_cases",
        "def f(x):\n"
        "    match x:\n"
        "        case 'open':\n"
        "            return 1\n"
        "        case 'closed':\n"
        "            return 2\n",
    ),
    (
        "match_or_pattern",
        "def f(x):\n"
        "    match x:\n"
        "        case 'open' | 'closed':\n"
        "            return 1\n",
    ),
    (
        "match_with_wildcard",
        "def f(x):\n"
        "    match x:\n"
        "        case 'open':\n"
        "            return 1\n"
        "        case 'closed':\n"
        "            return 2\n"
        "        case _:\n"
        "            return 0\n",
    ),
]


_SLD305_ABSENT: list[tuple[str, str]] = [
    (
        "single_string_case",
        "def f(x):\n"
        "    match x:\n"
        "        case 'open':\n"
        "            return 1\n"
        "        case _:\n"
        "            return 0\n",
    ),
    (
        "non_string_cases",
        "def f(x):\n"
        "    match x:\n"
        "        case 1:\n"
        "            return 1\n"
        "        case 2:\n"
        "            return 2\n",
    ),
]


_SLD306_PRESENT: list[tuple[str, str]] = [
    (
        "string_three_times_across_module",
        "def f(x):\n"
        "    return x == 'pending'\n"
        "def g(x):\n"
        "    return x != 'pending'\n"
        "def h(x):\n"
        "    return x == 'pending'\n",
    ),
    (
        "string_three_times_via_in",
        "def f(a):\n"
        "    return a in ('pending', 'done')\n"
        "def g(a):\n"
        "    return a in ('pending', 'open')\n"
        "def h(a):\n"
        "    return a == 'pending'\n",
    ),
    (
        "string_via_match_and_equality",
        "def f(x):\n"
        "    if x == 'open':\n"
        "        return 1\n"
        "def g(y):\n"
        "    match y:\n"
        "        case 'open':\n"
        "            return 1\n"
        "        case 'closed':\n"
        "            return 2\n"
        "def h(z):\n"
        "    return z != 'open'\n",
    ),
]


_SLD306_ABSENT: list[tuple[str, str]] = [
    (
        "string_twice_only",
        "def f(x):\n"
        "    return x == 'open'\n"
        "def g(x):\n"
        "    return x == 'open'\n",
    ),
    (
        "string_in_assignment_only",
        "x = 'open'\ny = 'open'\nz = 'open'\n",
    ),
    (
        "string_in_subscript_only",
        "d = {}\nd['open'] = 1\nd['open'] = 2\nd['open'] = 3\n",
    ),
]


_SLD307_PRESENT: list[tuple[str, str]] = [
    (
        "literal_two_strings",
        "from typing import Literal\n"
        "def f(x: Literal['open', 'closed']) -> int:\n"
        "    return 1\n",
    ),
    (
        "literal_single_string",
        "from typing import Literal\n" "x: Literal['open'] = 'open'\n",
    ),
    (
        "literal_qualified",
        "import typing\n"
        "def f(x: typing.Literal['open', 'closed']) -> int:\n"
        "    return 1\n",
    ),
    (
        "literal_in_optional",
        "from typing import Literal, Optional\n"
        "x: Optional[Literal['open', 'closed']] = None\n",
    ),
]


_SLD307_ABSENT: list[tuple[str, str]] = [
    (
        "literal_with_ints",
        "from typing import Literal\n"
        "def f(x: Literal[1, 2]) -> int:\n"
        "    return 1\n",
    ),
    (
        "literal_with_none",
        "from typing import Literal\n"
        "def f(x: Literal[None]) -> int:\n"
        "    return 1\n",
    ),
    (
        "string_typed_argument",
        "def f(x: str) -> int:\n" "    return 1\n",
    ),
]


class TestSLD304MultiCompare(unittest.TestCase):
    """SLD304: Same expression compared against multiple string literals."""

    def test_present(self) -> None:
        assert_present(self, _SLD304_PRESENT, "SLD304")

    def test_absent(self) -> None:
        assert_absent(self, _SLD304_ABSENT, "SLD304")

    def test_one_per_literal(self) -> None:
        cases = [
            (
                "or_chain_two_reports",
                "def f(x):\n"
                "    if x == 'open' or x == 'closed':\n"
                "        return 1\n",
                2,
            ),
            (
                "in_tuple_three_reports",
                "def f(x):\n" "    if x in ('a', 'b', 'c'):\n" "        return 1\n",
                3,
            ),
        ]
        assert_count(self, cases, "SLD304")


class TestSLD305MatchStringCases(unittest.TestCase):
    """SLD305: match statement with string-literal case patterns."""

    def test_present(self) -> None:
        assert_present(self, _SLD305_PRESENT, "SLD305")

    def test_absent(self) -> None:
        assert_absent(self, _SLD305_ABSENT, "SLD305")


class TestSLD306ModuleStringCount(unittest.TestCase):
    """SLD306: String literal appears in 3+ equality contexts in the module."""

    def test_present(self) -> None:
        assert_present(self, _SLD306_PRESENT, "SLD306")

    def test_absent(self) -> None:
        assert_absent(self, _SLD306_ABSENT, "SLD306")


class TestSLD307LiteralAnnotation(unittest.TestCase):
    """SLD307: Literal[...] annotation contains a string literal."""

    def test_present(self) -> None:
        assert_present(self, _SLD307_PRESENT, "SLD307")

    def test_absent(self) -> None:
        assert_absent(self, _SLD307_ABSENT, "SLD307")
