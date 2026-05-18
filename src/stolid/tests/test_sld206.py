"""Tests for SLD206: NotImplementedError outside @singledispatch is prohibited."""

from __future__ import annotations

import unittest

from .code_parser import assert_absent, assert_count, assert_present

_PRESENT: list[tuple[str, str]] = [
    (
        "raise_at_module_level",
        "raise NotImplementedError\n",
    ),
    (
        "raise_in_regular_function",
        "def f():\n    raise NotImplementedError\n",
    ),
    (
        "raise_call_in_regular_function",
        "def f():\n    raise NotImplementedError()\n",
    ),
    (
        "raise_with_message_in_regular_function",
        'def f():\n    raise NotImplementedError("not done")\n',
    ),
    (
        "raise_in_method",
        "class C:\n    def m(self):\n        raise NotImplementedError\n",
    ),
    (
        "raise_in_function_with_unrelated_decorator",
        "import functools\n\n"
        "@functools.lru_cache\n"
        "def f(x):\n    raise NotImplementedError\n",
    ),
    (
        "raise_in_register_function",
        "import functools\n\n"
        "@functools.singledispatch\n"
        "def f(x):\n    raise NotImplementedError\n\n"
        "@f.register\n"
        "def _(x: int):\n    raise NotImplementedError\n",
    ),
    (
        "raise_in_nested_function_under_singledispatch",
        "import functools\n\n"
        "@functools.singledispatch\n"
        "def f(x):\n"
        "    def helper():\n"
        "        raise NotImplementedError\n"
        "    return helper\n",
    ),
    (
        "except_clause_at_module_level",
        "try:\n    do()\nexcept NotImplementedError:\n    pass\n",
    ),
    (
        "except_clause_in_regular_function",
        "def f():\n    try:\n        do()\n"
        "    except NotImplementedError:\n        pass\n",
    ),
    (
        "raise_in_async_regular_function",
        "async def f():\n    raise NotImplementedError\n",
    ),
]


_ABSENT: list[tuple[str, str]] = [
    (
        "raise_in_singledispatch_function_qualified",
        "import functools\n\n"
        "@functools.singledispatch\n"
        "def f(x):\n    raise NotImplementedError\n",
    ),
    (
        "raise_in_singledispatch_function_bare",
        "from functools import singledispatch\n\n"
        "@singledispatch\n"
        "def f(x):\n    raise NotImplementedError\n",
    ),
    (
        "raise_call_with_message_in_singledispatch",
        "from functools import singledispatch\n\n"
        "@singledispatch\n"
        "def f(x):\n"
        '    raise NotImplementedError("override me")\n',
    ),
    (
        "no_use_of_not_implemented_error",
        "def f():\n    return 1\n",
    ),
    (
        "other_exception_in_regular_function",
        "def f():\n    raise ValueError\n",
    ),
    (
        "singledispatch_with_other_decorators_stacked",
        "import functools\n\n"
        "@staticmethod\n"
        "@functools.singledispatch\n"
        "def f(x):\n    raise NotImplementedError\n",
    ),
]


_COUNT: list[tuple[str, str, int]] = [
    (
        "singledispatch_default_ok_register_flagged",
        "import functools\n\n"
        "@functools.singledispatch\n"
        "def f(x):\n    raise NotImplementedError\n\n"
        "@f.register\n"
        "def _(x: int):\n    raise NotImplementedError\n",
        1,
    ),
    (
        "two_raises_in_regular_function",
        "def f(x):\n"
        "    if x:\n        raise NotImplementedError\n"
        "    raise NotImplementedError\n",
        2,
    ),
    (
        "except_and_raise_in_regular_function",
        "def f():\n"
        "    try:\n        raise NotImplementedError\n"
        "    except NotImplementedError:\n"
        "        raise NotImplementedError\n",
        3,
    ),
]


class TestSLD206NotImplementedErrorProhibited(unittest.TestCase):
    """Tests for SLD206: NotImplementedError outside singledispatch is prohibited."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _PRESENT, "SLD206")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _ABSENT, "SLD206")

    def test_count(self) -> None:
        """Verify count."""
        assert_count(self, _COUNT, "SLD206")
