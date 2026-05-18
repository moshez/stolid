"""Tests for SLD2xx error codes (ABC and abstractmethod related)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, empty

from .code_parser import assert_absent, assert_count, assert_present, get_error_codes

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


_SLD204_PRESENT: list[tuple[str, str]] = [
    ("import_after_assignment", "x = 1\nimport os\n"),
    ("from_import_after_assignment", "x = 1\nfrom os import path\n"),
    (
        "import_after_function_def",
        "def f():\n    pass\nimport os\n",
    ),
    ("import_inside_function", "def f():\n    import os\n"),
    (
        "from_import_inside_function",
        "def f():\n    from os import path\n",
    ),
    ("import_inside_class", "class C:\n    import os\n"),
    (
        "import_inside_method",
        "class C:\n    def m(self):\n        import os\n",
    ),
    ("import_inside_if_block", "if True:\n    import os\n"),
    (
        "import_inside_try",
        "try:\n    import os\nexcept ImportError:\n    pass\n",
    ),
    (
        "import_after_docstring_and_code",
        '"""Docstring."""\nx = 1\nimport os\n',
    ),
    (
        "import_after_non_docstring_expr",
        "1 + 1\nimport os\n",
    ),
    (
        "import_after_non_string_constant",
        "42\nimport os\n",
    ),
]


_SLD204_ABSENT: list[tuple[str, str]] = [
    ("single_import", "import os\n"),
    ("single_from_import", "from os import path\n"),
    (
        "multiple_imports_then_code",
        "import os\nimport sys\nfrom typing import Any\nx = 1\n",
    ),
    (
        "docstring_then_imports",
        '"""Module docstring."""\nimport os\nfrom sys import argv\n',
    ),
    (
        "future_then_imports",
        "from __future__ import annotations\nimport os\n",
    ),
    ("imports_then_code", "import os\nx = os.getcwd()\n"),
    ("empty_module", ""),
    ("only_docstring", '"""Module docstring."""\n'),
    (
        "string_expression_after_imports",
        'import os\n"not a docstring"\n',
    ),
]


_SLD204_COUNT: list[tuple[str, str, int]] = [
    (
        "multiple_imports_after_code",
        "x = 1\nimport os\nimport sys\n",
        2,
    ),
    (
        "import_in_function_and_after_code",
        "x = 1\ndef f():\n    import os\nimport sys\n",
        2,
    ),
    (
        "nested_import_in_method_in_class",
        "class C:\n    def m(self):\n        from os import path\n",
        1,
    ),
]


class TestSLD201ABCProhibited(unittest.TestCase):
    """Tests for SLD201: ABC import is prohibited."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD201_PRESENT, "SLD201")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD201_ABSENT, "SLD201")


class TestSLD202AbstractMethodProhibited(unittest.TestCase):
    """Tests for SLD202: @abstractmethod is prohibited."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD202_PRESENT, "SLD202")

    def test_count(self) -> None:
        """Verify count."""
        assert_count(self, _SLD202_COUNT, "SLD202")


class TestSLD203CastProhibited(unittest.TestCase):
    """Tests for SLD203: typing.cast is prohibited."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD203_PRESENT, "SLD203")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD203_ABSENT, "SLD203")


class TestSLD204ImportPlacement(unittest.TestCase):
    """Tests for SLD204: imports must be at the top of the module."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD204_PRESENT, "SLD204")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD204_ABSENT, "SLD204")

    def test_count(self) -> None:
        """Verify count."""
        assert_count(self, _SLD204_COUNT, "SLD204")

    def test_no_errors_on_well_formed_module(self) -> None:
        """Verify no errors on well formed module."""
        code = (
            '"""Module docstring."""\n'
            "from __future__ import annotations\n"
            "import os\n"
            "import sys\n"
            "from typing import Any\n"
            "\n"
            "x: Any = os.getcwd()\n"
            "y = sys.path\n"
        )
        codes = [c for c in get_error_codes(code) if c == "SLD204"]
        assert_that(codes, empty())
