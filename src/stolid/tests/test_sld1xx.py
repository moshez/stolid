"""Tests for SLD1xx error codes (mocking, dynamic execution)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, empty, has_length

from .code_parser import (
    assert_absent,
    assert_count,
    assert_present,
    check_code,
    get_error_codes,
)

_SLD102_PRESENT: list[tuple[str, str]] = [
    ("import_patch_from_unittest_mock", "from unittest.mock import patch\n"),
    ("import_patch_from_mock", "from mock import patch\n"),
    (
        "patch_aliased_import",
        "from unittest.mock import patch as p\n\np('module.thing')\n",
    ),
    (
        "patch_decorator",
        "from unittest.mock import patch\n\n"
        "@patch('module.thing')\n"
        "def test_something():\n    pass\n",
    ),
    (
        "patch_context_manager",
        "from unittest.mock import patch\n\n"
        "def test_something():\n"
        "    with patch('module.thing'):\n        pass\n",
    ),
    (
        "patch_object_call",
        "from unittest.mock import patch\n\n"
        "def test_something():\n"
        "    patch.object(obj, 'attr')\n",
    ),
    (
        "unittest_mock_patch_attribute_access",
        "import unittest.mock\n\nunittest.mock.patch('thing')\n",
    ),
    ("mock_module_patch_attribute", "import mock\n\nmock.patch('thing')\n"),
    (
        "patch_object_via_mock_module_attribute",
        "import unittest.mock\n\nunittest.mock.patch.object(obj, 'attr')\n",
    ),
    (
        "attribute_patch_on_nested_attribute",
        "import unittest\n\nunittest.mock.patch('thing')\n",
    ),
    (
        "patch_object_via_deeply_nested_attribute",
        "import unittest\n\nunittest.mock.patch.object(obj, 'attr')\n",
    ),
]


_SLD102_ABSENT: list[tuple[str, str]] = [
    ("mock_import_allowed", "from unittest.mock import Mock, MagicMock\n"),
    (
        "with_statement_non_call",
        "class MyClass:\n    pass\n\nwith some_context:\n    pass\n",
    ),
    ("with_statement_call_non_name", "with obj.method():\n    pass\n"),
    (
        "patch_attribute_not_mock",
        "class MyPatcher:\n    patch = None\n\nobj = MyPatcher()\nobj.patch\n",
    ),
    ("attribute_patch_on_non_mock_name", "something.patch('value')\n"),
    ("patch_object_with_non_patch_name", "something.object(1, 2)\n"),
    ("attribute_patch_nested_not_mock", "foo.bar.patch\n"),
    ("call_object_func_value_attribute_not_patch", "foo.bar.object(thing)\n"),
    ("call_object_func_value_name_not_patch", "factory.object(MyClass)\n"),
    ("call_object_on_non_patch_attribute", "factory.object(MyClass)\n"),
    (
        "patch_object_via_attribute_value_name_not_patch",
        "something.object(obj, 'attr')\n",
    ),
]


_SLD102_COUNT: list[tuple[str, str, int]] = [
    (
        "import_patch_among_multiple",
        "from unittest.mock import Mock, patch, MagicMock\n",
        1,
    ),
    (
        "call_with_attribute_func_not_object",
        "from unittest.mock import patch\n\npatch.dict({})\n",
        1,
    ),
    (
        "with_non_patch_function_call",
        "from unittest.mock import patch\n\nwith open('file.txt'):\n    pass\n",
        1,
    ),
    (
        "call_func_attribute_not_object",
        "from unittest.mock import patch\n\nresult = patch.dict({})\n",
        1,
    ),
    (
        "call_func_is_attribute_not_object",
        "from unittest.mock import patch\n\nx = patch.something('module')\n",
        1,
    ),
]


class TestSLD102(unittest.TestCase):
    """Tests for SLD102: patch/mock detection."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD102_PRESENT, "SLD102")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD102_ABSENT, "SLD102")

    def test_count(self) -> None:
        """Verify count."""
        assert_count(self, _SLD102_COUNT, "SLD102")

    def test_mock_import_no_errors(self) -> None:
        """Verify mock import no errors."""
        assert_that(
            get_error_codes("from unittest.mock import Mock, MagicMock\n"),
            empty(),
        )


_SLD103_PRESENT: list[tuple[str, str]] = [
    ("exec_call", "exec('x = 1')\n"),
    ("eval_call", "result = eval('1 + 1')\n"),
    ("dunder_import_call", "mod = __import__('os')\n"),
    ("exec_with_globals", "exec('x = 1', {}, {})\n"),
    ("eval_in_expression", "values = [eval(s) for s in inputs]\n"),
    ("exec_aliased", "f = exec\n"),
    ("eval_aliased", "g = eval\n"),
    ("dunder_import_aliased", "loader = __import__\n"),
    ("exec_in_default_arg", "def run(code, _exec=exec):\n    _exec(code)\n"),
    (
        "eval_inside_function",
        "def evaluate(source):\n    return eval(source)\n",
    ),
]


_SLD103_ABSENT: list[tuple[str, str]] = [
    ("regular_function_call", "print('hello')\n"),
    ("ast_literal_eval", "import ast\n\nast.literal_eval('1')\n"),
    ("exec_as_attribute", "obj.exec()\n"),
    ("eval_as_attribute", "obj.eval(x)\n"),
    ("exec_as_string_literal", "x = 'exec'\n"),
    ("exec_assignment_only", "exec = my_safe_runner\n"),
    ("del_exec", "del exec\n"),
    ("exec_in_all_list", "__all__ = ['exec']\n"),
]


_SLD103_COUNT: list[tuple[str, str, int]] = [
    (
        "alias_and_call",
        "f = exec\nf('x')\n",
        1,
    ),
    (
        "three_dangerous_in_one_line",
        "result = (exec, eval, __import__)\n",
        3,
    ),
    (
        "exec_called_twice",
        "exec('a')\nexec('b')\n",
        2,
    ),
]


class TestSLD103(unittest.TestCase):
    """Tests for SLD103: dangerous dynamic-execution builtins."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD103_PRESENT, "SLD103")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD103_ABSENT, "SLD103")

    def test_count(self) -> None:
        """Verify count."""
        assert_count(self, _SLD103_COUNT, "SLD103")

    def test_message_includes_name(self) -> None:
        """Verify message includes name."""
        errors = check_code("exec('x = 1')\n")
        sld103 = [msg for _, _, msg in errors if msg.startswith("SLD103")]
        assert_that(sld103, has_length(1))
        assert_that(sld103[0], contains_string("'exec'"))
