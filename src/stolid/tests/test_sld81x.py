"""Tests for SLD81x error codes (docstring enforcement)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, has_item

from .code_parser import assert_absent, assert_present, check_code, get_error_codes


def _module_codes(code: str, filename: str) -> list[str]:
    # Return the error codes produced by checking ``code`` under ``filename``.
    return [msg.split()[0] for _, _, msg in check_code(code, filename=filename)]


_SLD811_PRESENT: list[tuple[str, str]] = [
    ("public_module_no_docstring", "x = 1\n"),
    ("public_module_just_imports", "import os\n"),
]


_SLD811_ABSENT: list[tuple[str, str]] = [
    ("public_module_with_docstring", '"""Hello."""\nx = 1\n'),
]


_PRIVATE_MODULES = [
    ("_constants.py", "x = 1\n"),
    ("_private.py", "import os\n"),
]


_DUNDER_MODULE_NEEDS_DOC = [
    ("__init__.py", "x = 1\n"),
]


_SLD812_PRESENT: list[tuple[str, str]] = [
    ("public_class_no_docstring", "class Foo:\n    pass\n"),
    (
        "public_class_inside_private_module",
        "class Foo:\n    pass\n",
    ),
]


_SLD812_ABSENT: list[tuple[str, str]] = [
    ("private_class_no_docstring", "class _Foo:\n    pass\n"),
    (
        "public_class_with_docstring",
        'class Foo:\n    """A foo."""\n    pass\n',
    ),
    (
        "inner_class_inside_function_skipped",
        "def outer():\n    class Inner:\n        pass\n",
    ),
]


_SLD813_PRESENT: list[tuple[str, str]] = [
    ("public_function_no_docstring", "def foo():\n    pass\n"),
    (
        "public_method_in_private_class",
        "class _A:\n    def foo(self):\n        pass\n",
    ),
    (
        "public_method_in_public_class",
        'class A:\n    """A class."""\n' "    def foo(self):\n        pass\n",
    ),
    (
        "async_public_function_no_docstring",
        "async def foo():\n    pass\n",
    ),
]


_SLD813_ABSENT: list[tuple[str, str]] = [
    ("private_function_no_docstring", "def _foo():\n    pass\n"),
    (
        "private_method_no_docstring",
        "class _A:\n    def _bar(self):\n        pass\n",
    ),
    (
        "public_function_with_docstring",
        'def foo() -> None:\n    """Do foo."""\n    pass\n',
    ),
    (
        "inner_function_skipped",
        'def outer() -> None:\n    """Outer."""\n' "    def inner():\n        pass\n",
    ),
]


_SLD814_PRESENT: list[tuple[str, str]] = [
    (
        "missing_arg_x",
        'def f(x: int) -> None:\n    """Do something."""\n    pass\n',
    ),
    (
        "missing_one_of_two",
        'def f(a: int, b: int) -> None:\n    """Use a here."""\n    return None\n',
    ),
    (
        "missing_vararg",
        'def f(*args: int) -> None:\n    """Do nothing."""\n    pass\n',
    ),
    (
        "missing_kwarg",
        'def f(**opts: int) -> None:\n    """Do nothing."""\n    pass\n',
    ),
]


_SLD814_ABSENT: list[tuple[str, str]] = [
    (
        "all_args_named",
        "def f(a: int, b: int) -> None:\n"
        '    """Use ``a`` and ``b`` together."""\n'
        "    pass\n",
    ),
    (
        "self_arg_exempt",
        'class A:\n    """A."""\n'
        "    def m(self) -> None:\n"
        '        """Do nothing."""\n'
        "        pass\n",
    ),
    (
        "cls_arg_exempt",
        'class A:\n    """A."""\n'
        "    @classmethod\n"
        "    def m(cls) -> None:\n"
        '        """Do nothing."""\n'
        "        pass\n",
    ),
]


_SLD815_PRESENT: list[tuple[str, str]] = [
    (
        "no_return_mention",
        'def f() -> int:\n    """Compute."""\n    return 0\n',
    ),
    (
        "annotated_with_complex_type",
        'def f() -> list[int]:\n    """Build a list."""\n    return []\n',
    ),
]


_SLD815_ABSENT: list[tuple[str, str]] = [
    (
        "returns_mention",
        'def f() -> int:\n    """Return the answer."""\n    return 42\n',
    ),
    (
        "yields_mention",
        'def f() -> int:\n    """Yield the value."""\n    return 0\n',
    ),
    (
        "annotated_none_skips_return",
        'def f() -> None:\n    """Do something."""\n    pass\n',
    ),
    (
        "unannotated_skips_return",
        'def f():\n    """Do something."""\n    pass\n',
    ),
]


_SLD816_PRESENT: list[tuple[str, str]] = [
    (
        "field_missing",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        'class A:\n    """An A."""\n'
        "    x: int\n",
    ),
    (
        "one_missing_of_two",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        'class A:\n    """Mentions ``x`` only."""\n'
        "    x: int\n"
        "    y: int\n",
    ),
]


_SLD816_ABSENT: list[tuple[str, str]] = [
    (
        "all_fields_mentioned",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        'class A:\n    """Holds ``x`` and ``y``."""\n'
        "    x: int\n"
        "    y: int\n",
    ),
    (
        "private_field_skipped",
        "from dataclasses import dataclass, field\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        'class A:\n    """An A class."""\n'
        "    _hidden: int = 0\n",
    ),
    (
        "field_with_doc_skipped",
        "from dataclasses import dataclass, field\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        'class A:\n    """An A class."""\n'
        '    x: int = field(doc="the x")\n',
    ),
    (
        "non_dataclass_class_no_check",
        'class A:\n    """A normal class."""\n    x: int = 0\n',
    ),
    (
        "field_value_is_non_field_call",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        'class A:\n    """Holds ``x``."""\n'
        "    x: int = int(0)\n",
    ),
]


class TestSLD811PublicModuleDocstring(unittest.TestCase):
    """Tests for SLD811: public modules missing a module docstring."""

    def test_present(self) -> None:
        """Verify SLD811 fires for public modules without a module docstring."""
        for name, code in _SLD811_PRESENT:
            with self.subTest(name=name):
                assert_that(_module_codes(code, "public.py"), has_item("SLD811"))

    def test_absent_when_docstring_present(self) -> None:
        """Verify SLD811 stays silent when the module has a docstring."""
        for name, source in _SLD811_ABSENT:
            with self.subTest(name=name):
                codes = _module_codes(source, "public.py")
                assert_that("SLD811" in codes, equal_to(False))

    def test_private_modules_skipped(self) -> None:
        """Verify SLD811 is silent for filenames starting with a single underscore."""
        for filename, source in _PRIVATE_MODULES:
            with self.subTest(filename=filename):
                codes = _module_codes(source, filename)
                assert_that("SLD811" in codes, equal_to(False))

    def test_dunder_module_still_checked(self) -> None:
        """Verify SLD811 fires for ``__init__.py`` lacking a module docstring."""
        for filename, source in _DUNDER_MODULE_NEEDS_DOC:
            with self.subTest(filename=filename):
                codes = _module_codes(source, filename)
                assert_that(codes, has_item("SLD811"))

    def test_unknown_filename_skipped(self) -> None:
        """Verify SLD811 is silent when the filename is empty."""
        codes = _module_codes("x = 1\n", "")
        assert_that("SLD811" in codes, equal_to(False))


class TestSLD812PublicClassDocstring(unittest.TestCase):
    """Tests for SLD812: public classes missing a docstring."""

    def test_present(self) -> None:
        """Verify SLD812 fires for public classes without a docstring."""
        assert_present(self, _SLD812_PRESENT, "SLD812")

    def test_absent(self) -> None:
        """Verify SLD812 stays silent in the negative cases."""
        assert_absent(self, _SLD812_ABSENT, "SLD812")


class TestSLD813PublicFunctionDocstring(unittest.TestCase):
    """Tests for SLD813: public functions/methods missing a docstring."""

    def test_present(self) -> None:
        """Verify SLD813 fires for public functions/methods without a docstring."""
        assert_present(self, _SLD813_PRESENT, "SLD813")

    def test_absent(self) -> None:
        """Verify SLD813 stays silent in the negative cases."""
        assert_absent(self, _SLD813_ABSENT, "SLD813")


class TestSLD814FunctionArgDocumentation(unittest.TestCase):
    """Tests for SLD814: function docstrings must mention every argument."""

    def test_present(self) -> None:
        """Verify SLD814 fires when an argument name is missing from the docstring."""
        assert_present(self, _SLD814_PRESENT, "SLD814")

    def test_absent(self) -> None:
        """Verify SLD814 stays silent when all arguments are mentioned."""
        assert_absent(self, _SLD814_ABSENT, "SLD814")


class TestSLD815FunctionReturnDocumentation(unittest.TestCase):
    """Tests for SLD815: function docstrings must mention the return value."""

    def test_present(self) -> None:
        """Verify SLD815 fires when no return/yield word appears in the docstring."""
        assert_present(self, _SLD815_PRESENT, "SLD815")

    def test_absent(self) -> None:
        """Verify SLD815 is silent when return/yield is mentioned or return is None."""
        assert_absent(self, _SLD815_ABSENT, "SLD815")


class TestSLD816DataclassFieldDocumentation(unittest.TestCase):
    """Tests for SLD816: dataclass docstrings must mention each public field."""

    def test_present(self) -> None:
        """Verify SLD816 fires when a public dataclass field is unmentioned."""
        assert_present(self, _SLD816_PRESENT, "SLD816")

    def test_absent(self) -> None:
        """Verify SLD816 stays silent for documented, private, or field(doc=) fields."""
        assert_absent(self, _SLD816_ABSENT, "SLD816")


class TestSLD816EdgeCases(unittest.TestCase):
    """Edge cases for SLD816's class-body annotation walk."""

    def test_non_name_annassign_target_is_ignored(self) -> None:
        """Verify an ``obj.attr: int = 0`` form is not flagged as a missing field."""
        source = (
            "from dataclasses import dataclass\n\n"
            "@dataclass(frozen=True, slots=True, kw_only=True)\n"
            'class A:\n    """Holds ``obj`` only."""\n'
            "    obj: int = 0\n"
            "    obj.attr: int = 1\n"
        )
        codes = get_error_codes(source)
        assert_that("SLD816" in codes, equal_to(False))


class TestSLD813InnerFunctionExempt(unittest.TestCase):
    """Tests that inner functions never trigger SLD813."""

    def test_inner_def_in_def(self) -> None:
        """Verify an undocumented inner function does not raise SLD813."""
        source = (
            "def outer() -> None:\n"
            '    """Outer."""\n'
            "    def inner():\n"
            "        pass\n"
        )
        codes = get_error_codes(source)
        assert_that("SLD813" in codes, equal_to(False))

    def test_method_in_class_not_inner(self) -> None:
        """Verify methods of a class are not treated as inner functions."""
        source = "class A:\n" '    """A."""\n' "    def m(self):\n" "        pass\n"
        codes = get_error_codes(source)
        assert_that(codes, has_item("SLD813"))
