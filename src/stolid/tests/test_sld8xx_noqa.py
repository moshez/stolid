"""Tests for SLD801 noqa handling."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, equal_to, has_item

from ._sld8xx_shared import files, just_801
from .code_parser import check_multifile


class TestNoqa(unittest.TestCase):
    """noqa handling."""

    def test_noqa_sld801_suppresses_one(self) -> None:
        a = (
            "import itertools\n"
            "def take(seq, n):  # noqa: SLD801\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        b = (
            "import itertools\n"
            "def take(seq, n):\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        c = (
            "import itertools\n"
            "def take(seq, n):\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        result = just_801(check_multifile(files(**{"a.py": a, "b.py": b, "c.py": c})))
        paths = [path for path, _, _, _ in result]
        assert_that("a.py" in paths, equal_to(False))
        assert_that(paths.count("b.py"), equal_to(1))
        assert_that(paths.count("c.py"), equal_to(1))

    def test_noqa_still_in_also_at(self) -> None:
        a = (
            "import itertools\n"
            "def take(seq, n):  # noqa: SLD801\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        b = (
            "import itertools\n"
            "def take(seq, n):\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        c = (
            "import itertools\n"
            "def take(seq, n):\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        result = just_801(check_multifile(files(**{"a.py": a, "b.py": b, "c.py": c})))
        for _, _, _, msg in result:
            assert_that(msg, contains_string("a.py:2"))

    def test_bare_noqa_suppresses(self) -> None:
        a = (
            "import itertools\n"
            "def take(seq, n):  # noqa\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        b = (
            "import itertools\n"
            "def take(seq, n):\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        result = just_801(check_multifile(files(**{"a.py": a, "b.py": b})))
        paths = [path for path, _, _, _ in result]
        assert_that("a.py" in paths, equal_to(False))
        assert_that(paths, has_item("b.py"))

    def test_multi_code_noqa_includes_sld801(self) -> None:
        a = (
            "import itertools\n"
            "def take(seq, n):  # noqa: SLD301,SLD801\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        b = (
            "import itertools\n"
            "def take(seq, n):\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        result = just_801(check_multifile(files(**{"a.py": a, "b.py": b})))
        paths = [path for path, _, _, _ in result]
        assert_that("a.py" in paths, equal_to(False))
        assert_that(paths, has_item("b.py"))

    def test_wrong_code_noqa_does_not_suppress(self) -> None:
        a = (
            "import itertools\n"
            "def take(seq, n):  # noqa: SLD802\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        b = (
            "import itertools\n"
            "def take(seq, n):\n"
            "    return list(itertools.islice(seq, n))\n"
        )
        result = just_801(check_multifile(files(**{"a.py": a, "b.py": b})))
        paths = [path for path, _, _, _ in result]
        assert_that(paths, has_item("a.py"))
        assert_that(paths, has_item("b.py"))
