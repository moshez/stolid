"""Tests for SLD801 scope and binding features."""

from __future__ import annotations

import unittest

from ._sld8xx_shared import assert_pair_positive

_SCOPE_POSITIVE: list[tuple[str, str, str]] = [
    (
        "for_target_binding",
        "def f(xs):\n    for item in xs:\n"
        "        if item > 0:\n            print(item, item, item)\n",
        "def g(items):\n    for value in items:\n"
        "        if value > 0:\n            print(value, value, value)\n",
    ),
    (
        "with_as_binding",
        "def f(p):\n    with open(p) as fh:\n"
        "        if fh.read():\n            return fh.readline()\n",
        "def g(q):\n    with open(q) as handle:\n"
        "        if handle.read():\n            return handle.readline()\n",
    ),
    (
        "except_as_binding",
        "def f(x):\n    try:\n        return x.do()\n"
        "    except Exception as exc:\n        return exc.args + exc.args\n",
        "def g(y):\n    try:\n        return y.do()\n"
        "    except Exception as err:\n        return err.args + err.args\n",
    ),
    (
        "annassign_binding",
        "def f(x):\n    y: int = x.compute()\n    return y + y + y\n",
        "def g(z):\n    out: int = z.compute()\n    return out + out + out\n",
    ),
    (
        "walrus_binding",
        "def f(xs):\n" "    if (n := xs.size()) > 0:\n        return n + n + n\n",
        "def g(items):\n"
        "    if (count := items.size()) > 0:\n"
        "        return count + count + count\n",
    ),
    (
        "starred_target_binding",
        "def f(xs):\n    first, *rest = xs.split()\n" "    return rest + rest + rest\n",
        "def g(items):\n    head, *tail = items.split()\n"
        "    return tail + tail + tail\n",
    ),
    (
        "vararg_kwarg_binding",
        "def f(*args, **kw):\n    if args:\n" "        return kw.values() + args\n",
        "def g(*xs, **ys):\n    if xs:\n        return ys.values() + xs\n",
    ),
    (
        "lambda_normalizes",
        "def f(xs):\n"
        "    return sorted(xs, key=lambda item: item.score + item.bonus)\n",
        "def g(items):\n" "    return sorted(items, key=lambda x: x.score + x.bonus)\n",
    ),
    (
        "lambda_star_args",
        "def f(xs):\n"
        "    g = lambda *a, **kw: a[0].run(kw)\n"
        "    return g(xs).done().final()\n",
        "def h(xs):\n"
        "    g = lambda *p, **q: p[0].run(q)\n"
        "    return g(xs).done().final()\n",
    ),
    (
        "parameter_reassignment_dedup",
        "def f(x):\n    x = x.next()\n    return x.next().next().next()\n",
        "def g(y):\n    y = y.next()\n    return y.next().next().next()\n",
    ),
    (
        "with_no_as",
        "def f(p):\n    with open(p):\n"
        "        if p.read():\n            return p.first() + p.first()\n",
        "def g(q):\n    with open(q):\n"
        "        if q.read():\n            return q.first() + q.first()\n",
    ),
    (
        "except_no_as",
        "def f(x):\n    try:\n        return x.fetch() + x.fetch()\n"
        "    except ValueError:\n        return x.default()\n",
        "def g(y):\n    try:\n        return y.fetch() + y.fetch()\n"
        "    except ValueError:\n        return y.default()\n",
    ),
    (
        "ellipsis_constant_collapse",
        "def f(x):\n    if x is ...:\n        return x.run() + x.run()\n",
        "def g(y):\n    if y is ...:\n        return y.run() + y.run()\n",
    ),
]


class TestScopeFeatures(unittest.TestCase):
    """Tests for less-common scope and binding features."""

    def test_pair_clones_reported(self) -> None:
        """Verify pair clones reported."""
        assert_pair_positive(self, _SCOPE_POSITIVE)
