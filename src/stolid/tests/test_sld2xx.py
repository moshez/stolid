"""Tests for SLD2xx error codes (ABC and abstractmethod related)."""

from __future__ import annotations

import unittest

from .code_parser import assert_absent, assert_count, assert_present

_ABC_IMPORT_PRESENT: list[tuple[str, str]] = [
    ("import_abc_from_abc", "from abc import ABC\n"),
    ("import_abc_with_alias", "from abc import ABC as AbstractBaseClass\n"),
]


_ABC_IMPORT_ABSENT: list[tuple[str, str]] = [
    ("import_abcmeta_allowed", "from abc import ABCMeta\n"),
]


_ABSTRACTMETHOD_USE_PRESENT: list[tuple[str, str]] = [
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


_ABSTRACTMETHOD_USE_COUNT: list[tuple[str, str, int]] = [
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


_TYPING_CAST_PRESENT: list[tuple[str, str]] = [
    ("cast_from_typing", "from typing import cast\nx = cast(int, value)\n"),
    (
        "cast_aliased",
        "from typing import cast as as_type\nx = as_type(int, value)\n",
    ),
    ("cast_via_typing_module", "import typing\nx = typing.cast(int, value)\n"),
]


_TYPING_CAST_ABSENT: list[tuple[str, str]] = [
    ("non_typing_cast_allowed", "from mylib import cast\nx = cast(value)\n"),
    (
        "other_module_cast_attribute_allowed",
        "import other\nx = other.cast(int, value)\n",
    ),
    ("no_cast_usage", "from typing import List\nx: List[int] = []\n"),
]


_BIG_FROM = "from somelib import (a1, a2, a3, a4, a5, a6, a7, a8)\n"

_BIG_FROM_SPLIT = (
    "from somelib import a1, a2, a3, a4\nfrom somelib import a5, a6, a7, a8\n"
)

_BIG_IMPORT = (
    "import somelib\n"
    "x = (somelib.a1, somelib.a2, somelib.a3, somelib.a4,\n"
    "     somelib.a5, somelib.a6, somelib.a7, somelib.a8)\n"
)

_BIG_IMPORT_ALIAS = (
    "import somelib as sl\n"
    "x = (sl.a1, sl.a2, sl.a3, sl.a4, sl.a5, sl.a6, sl.a7, sl.a8)\n"
)

_TYPE_CHECKING_GUARD = (
    "from typing import TYPE_CHECKING\n"
    "if TYPE_CHECKING:\n"
    "    from somelib import a1, a2, a3, a4, a5, a6, a7, a8\n"
)

_TYPE_CHECKING_USES = (
    "from typing import TYPE_CHECKING\n"
    "import somelib\n"
    "if TYPE_CHECKING:\n"
    "    x = (somelib.a1, somelib.a2, somelib.a3, somelib.a4,\n"
    "         somelib.a5, somelib.a6, somelib.a7, somelib.a8)\n"
)


_TYPE_CHECKING_ELSE = (
    "from typing import TYPE_CHECKING\n"
    "if TYPE_CHECKING:\n"
    "    pass\n"
    "else:\n"
    "    from somelib import a1, a2, a3, a4, a5, a6, a7, a8\n"
)


_OVER_IMPORTED_MODULE_PRESENT: list[tuple[str, str]] = [
    ("from_import_eight_names", _BIG_FROM),
    ("from_import_aggregated_across_statements", _BIG_FROM_SPLIT),
    ("type_checking_else_branch_runs_at_runtime", _TYPE_CHECKING_ELSE),
]


_OVER_IMPORTED_MODULE_ABSENT: list[tuple[str, str]] = [
    (
        "from_import_seven_names_under_limit",
        "from somelib import a1, a2, a3, a4, a5, a6, a7\n",
    ),
    (
        "typing_overuse_is_allowed",
        "from typing import (Any, Iterable, Iterator, List, Mapping, "
        "Optional, Protocol, Sequence)\n",
    ),
    ("import_plus_eight_attribute_accesses_is_not_sld205", _BIG_IMPORT),
    ("import_with_alias_plus_attribute_accesses_is_not_sld205", _BIG_IMPORT_ALIAS),
    ("from_import_inside_type_checking_block", _TYPE_CHECKING_GUARD),
    (
        "qualified_typing_module_test",
        "import typing\n"
        "if typing.TYPE_CHECKING:\n"
        "    from somelib import a1, a2, a3, a4, a5, a6, a7, a8\n",
    ),
    (
        "from_import_with_relative_module_skipped",
        "from . import a1, a2, a3, a4, a5, a6, a7, a8\n",
    ),
]


_OVER_IMPORTED_MODULE_COUNT: list[tuple[str, str, int]] = [
    ("from_import_eight_names_one_error", _BIG_FROM, 1),
    ("split_from_imports_one_error", _BIG_FROM_SPLIT, 1),
    (
        "two_modules_two_errors",
        "from libA import a1, a2, a3, a4, a5, a6, a7, a8\n"
        "from libB import b1, b2, b3, b4, b5, b6, b7, b8\n",
        2,
    ),
]


_OVERUSED_MODULE_ATTRIBUTES_PRESENT: list[tuple[str, str]] = [
    ("import_plus_eight_attribute_accesses", _BIG_IMPORT),
    ("import_with_alias_plus_attribute_accesses", _BIG_IMPORT_ALIAS),
]


_OVERUSED_MODULE_ATTRIBUTES_ABSENT: list[tuple[str, str]] = [
    (
        "import_plus_seven_attribute_accesses",
        "import somelib\n"
        "x = (somelib.a1, somelib.a2, somelib.a3, somelib.a4,\n"
        "     somelib.a5, somelib.a6, somelib.a7)\n",
    ),
    (
        "import_typing_attribute_uses_allowed",
        "import typing\n"
        "x = (typing.Any, typing.Iterable, typing.Iterator,\n"
        "     typing.List, typing.Mapping, typing.Optional,\n"
        "     typing.Protocol, typing.Sequence)\n",
    ),
    ("import_with_no_attribute_uses", "import somelib\n"),
    (
        "repeated_attribute_access_counts_once",
        "import somelib\n"
        "x = (somelib.a1, somelib.a1, somelib.a1, somelib.a1,\n"
        "     somelib.a1, somelib.a1, somelib.a1, somelib.a1)\n",
    ),
    ("attribute_uses_inside_type_checking_block", _TYPE_CHECKING_USES),
    (
        "attribute_on_non_imported_name_ignored",
        "obj.a1\nobj.a2\nobj.a3\nobj.a4\nobj.a5\nobj.a6\nobj.a7\nobj.a8\n",
    ),
    ("from_import_eight_names_is_not_sld207", _BIG_FROM),
    ("from_import_aggregated_is_not_sld207", _BIG_FROM_SPLIT),
]


_OVERUSED_MODULE_ATTRIBUTES_COUNT: list[tuple[str, str, int]] = [
    ("import_eight_attrs_one_error", _BIG_IMPORT, 1),
    (
        "two_modules_two_errors",
        "import libA\nimport libB\n"
        "x = (libA.a1, libA.a2, libA.a3, libA.a4,\n"
        "     libA.a5, libA.a6, libA.a7, libA.a8)\n"
        "y = (libB.b1, libB.b2, libB.b3, libB.b4,\n"
        "     libB.b5, libB.b6, libB.b7, libB.b8)\n",
        2,
    ),
]


class TestSLD201ABCProhibited(unittest.TestCase):
    """Tests for SLD201: ABC import is prohibited."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _ABC_IMPORT_PRESENT, "SLD201")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _ABC_IMPORT_ABSENT, "SLD201")


class TestSLD202AbstractMethodProhibited(unittest.TestCase):
    """Tests for SLD202: @abstractmethod is prohibited."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _ABSTRACTMETHOD_USE_PRESENT, "SLD202")

    def test_count(self) -> None:
        """Verify count."""
        assert_count(self, _ABSTRACTMETHOD_USE_COUNT, "SLD202")


class TestSLD203CastProhibited(unittest.TestCase):
    """Tests for SLD203: typing.cast is prohibited."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _TYPING_CAST_PRESENT, "SLD203")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _TYPING_CAST_ABSENT, "SLD203")


class TestSLD205ModuleOveruse(unittest.TestCase):
    """Tests for SLD205: too many ``from`` imports from a single module."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _OVER_IMPORTED_MODULE_PRESENT, "SLD205")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _OVER_IMPORTED_MODULE_ABSENT, "SLD205")

    def test_count(self) -> None:
        """Verify count."""
        assert_count(self, _OVER_IMPORTED_MODULE_COUNT, "SLD205")


class TestSLD207ModuleAttributeOveruse(unittest.TestCase):
    """Tests for SLD207: too many attribute accesses on a single module."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _OVERUSED_MODULE_ATTRIBUTES_PRESENT, "SLD207")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _OVERUSED_MODULE_ATTRIBUTES_ABSENT, "SLD207")

    def test_count(self) -> None:
        """Verify count."""
        assert_count(self, _OVERUSED_MODULE_ATTRIBUTES_COUNT, "SLD207")
