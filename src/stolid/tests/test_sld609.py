"""Tests for SLD609: parameter used only as a branch condition."""

from __future__ import annotations

import unittest

from .code_parser import (
    assert_absent,
    assert_message_contains_all,
    assert_present,
)

_SLD609_PRESENT: list[tuple[str, str]] = [
    (
        "boolean_flag",
        "def fetch(uid, mark):\n"
        "    if mark:\n"
        "        do(uid)\n"
        "    return uid\n",
    ),
    (
        "if_else_body",
        "def f(x, flag):\n"
        "    if flag:\n"
        "        do(x)\n"
        "    else:\n"
        "        undo(x)\n",
    ),
    (
        "string_equality_branch",
        "def render(data, fmt):\n"
        "    if fmt == 'json':\n"
        "        return to_json(data)\n"
        "    return to_xml(data)\n",
    ),
    (
        "ternary_test",
        "def greet(name, formal):\n"
        "    return ('Good day' if formal else 'Hi') + name\n",
    ),
    (
        "while_test",
        "def loop(x, keep):\n"
        "    while keep:\n"
        "        x = step(x)\n"
        "    return x\n",
    ),
    (
        "assert_test",
        "def use(x, must):\n    assert must\n    return x\n",
    ),
    (
        "assert_with_msg",
        "def use(x, must):\n    assert must, 'boom'\n    return x\n",
    ),
    (
        "match_subject",
        "def f(x, mode):\n"
        "    match mode:\n"
        "        case 1:\n"
        "            return x\n"
        "        case _:\n"
        "            return -x\n",
    ),
    (
        "match_guard",
        "def f(x, mode):\n"
        "    match x:\n"
        "        case n if mode:\n"
        "            return n\n"
        "        case _:\n"
        "            return 0\n",
    ),
    (
        "comprehension_if",
        "def f(xs, keep):\n    return [x for x in xs if keep]\n",
    ),
    (
        "not_unary",
        "def f(x, off):\n    if not off:\n        return x\n    return -x\n",
    ),
    (
        "boolop_and",
        "def f(x, flag):\n"
        "    if flag and ready():\n"
        "        return x\n"
        "    return -x\n",
    ),
    (
        "async_function",
        "async def f(x, mark):\n"
        "    if mark:\n"
        "        x = await refresh(x)\n"
        "    return x\n",
    ),
    (
        "kwonly_flag",
        "def f(x, *, mark):\n    if mark:\n        return x\n    return -x\n",
    ),
    (
        "posonly_flag",
        "def f(x, mark, /):\n    if mark:\n        return x\n    return -x\n",
    ),
    (
        "membership_in_literal_tuple",
        "def f(x, mode):\n"
        "    if mode in ('a', 'b'):\n"
        "        return x\n"
        "    return -x\n",
    ),
    (
        "membership_in_string_literal",
        "def classify(c):\n    if c in 'aeiou':\n        return 1\n    return 2\n",
    ),
]


_SLD609_ABSENT: list[tuple[str, str]] = [
    (
        "data_assignment",
        "def set_enabled(widget, enabled):\n    widget.enabled = enabled\n",
    ),
    (
        "pure_forwarder",
        "def forward(x, flag):\n    return helper(x, flag)\n",
    ),
    (
        "none_default_idiom",
        "def parse(text, opts=None):\n"
        "    if opts is None:\n"
        "        opts = default_opts()\n"
        "    return run(text, opts)\n",
    ),
    (
        "value_returned",
        "def is_ready(job):\n    return job.status == 'done'\n",
    ),
    (
        "self_and_cls_skipped",
        "class C:\n"
        "    def m(self):\n"
        "        if self:\n"
        "            return 1\n"
        "        return 2\n"
        "    @classmethod\n"
        "    def n(cls):\n"
        "        if cls:\n"
        "            return 1\n"
        "        return 2\n",
    ),
    (
        "varargs_skipped",
        "def f(*args, **kwargs):\n"
        "    if args:\n"
        "        return kwargs\n"
        "    return None\n",
    ),
    (
        "unused_param",
        "def f(x):\n    return 1\n",
    ),
    (
        "attribute_owner",
        "def f(obj):\n"
        "    if obj.ready:\n"
        "        return obj\n"
        "    return None\n",
    ),
    (
        "subscript_owner",
        "def f(arr):\n    if arr[0]:\n        return arr\n    return None\n",
    ),
    (
        "binop_operand",
        "def f(p):\n    if p + 1:\n        return p\n    return -p\n",
    ),
    (
        "nested_function_captures",
        "def outer(p):\n"
        "    def inner():\n"
        "        return p\n"
        "    return inner\n",
    ),
    (
        "lambda_captures",
        "def f(p):\n    return lambda x: p\n",
    ),
    (
        "comprehension_iter_is_data",
        "def f(xs):\n    return [y for y in xs]\n",
    ),
    (
        "call_with_flag_as_arg",
        "def f(p):\n    if helper(p):\n        return 1\n    return 2\n",
    ),
    (
        "call_with_flag_as_kwarg",
        "def f(p):\n    if helper(x=p):\n        return 1\n    return 2\n",
    ),
    (
        "store_then_used",
        "def f(p):\n"
        "    p = compute()\n"
        "    if p:\n"
        "        return p\n"
        "    return -p\n",
    ),
    (
        "assert_message_uses_param",
        "def f(p):\n    assert p, format(p)\n    return 1\n",
    ),
    (
        "ifexp_body_is_data",
        "def f(p):\n    return p if ready() else -p\n",
    ),
    (
        "membership_in_runtime_value",
        "def find(needle, hay):\n    return [x for x in hay if needle in x]\n",
    ),
    (
        "membership_in_runtime_name",
        "def f(key, table):\n"
        "    if key in table:\n"
        "        return 1\n"
        "    return 2\n",
    ),
    (
        "compare_comparator_is_data",
        "def lookup(name, allowed):\n"
        "    if name in allowed:\n"
        "        return name\n"
        "    return None\n",
    ),
    (
        "compare_right_side_is_data",
        "def matches(item, target):\n"
        "    if item.name == target:\n"
        "        return item\n"
        "    return None\n",
    ),
]


class TestSLD609FlagParameter(unittest.TestCase):
    """Tests for SLD609: parameter used only as a branch condition."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD609_PRESENT, "SLD609")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD609_ABSENT, "SLD609")

    def test_message_names_parameter_and_function(self) -> None:
        """Verify the SLD609 message names the parameter and the function."""
        assert_message_contains_all(
            self,
            "def fetch(uid, mark):\n    if mark:\n        do(uid)\n    return uid\n",
            "SLD609",
            ("mark", "fetch"),
        )
