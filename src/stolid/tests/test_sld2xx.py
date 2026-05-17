"""Tests for SLD2xx error codes (ABC and abstractmethod related)."""

from __future__ import annotations

import unittest

from .code_parser import assert_absent, assert_count, assert_present

_SLD201_PRESENT: list[tuple[str, str]] = [
    ("import_abc_from_abc", "from abc import ABC\n"),
    ("import_abc_with_alias", "from abc import ABC as AbstractBaseClass\n"),
]


_SLD201_ABSENT: list[tuple[str, str]] = [
    ("import_abcmeta_allowed", "from abc import ABCMeta\n"),
]


_SLD202_PRESENT: list[tuple[str, str]] = [
    ("import_abstractmethod", "from abc import abstractmethod\n"),
    (
        "abstractmethod_via_abc_module",
        "import abc\n\nclass MyClass:\n"
        "    @abc.abstractmethod\n"
        "    def my_method(self):\n        pass\n",
    ),
    (
        "abstractmethod_aliased",
        "from abc import abstractmethod as am\n\n"
        "class MyClass:\n    @am\n    def method(self):\n        pass\n",
    ),
    (
        "abstractmethod_decorator_with_import_abc",
        "import abc\n\nclass MyInterface:\n"
        "    @abc.abstractmethod\n    def method(self):\n        pass\n",
    ),
]


_SLD202_COUNT: list[tuple[str, str, int]] = [
    (
        "abstractmethod_decorator_direct",
        "from abc import abstractmethod\n\n"
        "class MyClass:\n    @abstractmethod\n"
        "    def my_method(self):\n        pass\n",
        2,
    ),
    (
        "abstractmethod_on_class_decorator",
        "from abc import abstractmethod\n\n"
        "@abstractmethod\nclass MyClass:\n    pass\n",
        2,
    ),
]


_SLD203_PRESENT: list[tuple[str, str]] = [
    ("cast_from_typing", "from typing import cast\nx = cast(int, value)\n"),
    (
        "cast_aliased",
        "from typing import cast as as_type\nx = as_type(int, value)\n",
    ),
    ("cast_via_typing_module", "import typing\nx = typing.cast(int, value)\n"),
]


_SLD203_ABSENT: list[tuple[str, str]] = [
    ("non_typing_cast_allowed", "from mylib import cast\nx = cast(value)\n"),
    (
        "other_module_cast_attribute_allowed",
        "import other\nx = other.cast(int, value)\n",
    ),
    ("no_cast_usage", "from typing import List\nx: List[int] = []\n"),
]


class TestSLD201ABCProhibited(unittest.TestCase):
    """Tests for SLD201: ABC import is prohibited."""

    def test_present(self) -> None:
        assert_present(self, _SLD201_PRESENT, "SLD201")

    def test_absent(self) -> None:
        assert_absent(self, _SLD201_ABSENT, "SLD201")


class TestSLD202AbstractMethodProhibited(unittest.TestCase):
    """Tests for SLD202: @abstractmethod is prohibited."""

    def test_present(self) -> None:
        assert_present(self, _SLD202_PRESENT, "SLD202")

    def test_count(self) -> None:
        assert_count(self, _SLD202_COUNT, "SLD202")


class TestSLD203CastProhibited(unittest.TestCase):
    """Tests for SLD203: typing.cast is prohibited."""

    def test_present(self) -> None:
        assert_present(self, _SLD203_PRESENT, "SLD203")

    def test_absent(self) -> None:
        assert_absent(self, _SLD203_ABSENT, "SLD203")
