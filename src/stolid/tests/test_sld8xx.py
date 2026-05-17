"""Tests for SLD8xx — the cross-file duplicate detector (positive/negative)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, greater_than, has_item, has_length

from ._sld8xx_shared import TAKE_BODY, files, just_801
from .code_parser import check_multifile, multifile_codes


class TestPositiveClones(unittest.TestCase):
    """Cases that should be reported."""

    def test_take_quartet(self) -> None:
        result = check_multifile({f"f{i}.py": TAKE_BODY for i in range(4)})
        codes = [msg.split()[0] for _, _, _, msg in result]
        assert_that(codes.count("SLD801"), equal_to(4))

    def test_rename_invariance(self) -> None:
        a = (
            "import itertools\n"
            "def take(seq, n):\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        b = (
            "import itertools\n"
            "def take(items, count):\n"
            "    return list(itertools.islice(items, count))\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes.count("SLD801"), equal_to(2))

    def test_hello_goodbye(self) -> None:
        a = "def hello(a, b, c, d):\n    return a*b + c*d\n"
        b = "def goodbye(e, f, g, h):\n    return e*f + g*h\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

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

    def test_literal_type_collapse(self) -> None:
        a = (
            "import itertools\n"
            "def take(seq): return list(itertools.islice(seq, range(10)))\n"
        )
        b = (
            "import itertools\n"
            "def take(seq): return list(itertools.islice(seq, range(100)))\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_string_literal_collapse(self) -> None:
        a = (
            "import itertools\n"
            'def take(seq): return list(itertools.islice(seq, "hello"))\n'
        )
        b = (
            "import itertools\n"
            'def take(seq): return list(itertools.islice(seq, "world"))\n'
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_closure_position_match(self) -> None:
        a = (
            "def outer(a, b):\n"
            "    def inner():\n"
            "        return a + a + a + a + a\n"
        )
        b = (
            "def outer(x, y):\n"
            "    def inner():\n"
            "        return x + x + x + x + x\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_comprehension_scope(self) -> None:
        a = "def f(xs, ys):\n" "    return [a*b + a*b + a*b for a, b in zip(xs, ys)]\n"
        b = "def g(ms, ns):\n" "    return [m*n + m*n + m*n for m, n in zip(ms, ns)]\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_subexpression_collision(self) -> None:
        big_expr = "a*b + c*d + e*f + g*h + i*j"
        a = f"def f(a, b, c, d, e, f, g, h, i, j):\n    return {big_expr}\n"
        b = (
            "def g(a, b, c, d, e, f, g, h, i, j):\n"
            "    if a > 0:\n"
            f"        return {big_expr}\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))


class TestNegativeNoClones(unittest.TestCase):
    """Cases that must not be reported."""

    def test_singleton_preserved(self) -> None:
        a = "def f(x): return 1 if x is None else 2\n"
        b = "def f(x): return 1 if x is False else 2\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that("SLD801" in codes, equal_to(False))

    def test_different_module_qualified_call(self) -> None:
        a = (
            "import itertools\n"
            "def take(seq, n): return list(itertools.islice(seq, n))\n"
        )
        b = (
            "import functools\n"
            "def take(seq, n): return list(functools.reduce(seq, n))\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that("SLD801" in codes, equal_to(False))

    def test_different_operator(self) -> None:
        a = "def f(a, b, c, d): return a + b + c + d\n"
        b = "def g(a, b, c, d): return a - b - c - d\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that("SLD801" in codes, equal_to(False))

    def test_argument_order_matters(self) -> None:
        a = "def f(a, b, c, d): return a + b + c + d\n"
        b = "def g(a, b, c, d): return b + a + d + c\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that("SLD801" in codes, equal_to(False))

    def test_async_vs_sync(self) -> None:
        a = "def f(x): return x*x\n"
        b = "async def f(x): return x*x\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that("SLD801" in codes, equal_to(False))

    def test_listcomp_vs_generator(self) -> None:
        a = "def f(xs): return [x for x in xs]\n"
        b = "def g(xs): return (x for x in xs)\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that("SLD801" in codes, equal_to(False))

    def test_closure_position_mismatch(self) -> None:
        a = (
            "def outer(a, b):\n"
            "    def inner():\n"
            "        return a + a + a + a + a\n"
        )
        b = (
            "def outer(x, y):\n"
            "    def inner():\n"
            "        return y + y + y + y + y\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that("SLD801" in codes, equal_to(False))

    def test_below_size_threshold(self) -> None:
        body = "def f(): return 1\n"
        codes = multifile_codes({f"f{i}.py": body for i in range(5)})
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

    def test_long_assertion_sequence(self) -> None:
        lines = ["def check(obj):"]
        fields = "abcdefghijklmnopqrst"
        for i, field_name in enumerate(fields):
            lines.append(f"    assert obj.{field_name} == {i}")
        body = "\n".join(lines) + "\n"
        codes = multifile_codes({"f.py": body})
        assert_that("SLD801" in codes, equal_to(False))

    def test_empty_file(self) -> None:
        codes = multifile_codes({"f.py": ""})
        assert_that("SLD801" in codes, equal_to(False))

    def test_recursive_function_no_self_clone(self) -> None:
        body = (
            "def factorial(n):\n"
            "    return 1 if n == 0 else n * factorial(n - 1) * factorial(n - 2)\n"
        )
        codes = multifile_codes({"f.py": body})
        assert_that("SLD801" in codes, equal_to(False))

    def test_distinct_annotations(self) -> None:
        a = "def f(x: int) -> str: return str(x)\n"
        b = "def f(x: float) -> bytes: return bytes(x)\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that("SLD801" in codes, equal_to(False))
