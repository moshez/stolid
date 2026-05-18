"""Tests for SLD9xx error codes (private-access checker)."""

from __future__ import annotations

import ast
import unittest

from hamcrest import assert_that, contains_string, equal_to, has_item

from .._private_access_check import PrivacyKind, check_private_access
from .code_parser import assert_absent, assert_present, check_code

_SLD901_PRESENT: list[tuple[str, str]] = [
    ("external_read_top_level_function", "def f(x):\n    return x._private\n"),
    (
        "external_read_local_var_in_method",
        "class A:\n"
        "    def m(self):\n"
        "        other = self.get()\n"
        "        return other._value\n",
    ),
    (
        "aliased_self_not_privileged",
        "class A:\n"
        "    def m(self):\n"
        "        me = self\n"
        "        return me._cache\n",
    ),
    ("read_in_lambda", "result = (lambda x: x._private)(thing)\n"),
    (
        "staticmethod_self_arg_not_privileged",
        "class A:\n"
        "    @staticmethod\n"
        "    def m(self):\n"
        "        return self._private\n",
    ),
    (
        "staticmethod_via_attribute_decorator_not_privileged",
        "class A:\n"
        "    @builtins.staticmethod\n"
        "    def m(self):\n"
        "        return self._private\n",
    ),
    (
        "single_underscore_name",
        "def f(x):\n    return x._\n",
    ),
    (
        "module_level_access_no_import",
        "obj = make()\nobj._field\n",
    ),
    (
        "private_attr_on_non_name_expression",
        "config.section._password\n",
    ),
    (
        "private_attr_on_call_result",
        "make()._cache\n",
    ),
]


_SLD901_ABSENT: list[tuple[str, str]] = [
    (
        "self_access_in_method",
        "class A:\n    def m(self):\n        return self._cache\n",
    ),
    (
        "cls_access_in_classmethod",
        "class A:\n"
        "    @classmethod\n"
        "    def m(cls):\n"
        "        return cls._registry\n",
    ),
    (
        "custom_self_name_supported",
        "class A:\n    def m(this):\n        return this._cache\n",
    ),
    ("dunder_not_flagged", "def f(x):\n    return x.__class__\n"),
    ("trailing_underscore_not_flagged", "def f(x):\n    return x.class_\n"),
    ("public_attr_not_flagged", "def f(x):\n    return x.value\n"),
    (
        "method_with_no_args_not_treated_as_having_self",
        "class A:\n    def m():\n        return 1\n",
    ),
    (
        "non_staticmethod_attribute_decorator",
        "class A:\n"
        "    @builtins.something_else\n"
        "    def m(self):\n"
        "        return self._cache\n",
    ),
    (
        "from_dunder_future_import",
        "from __future__ import annotations\n",
    ),
]


_SLD902_PRESENT: list[tuple[str, str]] = [
    ("external_assignment", "obj._token = 'x'\n"),
    ("external_augmented_assignment", "obj._retries += 1\n"),
    ("external_del", "del obj._cache\n"),
    ("multiple_assignment_targets", "obj1._a = obj2._b = 1\n"),
    ("tuple_unpacking_assignment", "(obj._x, obj._y) = (1, 2)\n"),
]


_SLD902_ABSENT: list[tuple[str, str]] = [
    (
        "self_assignment_in_method",
        "class A:\n    def m(self):\n        self._cache = {}\n",
    ),
    (
        "self_aug_assignment",
        "class A:\n    def m(self):\n        self._count += 1\n",
    ),
    (
        "self_del",
        "class A:\n    def m(self):\n        del self._cache\n",
    ),
    ("read_not_flagged_as_write", "x = obj._y\n"),
]


_SLD903_PRESENT: list[tuple[str, str]] = [
    ("from_package_private_name", "from pkg import _helper\n"),
    ("mixed_public_and_private", "from pkg import alpha, _beta, gamma\n"),
    ("aliased_private_still_flagged", "from pkg import _x as y\n"),
]


_SLD903_ABSENT: list[tuple[str, str]] = [
    ("relative_import_private_permitted", "from . import _helper\n"),
    (
        "relative_with_module_and_private_permitted",
        "from .sub import _helper\n",
    ),
    ("relative_private_module_permitted", "from ._sub import public\n"),
    ("public_absolute_import", "from pkg import helper\n"),
    ("dunder_import_not_private", "from pkg import __version__\n"),
    ("star_import_not_flagged", "from pkg import *\n"),
]


_SLD904_PRESENT: list[tuple[str, str]] = [
    ("import_private_submodule", "import numpy._core\n"),
    ("from_import_private_module", "from numpy._core import multiarray\n"),
    ("top_level_private_package", "import _internal\n"),
    ("aliased_private_submodule", "import numpy._core as nc\n"),
    (
        "deeply_nested_private_one_violation",
        "from pkg._a._b import x\n",
    ),
]


