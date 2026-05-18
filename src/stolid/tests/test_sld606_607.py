"""Tests for SLD606 / SLD607: try/finally and try/except/pass."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, equal_to

from .code_parser import (
    assert_absent,
    assert_present,
    check_code,
    get_error_codes,
)

_SLD606_PRESENT: list[tuple[str, str]] = [
    (
        "try_finally_at_module_level",
        "try:\n    do()\nfinally:\n    cleanup()\n",
    ),
    (
        "try_finally_in_regular_function",
        "def f():\n    try:\n        do()\n    finally:\n        cleanup()\n",
    ),
    (
        "try_except_finally_in_regular_function",
        "def f():\n    try:\n        do()\n"
        "    except ValueError:\n        log()\n"
        "    finally:\n        cleanup()\n",
    ),
    (
        "try_finally_in_nested_function_under_contextmanager",
        "import contextlib\n\n"
        "@contextlib.contextmanager\n"
        "def cm():\n"
        "    def inner():\n"
        "        try:\n"
        "            do()\n"
        "        finally:\n"
        "            cleanup()\n"
        "    inner()\n"
        "    yield\n",
    ),
    (
        "try_finally_in_function_with_unrelated_decorator",
        "import functools\n\n"
        "@functools.lru_cache\n"
        "def f():\n"
        "    try:\n        do()\n    finally:\n        cleanup()\n",
    ),
]


_SLD606_ABSENT: list[tuple[str, str]] = [
    (
        "try_finally_in_contextmanager_bare",
        "from contextlib import contextmanager\n\n"
        "@contextmanager\n"
        "def cm():\n"
        "    setup()\n"
        "    try:\n        yield\n    finally:\n        cleanup()\n",
    ),
    (
        "try_finally_in_contextmanager_qualified",
        "import contextlib\n\n"
        "@contextlib.contextmanager\n"
        "def cm():\n"
        "    try:\n        yield\n    finally:\n        cleanup()\n",
    ),
    (
        "try_finally_in_asynccontextmanager",
        "from contextlib import asynccontextmanager\n\n"
        "@asynccontextmanager\n"
        "async def cm():\n"
        "    try:\n        yield\n    finally:\n        cleanup()\n",
    ),
    (
        "try_finally_in_contextmanager_called_decorator",
        "from contextlib import contextmanager\n\n"
        "@contextmanager()\n"
        "def cm():\n"
        "    try:\n        yield\n    finally:\n        cleanup()\n",
    ),
    (
        "try_except_no_finally",
        "try:\n    do()\nexcept ValueError:\n    log()\n",
    ),
    (
        "subscript_decorator_does_not_exempt",
        "decs = [None]\n\n" "@decs[0]\n" "def f():\n    return 1\n",
    ),
]


_SLD607_PRESENT: list[tuple[str, str]] = [
    (
        "try_except_pass_at_module_level",
        "try:\n    do()\nexcept ValueError:\n    pass\n",
    ),
    (
        "try_except_pass_with_alias",
        "try:\n    do()\nexcept ValueError as exc:\n    pass\n",
    ),
    (
        "try_bare_except_pass",
        "try:\n    do()\nexcept:\n    pass\n",
    ),
    (
        "try_multiple_except_all_pass",
        "try:\n    do()\n"
        "except ValueError:\n    pass\n"
        "except TypeError:\n    pass\n",
    ),
    (
        "try_except_pass_in_function",
        "def f():\n    try:\n        do()\n" "    except ValueError:\n        pass\n",
    ),
    (
        "try_except_pass_in_contextmanager",
        "from contextlib import contextmanager\n\n"
        "@contextmanager\n"
        "def cm():\n"
        "    try:\n        yield\n    except ValueError:\n        pass\n",
    ),
]


_SLD607_ABSENT: list[tuple[str, str]] = [
    (
        "try_except_with_real_handler",
        "try:\n    do()\nexcept ValueError:\n    log()\n",
    ),
    (
        "try_except_pass_with_else",
        "try:\n    do()\nexcept ValueError:\n    pass\nelse:\n    other()\n",
    ),
    (
        "try_except_pass_with_finally",
        "try:\n    do()\nexcept ValueError:\n    pass\nfinally:\n    cleanup()\n",
    ),
    (
        "try_mixed_pass_and_real_handler",
        "try:\n    do()\n"
        "except ValueError:\n    pass\n"
        "except TypeError:\n    log()\n",
    ),
    (
        "try_finally_only_no_handlers",
        "try:\n    do()\nfinally:\n    cleanup()\n",
    ),
    (
        "try_except_with_two_pass_statements",
        "try:\n    do()\nexcept ValueError:\n    pass\n    pass\n",
    ),
]


_SLD606_COUNT: list[tuple[str, str, int]] = [
    (
        "two_independent_try_finally",
        "try:\n    a()\nfinally:\n    cleanup_a()\n"
        "try:\n    b()\nfinally:\n    cleanup_b()\n",
        2,
    ),
    (
        "nested_try_finally_each_flagged",
        "try:\n    try:\n        do()\n    finally:\n        inner_cleanup()\n"
        "finally:\n    outer_cleanup()\n",
        2,
    ),
]


class TestSLD606TryFinally(unittest.TestCase):
    """Tests for SLD606: ``try``/``finally`` should be a context manager."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD606_PRESENT, "SLD606")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD606_ABSENT, "SLD606")

    def test_count(self) -> None:
        """Verify count."""
        for name, code, count in _SLD606_COUNT:
            with self.subTest(name=name):
                assert_that(
                    get_error_codes(code).count("SLD606"),
                    equal_to(count),
                )

    def test_message_describes_replacement(self) -> None:
        """Verify the SLD606 message points at the replacement."""
        code = "try:\n    do()\nfinally:\n    cleanup()\n"
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD606" in msg]
        assert_that(messages[0], contains_string("contextlib.contextmanager"))


class TestSLD607TryExceptPass(unittest.TestCase):
    """Tests for SLD607: ``try``/``except``/``pass`` should be ``suppress``."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD607_PRESENT, "SLD607")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD607_ABSENT, "SLD607")

    def test_message_mentions_suppress(self) -> None:
        """Verify the SLD607 message points at contextlib.suppress."""
        code = "try:\n    do()\nexcept ValueError:\n    pass\n"
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD607" in msg]
        assert_that(messages[0], contains_string("suppress"))
