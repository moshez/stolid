"""Tests for SLD8xx — the cross-file duplicate detector (positive/negative)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, greater_than, has_item, has_length

from ._sld8xx_shared import (
    TAKE_BODY,
    assert_pair_negative,
    assert_pair_positive,
    files,
    just_801,
)
from .code_parser import check_multifile, multifile_codes

_POSITIVE_CASES: list[tuple[str, str, str]] = [
    (
        "rename_invariance",
        "import itertools\n"
        "def take(seq, n):\n"
        "    return list(itertools.islice(seq, n))\n",
        "import itertools\n"
        "def take(items, count):\n"
        "    return list(itertools.islice(items, count))\n",
    ),
    (
        "hello_goodbye",
        "def hello(a, b, c, d):\n    return a*b + c*d\n",
        "def goodbye(e, f, g, h):\n    return e*f + g*h\n",
    ),
    (
        "literal_type_collapse",
        "import itertools\n"
        "def take(seq): return list(itertools.islice(seq, range(10)))\n",
        "import itertools\n"
        "def take(seq): return list(itertools.islice(seq, range(100)))\n",
    ),
    (
        "string_literal_collapse",
        "import itertools\n"
        'def take(seq): return list(itertools.islice(seq, "hello"))\n',
        "import itertools\n"
        'def take(seq): return list(itertools.islice(seq, "world"))\n',
    ),
    (
        "closure_position_match",
        "def outer(a, b):\n" "    def inner():\n" "        return a + a + a + a + a\n",
        "def outer(x, y):\n" "    def inner():\n" "        return x + x + x + x + x\n",
    ),
    (
        "comprehension_scope",
        "def f(xs, ys):\n" "    return [a*b + a*b + a*b for a, b in zip(xs, ys)]\n",
        "def g(ms, ns):\n" "    return [m*n + m*n + m*n for m, n in zip(ms, ns)]\n",
    ),
]


_BIG_EXPR = "a*b + c*d + e*f + g*h + i*j"

_SUBEXPR_A = f"def f(a, b, c, d, e, f, g, h, i, j):\n    return {_BIG_EXPR}\n"
_SUBEXPR_B = (
    "def g(a, b, c, d, e, f, g, h, i, j):\n"
    "    if a > 0:\n"
    f"        return {_BIG_EXPR}\n"
)


_NEGATIVE_CASES: list[tuple[str, str, str]] = [
    (
        "singleton_preserved",
        "def f(x): return 1 if x is None else 2\n",
        "def f(x): return 1 if x is False else 2\n",
    ),
    (
        "different_module_qualified_call",
        "import itertools\n"
        "def take(seq, n): return list(itertools.islice(seq, n))\n",
        "import functools\n"
        "def take(seq, n): return list(functools.reduce(seq, n))\n",
    ),
    (
        "different_operator",
        "def f(a, b, c, d): return a + b + c + d\n",
        "def g(a, b, c, d): return a - b - c - d\n",
    ),
    (
        "argument_order_matters",
        "def f(a, b, c, d): return a + b + c + d\n",
        "def g(a, b, c, d): return b + a + d + c\n",
    ),
    (
        "async_vs_sync",
        "def f(x): return x*x\n",
        "async def f(x): return x*x\n",
    ),
    (
        "listcomp_vs_generator",
        "def f(xs): return [x for x in xs]\n",
        "def g(xs): return (x for x in xs)\n",
    ),
    (
        "closure_position_mismatch",
        "def outer(a, b):\n" "    def inner():\n" "        return a + a + a + a + a\n",
        "def outer(x, y):\n" "    def inner():\n" "        return y + y + y + y + y\n",
    ),
    (
        "distinct_annotations",
        "def f(x: int) -> str: return str(x)\n",
        "def f(x: float) -> bytes: return bytes(x)\n",
    ),
]


_SINGLE_FILE_ABSENT: list[tuple[str, str]] = [
    ("empty_file", ""),
    (
        "recursive_function_self",
        "def factorial(n):\n"
        "    return 1 if n == 0 else n * factorial(n - 1) * factorial(n - 2)\n",
    ),
    (
        "long_assertion_sequence",
        "def check(obj):\n"
        + "".join(
            f"    assert obj.{ch} == {i}\n"
            for i, ch in enumerate("abcdefghijklmnopqrst")
        ),
    ),
]


class TestPositiveClones(unittest.TestCase):
    """Cases where SLD801 should be reported across two files."""

    def test_two_file_clones(self) -> None:
        assert_pair_positive(self, _POSITIVE_CASES)

    def test_take_quartet(self) -> None:
        result = check_multifile({f"f{i}.py": TAKE_BODY for i in range(4)})
        codes = [msg.split()[0] for _, _, _, msg in result]
        assert_that(codes.count("SLD801"), equal_to(4))

    def test_nested_inner_collide(self) -> None:
        a = (
            "def foo(a, b):\n"
            "    t = 5\n"
            "    def inner(c):\n"
            "        return c*c + c*c*c + c*c*c*c\n"
        )
        b = (
            "def bar(g, h):\n"
            "    t = 7 + 2\n"
            "    s = 5\n"
            "    def inner2(x):\n"
            "        return x*x + x*x*x + x*x*x*x\n"
        )
        result = just_801(check_multifile(files(**{"a.py": a, "b.py": b})))
        assert_that(result, has_length(2))

    def test_same_file_duplication(self) -> None:
        body = (
            "import itertools\n"
            "def take1(seq, n): return list(itertools.islice(seq, n))\n"
            "def take2(seq, n): return list(itertools.islice(seq, n))\n"
            "def take3(seq, n): return list(itertools.islice(seq, n))\n"
        )
        result = just_801(check_multifile({"f.py": body}))
        assert_that(result, has_length(3))

    def test_cross_class_method_duplication(self) -> None:
        a = (
            "import itertools\n"
            "class A:\n"
            "    def fetch(self, seq, n):\n"
            "        return list(itertools.islice(seq, n))\n"
        )
        b = (
            "import itertools\n"
            "class B:\n"
            "    def gather(self, items, count):\n"
            "        return list(itertools.islice(items, count))\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes.count("SLD801"), greater_than(0))

    def test_subexpression_collision(self) -> None:
        codes = multifile_codes(files(**{"a.py": _SUBEXPR_A, "b.py": _SUBEXPR_B}))
        assert_that(codes, has_item("SLD801"))


class TestNegativeNoClones(unittest.TestCase):
    """Cases that must not be reported."""

    def test_two_file_no_clones(self) -> None:
        assert_pair_negative(self, _NEGATIVE_CASES)

    def test_single_file_no_clones(self) -> None:
        for name, body in _SINGLE_FILE_ABSENT:
            with self.subTest(name=name):
                codes = multifile_codes({"f.py": body})
                assert_that("SLD801" in codes, equal_to(False))

    def test_below_size_threshold(self) -> None:
        codes = multifile_codes({f"f{i}.py": "def f(): return 1\n" for i in range(5)})
        assert_that("SLD801" in codes, equal_to(False))

    def test_below_score_threshold(self) -> None:
        body = (
            "class C:\n"
            "    def __init__(self, a, b, c, d, e):\n"
            "        self.a = a\n"
            "        self.b = b\n"
            "        self.c = c\n"
            "        self.d = d\n"
            "        self.e = e\n"
        )
        codes = multifile_codes({f"f{i}.py": body for i in range(5)})
        assert_that("SLD801" in codes, equal_to(False))
