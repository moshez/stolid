"""Tests for SLD801 scope and binding features."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, has_item

from ._sld8xx_shared import files
from .code_parser import multifile_codes


class TestScopeFeatures(unittest.TestCase):
    """Tests for less-common scope and binding features."""

    def test_for_target_binding_normalizes(self) -> None:
        a = (
            "def f(xs):\n"
            "    for item in xs:\n"
            "        if item > 0:\n"
            "            print(item, item, item)\n"
        )
        b = (
            "def g(items):\n"
            "    for value in items:\n"
            "        if value > 0:\n"
            "            print(value, value, value)\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_with_as_binding_normalizes(self) -> None:
        a = (
            "def f(p):\n"
            "    with open(p) as fh:\n"
            "        if fh.read():\n"
            "            return fh.readline()\n"
        )
        b = (
            "def g(q):\n"
            "    with open(q) as handle:\n"
            "        if handle.read():\n"
            "            return handle.readline()\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_except_as_binding_normalizes(self) -> None:
        a = (
            "def f(x):\n"
            "    try:\n"
            "        return x.do()\n"
            "    except Exception as exc:\n"
            "        return exc.args + exc.args\n"
        )
        b = (
            "def g(y):\n"
            "    try:\n"
            "        return y.do()\n"
            "    except Exception as err:\n"
            "        return err.args + err.args\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_annassign_binding_normalizes(self) -> None:
        a = "def f(x):\n    y: int = x.compute()\n    return y + y + y\n"
        b = "def g(z):\n    out: int = z.compute()\n    return out + out + out\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_walrus_binding_normalizes(self) -> None:
        a = "def f(xs):\n    if (n := xs.size()) > 0:\n        return n + n + n\n"
        b = (
            "def g(items):\n"
            "    if (count := items.size()) > 0:\n"
            "        return count + count + count\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_starred_target_binding(self) -> None:
        a = (
            "def f(xs):\n"
            "    first, *rest = xs.split()\n"
            "    return rest + rest + rest\n"
        )
        b = (
            "def g(items):\n"
            "    head, *tail = items.split()\n"
            "    return tail + tail + tail\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_vararg_kwarg_binding_normalizes(self) -> None:
        a = (
            "def f(*args, **kw):\n"
            "    if args:\n"
            "        return kw.values() + args\n"
        )
        b = "def g(*xs, **ys):\n    if xs:\n        return ys.values() + xs\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_lambda_normalizes(self) -> None:
        a = (
            "def f(xs):\n"
            "    return sorted(xs, key=lambda item: item.score + item.bonus)\n"
        )
        b = (
            "def g(items):\n"
            "    return sorted(items, key=lambda x: x.score + x.bonus)\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_lambda_with_star_args(self) -> None:
        a = (
            "def f(xs):\n"
            "    g = lambda *a, **kw: a[0].run(kw)\n"
            "    return g(xs).done().final()\n"
        )
        b = (
            "def h(xs):\n"
            "    g = lambda *p, **q: p[0].run(q)\n"
            "    return g(xs).done().final()\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_parameter_reassignment_dedup(self) -> None:
        a = "def f(x):\n    x = x.next()\n    return x.next().next().next()\n"
        b = "def g(y):\n    y = y.next()\n    return y.next().next().next()\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_with_no_as(self) -> None:
        a = (
            "def f(p):\n"
            "    with open(p):\n"
            "        if p.read():\n"
            "            return p.first() + p.first()\n"
        )
        b = (
            "def g(q):\n"
            "    with open(q):\n"
            "        if q.read():\n"
            "            return q.first() + q.first()\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_except_no_as(self) -> None:
        a = (
            "def f(x):\n"
            "    try:\n"
            "        return x.fetch() + x.fetch()\n"
            "    except ValueError:\n"
            "        return x.default()\n"
        )
        b = (
            "def g(y):\n"
            "    try:\n"
            "        return y.fetch() + y.fetch()\n"
            "    except ValueError:\n"
            "        return y.default()\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))

    def test_ellipsis_constant_collapse(self) -> None:
        a = "def f(x):\n    if x is ...:\n        return x.run() + x.run()\n"
        b = "def g(y):\n    if y is ...:\n        return y.run() + y.run()\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))
