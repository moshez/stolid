"""Tests for SLD703: near-duplicate variable names in a scope."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, equal_to

from .code_parser import assert_absent, assert_present, check_code

_PRESENT: list[tuple[str, str]] = [
    (
        "module_substitution",
        "mosh = 1\nmish = 2\n",
    ),
    (
        "module_insertion_end",
        "mosh = 1\nmoshe = 2\n",
    ),
    (
        "module_insertion_start",
        "ish = 1\nmish = 2\n",
    ),
    (
        "module_insertion_middle",
        "mish = 1\nmoish = 2\n",
    ),
    (
        "function_params",
        "def fn(foo, fooo):\n    return foo\n",
    ),
    (
        "function_locals",
        "def fn():\n    count = 1\n    counts = 2\n    return counts\n",
    ),
    (
        "function_name_vs_local",
        "def name():\n    pass\ndef names():\n    pass\n",
    ),
    (
        "class_attributes",
        "class Box:\n    width = 1\n    widths = 2\n",
    ),
    (
        "for_target_vs_local",
        "def fn():\n    nodes = []\n    for node in nodes:\n        pass\n",
    ),
    (
        "single_letter_non_loop_pair",
        "x = 1\ny = 2\n",
    ),
    (
        "import_collision",
        "from typing import List\nimport list_module as Lists\n",
    ),
    (
        "starred_target",
        (
            "items = []\n"
            "def fn():\n"
            "    first = 1\n"
            "    *firs, last = items\n"
            "    return first, firs, last\n"
        ),
    ),
    (
        "walrus_binding",
        (
            "def fn():\n"
            "    value = 0\n"
            "    if (values := [1, 2, 3]):\n"
            "        return values\n"
            "    return value\n"
        ),
    ),
    (
        "except_handler_name",
        (
            "def fn():\n"
            "    err = None\n"
            "    try:\n"
            "        pass\n"
            "    except Exception as errr:\n"
            "        err = errr\n"
            "    return err\n"
        ),
    ),
]


_ABSENT: list[tuple[str, str]] = [
    (
        "different_names",
        "alpha = 1\nbeta = 2\n",
    ),
    (
        "two_letter_diff_substitution",
        "abc = 1\naxy = 2\n",
    ),
    (
        "two_letter_diff_length",
        "ab = 1\nabcd = 2\n",
    ),
    (
        "same_name_rebound",
        "x = 1\nx = 2\n",
    ),
    (
        "single_letter_loop_iters",
        "for i in range(10):\n    pass\nfor j in range(10):\n    pass\n",
    ),
    (
        "single_letter_destructured_loop",
        "items = []\nfor i, thing in items:\n    print(i, thing)\n",
    ),
    (
        "separate_function_scopes",
        "def first():\n    foo = 1\n\n\ndef second():\n    fooo = 2\n",
    ),
    (
        "method_scope_isolated",
        (
            "class Box:\n"
            "    def width(self):\n"
            "        return 1\n"
            "    def length(self):\n"
            "        widths = 2\n"
            "        return widths\n"
        ),
    ),
    (
        "augmented_assignment_not_binding",
        "count = 1\ncount += 1\n",
    ),
    (
        "digit_substitution_not_a_letter",
        "SLD304 = 1\nSLD305 = 2\n",
    ),
    (
        "digit_insertion_not_a_letter",
        "foo = 1\nfoo1 = 2\n",
    ),
    (
        "underscore_insertion_not_a_letter",
        "foo = 1\n_foo = 2\n",
    ),
]


class TestSLD703(unittest.TestCase):
    """Tests for SLD703 near-duplicate name detection."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _PRESENT, "SLD703")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _ABSENT, "SLD703")

    def test_message_includes_both_names(self) -> None:
        """Verify message includes both names."""
        errors = check_code("alpha = 1\nalphas = 2\n")
        messages = [msg for _, _, msg in errors if "SLD703" in msg]
        assert_that(messages[0], contains_string("alpha"))
        assert_that(messages[0], contains_string("alphas"))

    def test_reports_on_later_binding(self) -> None:
        """Verify reports on later binding."""
        errors = check_code("alpha = 1\nalphas = 2\n")
        rows = [line for line, _, msg in errors if "SLD703" in msg]
        assert_that(rows, equal_to([2]))

    def test_for_loop_destructured_single_letter_exempt(self) -> None:
        """Verify destructured loop single-letter is exempt."""
        source = "items = []\nfor i, j in items:\n    print(i, j)\n"
        codes = [msg.split()[0] for _, _, msg in check_code(source)]
        assert_that("SLD703" in codes, equal_to(False))