_SLD904_ABSENT: list[tuple[str, str]] = [
    ("relative_private_submodule_permitted", "from ._core import x\n"),
    ("relative_dot_dot_private_permitted", "from .._utils import h\n"),
    ("public_module_import", "import numpy\n"),
    ("public_from_import", "from os.path import join\n"),
]


_SLD905_PRESENT: list[tuple[str, str]] = [
    (
        "import_as_then_private_attr",
        "import numpy as np\nnp._core\n",
    ),
    (
        "plain_import_then_private_attr",
        "import os\nos._exit\n",
    ),
    (
        "from_import_bound_name_then_private_attr",
        "from pkg import helper\nhelper._internal\n",
    ),
    (
        "relative_import_bound_name_then_private_attr",
        "from . import sub\nsub._helper\n",
    ),
    (
        "chained_private_via_imported_module",
        "import numpy as np\nx = np._core.something\n",
    ),
]


_SLD905_ABSENT: list[tuple[str, str]] = [
    (
        "public_attr_on_imported_module",
        "import numpy as np\nnp.array\n",
    ),
    (
        "dunder_attr_on_imported_module",
        "import os\nos.__name__\n",
    ),
    (
        "non_imported_name_falls_through_to_read",
        "obj._field\n",
    ),
]


class TestSLD901ExternalRead(unittest.TestCase):
    """Tests for SLD901: external read of a private attribute."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD901_PRESENT, "SLD901")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD901_ABSENT, "SLD901")


class TestSLD902ExternalWrite(unittest.TestCase):
    """Tests for SLD902: external write of a private attribute."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD902_PRESENT, "SLD902")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD902_ABSENT, "SLD902")


class TestSLD903AbsolutePrivateImport(unittest.TestCase):
    """Tests for SLD903: absolute import of a private name."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD903_PRESENT, "SLD903")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD903_ABSENT, "SLD903")


class TestSLD904PrivateSubmoduleImport(unittest.TestCase):
    """Tests for SLD904: import touching a private submodule."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD904_PRESENT, "SLD904")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD904_ABSENT, "SLD904")

    def test_deep_path_one_violation(self) -> None:
        """Verify deep path one violation."""
        codes = [
            msg.split()[0] for _, _, msg in check_code("from pkg._a._b import x\n")
        ]
        assert_that(codes.count("SLD904"), equal_to(1))


class TestSLD905ModulePrivateAttr(unittest.TestCase):
    """Tests for SLD905: private access on an imported name."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD905_PRESENT, "SLD905")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD905_ABSENT, "SLD905")


class TestErrorMessages(unittest.TestCase):
    """Tests that emitted messages mention the offending name."""

    def test_message_includes_attribute(self) -> None:
        """Verify message includes attribute."""
        cases = [
            ("SLD901", "obj._secret\n", "_secret"),
            ("SLD902", "obj._token = 'x'\n", "_token"),
            ("SLD903", "from pkg import _internal\n", "_internal"),
            ("SLD904", "import pkg._sub\n", "pkg._sub"),
            ("SLD905", "import os\nos._exit\n", "_exit"),
        ]
        for code, source, expected in cases:
            with self.subTest(code=code):
                errors = check_code(source)
                messages = [msg for _, _, msg in errors if code in msg]
                assert_that(messages[0], contains_string(expected))


def kinds_for(source: str) -> set[PrivacyKind]:
    """Return the set of violation kinds emitted by the visitor for ``source``."""
    return {err.kind for err in check_private_access(ast.parse(source))}


class TestKindAndAttrEmission(unittest.TestCase):
    """Tests against the visitor's semantic surface (kind, attr)."""

    def test_emits_expected_kinds(self) -> None:
        """Verify emits expected kinds."""
        cases = [
            ("def f(x): return x._private\n", PrivacyKind.EXTERNAL_PRIVATE_READ),
            ("obj._token = 'x'\n", PrivacyKind.EXTERNAL_PRIVATE_WRITE),
            ("del obj._cache\n", PrivacyKind.EXTERNAL_PRIVATE_WRITE),
            ("from pkg import _helper\n", PrivacyKind.ABSOLUTE_PRIVATE_IMPORT),
            ("from numpy._core import x\n", PrivacyKind.PRIVATE_SUBMODULE_IMPORT),
            ("import numpy as np\nnp._core\n", PrivacyKind.MODULE_PRIVATE_ATTR),
        ]
        for source, expected in cases:
            with self.subTest(kind=expected):
                assert_that(kinds_for(source), has_item(expected))

    def test_relative_import_emits_nothing(self) -> None:
        """Verify relative import emits nothing."""
        assert_that(kinds_for("from . import _helper\n"), equal_to(set()))

    def test_self_access_in_method_emits_nothing(self) -> None:
        """Verify self access in method emits nothing."""
        source = "class A:\n    def m(self):\n        return self._x\n"
        assert_that(kinds_for(source), equal_to(set()))

    def test_attr_field_records_offending_name(self) -> None:
        """Verify attr field records offending name."""
        errors = list(check_private_access(ast.parse("obj._secret\n")))
        assert_that([err.attr for err in errors], equal_to(["_secret"]))
