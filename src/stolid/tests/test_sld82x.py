"""Tests for SLD82x error codes (forbid docstrings on private things)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, has_item

from .code_parser import assert_absent, assert_present, check_code


def _module_codes(code: str, filename: str) -> list[str]:
    # Return the error codes produced by checking ``code`` under ``filename``.
    return [msg.split()[0] for _, _, msg in check_code(code, filename=filename)]


_SLD821_PRESENT: list[tuple[str, str]] = [
    ("private_module_with_docstring", '"""Internals."""\nx = 1\n'),
]


_SLD821_ABSENT: list[tuple[str, str]] = [
    ("private_module_no_docstring", "x = 1\n"),
]


_SLD822_PRESENT: list[tuple[str, str]] = [
    (
        "private_class_with_docstring",
        'class _Foo:\n    """A foo."""\n    x: int = 0\n',
    ),
]


_SLD822_ABSENT: list[tuple[str, str]] = [
    ("private_class_no_docstring", "class _Foo:\n    pass\n"),
    (
        "dunder_class_name_not_treated_as_private",
        'class Foo:\n    """A foo."""\n    pass\n',
    ),
    (
        "private_inner_class_in_function_skipped",
        'def outer():\n    class _Inner:\n        """Inner."""\n        pass\n',
    ),
]


_SLD823_PRESENT: list[tuple[str, str]] = [
    (
        "private_function_with_docstring",
        'def _foo() -> None:\n    """Do foo."""\n    pass\n',
    ),
    (
        "private_method_with_docstring",
        "class A:\n"
        '    """A."""\n'
        "    def _bar(self) -> None:\n"
        '        """Do bar."""\n'
        "        pass\n",
    ),
]


_SLD823_ABSENT: list[tuple[str, str]] = [
    ("private_function_no_docstring", "def _foo():\n    pass\n"),
    (
        "dunder_method_with_docstring",
        "class A:\n"
        '    """A."""\n'
        "    def __str__(self) -> str:\n"
        '        """Stringify."""\n'
        "        return 'a'\n",
    ),
    (
        "inner_private_function_with_docstring",
        'def outer() -> None:\n    """Outer."""\n'
        "    def _inner():\n"
        '        """Inner."""\n'
        "        return 1\n",
    ),
]


class TestSLD821PrivateModuleDocstring(unittest.TestCase):
    """Tests for SLD821: private modules with a docstring."""

    def test_present(self) -> None:
        """Verify SLD821 fires for a ``_foo.py`` module that has a docstring."""
        for name, code in _SLD821_PRESENT:
            with self.subTest(name=name):
                assert_that(_module_codes(code, "_foo.py"), has_item("SLD821"))

    def test_absent(self) -> None:
        """Verify SLD821 is silent when a private module has no docstring."""
        for name, source in _SLD821_ABSENT:
            with self.subTest(name=name):
                codes = _module_codes(source, "_foo.py")
                assert_that("SLD821" in codes, equal_to(False))

    def test_public_module_with_docstring_not_flagged(self) -> None:
        """Verify SLD821 does not fire for a public module with a docstring."""
        codes = _module_codes('"""Hello."""\nx = 1\n', "public.py")
        assert_that("SLD821" in codes, equal_to(False))


class TestSLD822PrivateClassDocstring(unittest.TestCase):
    """Tests for SLD822: private classes with a docstring."""

    def test_present(self) -> None:
        """Verify SLD822 fires when a private class carries a docstring."""
        assert_present(self, _SLD822_PRESENT, "SLD822")

    def test_absent(self) -> None:
        """Verify SLD822 stays silent in the negative cases."""
        assert_absent(self, _SLD822_ABSENT, "SLD822")


class TestSLD823PrivateFunctionDocstring(unittest.TestCase):
    """Tests for SLD823: private functions/methods with a docstring."""

    def test_present(self) -> None:
        """Verify SLD823 fires when a private function/method has a docstring."""
        assert_present(self, _SLD823_PRESENT, "SLD823")

    def test_absent(self) -> None:
        """Verify SLD823 is silent for dunders, inner privates, and undocumented."""
        assert_absent(self, _SLD823_ABSENT, "SLD823")
