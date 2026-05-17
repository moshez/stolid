"""Tests for SLD4xx error codes (inheritance related)."""

from __future__ import annotations

import unittest

from .code_parser import assert_absent, assert_present

_SLD401_PRESENT: list[tuple[str, str]] = [
    (
        "inherit_from_concrete_class",
        "class Parent:\n    pass\n\nclass Child(Parent):\n    pass\n",
    ),
    (
        "multiple_inheritance_mixed",
        "from typing import Protocol\n\n"
        "class Concrete:\n    pass\n\n"
        "class MyClass(Concrete, Protocol):\n    pass\n",
    ),
]


_SLD401_ABSENT: list[tuple[str, str]] = [
    (
        "protocol",
        "from typing import Protocol\n\n"
        "class MyProtocol(Protocol):\n    def method(self): ...\n",
    ),
    (
        "generic",
        "from typing import Generic, TypeVar\n\nT = TypeVar('T')\n\n"
        "class MyClass(Generic[T]):\n    pass\n",
    ),
    ("exception", "class MyError(Exception):\n    pass\n"),
    ("base_exception", "class MyError(BaseException):\n    pass\n"),
    (
        "testcase_attribute",
        "import unittest\n\nclass MyTest(unittest.TestCase):\n    pass\n",
    ),
    (
        "testcase_name",
        "from unittest import TestCase\n\nclass MyTest(TestCase):\n    pass\n",
    ),
    (
        "enum",
        "from enum import Enum\n\n" "class Color(Enum):\n    RED = 1\n    GREEN = 2\n",
    ),
    (
        "intenum",
        "from enum import IntEnum\n\n"
        "class Priority(IntEnum):\n    LOW = 1\n    HIGH = 2\n",
    ),
    (
        "typeddict",
        "from typing import TypedDict\n\n"
        "class Movie(TypedDict):\n    name: str\n    year: int\n",
    ),
    (
        "namedtuple",
        "from typing import NamedTuple\n\n"
        "class Point(NamedTuple):\n    x: int\n    y: int\n",
    ),
    ("no_base", "class MyClass:\n    pass\n"),
    (
        "subscripted_generic",
        "from typing import Generic, TypeVar\n\nT = TypeVar('T')\n\n"
        "class Container(Generic[T]):\n    pass\n",
    ),
    ("base_unknown_type", "class MyClass(get_base()):\n    pass\n"),
]


class TestSLD401InheritanceProhibited(unittest.TestCase):
    """Tests for SLD401: Inheritance from concrete classes is prohibited."""

    def test_present(self) -> None:
        assert_present(self, _SLD401_PRESENT, "SLD401")

    def test_absent(self) -> None:
        assert_absent(self, _SLD401_ABSENT, "SLD401")
