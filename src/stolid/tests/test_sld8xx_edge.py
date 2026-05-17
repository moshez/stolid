"""Tests for SLD801 edge cases: filesystem, dominance, reporting."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, has_item, has_length

from ._sld8xx_shared import TAKE_BODY, files, just_801
from .._duplicate_scan import scan_paths
from .code_parser import check_multifile, multifile_codes
from .fakes import InMemoryFileSystem


class TestSubtreeReporting(unittest.TestCase):
    """Reporting of subtree positions and parent-dominates."""

    def test_parent_dominates(self) -> None:
        a = (
            "import itertools\n"
            "def take(seq, n): return list(itertools.islice(seq, n))\n"
        )
        result = just_801(check_multifile({"a.py": a, "b.py": a}))
        assert_that(result, has_length(2))
        node_counts = {int(msg.split("(")[1].split(" ")[0]) for _, _, _, msg in result}
        assert_that(node_counts, equal_to({17}))


class TestEdgeCases(unittest.TestCase):
    """Edge cases: syntax errors, non-.py, gitignore, decorators."""

    def test_syntax_error_continues(self) -> None:
        broken = "def take(seq, n: return list(\n"
        result = check_multifile(
            files(**{"a.py": broken, "b.py": TAKE_BODY, "c.py": TAKE_BODY})
        )
        codes = [msg.split()[0] for _, _, _, msg in result]
        assert_that(codes.count("SLD801"), equal_to(2))

    def test_non_py_files_ignored(self) -> None:
        codes = multifile_codes(
            {
                "f.py": TAKE_BODY,
                "g.py": TAKE_BODY,
                "readme.txt": "this is not python",
                "data.json": "{not valid python}",
            }
        )
        assert_that(codes.count("SLD801"), equal_to(2))

    def test_gitignore_honored(self) -> None:
        codes = multifile_codes(
            {
                ".gitignore": "ignored.py\n",
                "a.py": TAKE_BODY,
                "ignored.py": TAKE_BODY,
            }
        )
        assert_that("SLD801" in codes, equal_to(False))

    def test_decorator_participates_in_hash(self) -> None:
        a = (
            "class A:\n"
            "    @property\n"
            "    def name(self):\n"
            "        return self._name\n"
        )
        b = "class B:\n    def name(self):\n        return self._name\n"
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that("SLD801" in codes, equal_to(False))

    def test_method_self_normalized(self) -> None:
        a = (
            "import itertools\n"
            "class A:\n"
            "    def foo(self, seq, n):\n"
            "        return list(itertools.islice(seq, n))\n"
        )
        b = (
            "import itertools\n"
            "class B:\n"
            "    def bar(self, items, count):\n"
            "        return list(itertools.islice(items, count))\n"
        )
        codes = multifile_codes(files(**{"a.py": a, "b.py": b}))
        assert_that(codes, has_item("SLD801"))


class TestSubtreeDomination(unittest.TestCase):
    """Tests for parent-dominates suppression."""

    def test_non_dominated_groups_reported(self) -> None:
        a = (
            "import itertools\n"
            "def take(seq, n): return list(itertools.islice(seq, n))\n"
        )
        b = (
            "import itertools\n"
            "def take(seq, n): return list(itertools.islice(seq, n))\n"
            "def fetch(items, count):\n"
            "    if items:\n"
            "        for i in items:\n"
            "            print(i.value)\n"
        )
        c = (
            "import itertools\n"
            "def fetch(items, count):\n"
            "    if items:\n"
            "        for i in items:\n"
            "            print(i.value)\n"
        )
        result = just_801(check_multifile(files(**{"a.py": a, "b.py": b, "c.py": c})))
        node_counts = {int(msg.split("(")[1].split(" ")[0]) for _, _, _, msg in result}
        assert_that(len(node_counts) >= 1, equal_to(True))


class TestSameFileTwoClones(unittest.TestCase):
    """A small clone earlier in a file plus a larger one later: both reported."""

    def test_both_groups_reported(self) -> None:
        body = (
            "import itertools\n"
            "def small(seq, n): return list(itertools.islice(seq, n))\n"
            "\n"
            "def big(items, count):\n"
            "    if items:\n"
            "        for it in items:\n"
            "            print(it.value)\n"
            "        return count\n"
        )
        result = just_801(check_multifile({"a.py": body, "b.py": body}))
        node_counts = {int(msg.split("(")[1].split(" ")[0]) for _, _, _, msg in result}
        assert_that(len(node_counts) >= 2, equal_to(True))


class TestPathRoots(unittest.TestCase):
    """Tests for root path handling (trailing slash)."""

    def test_trailing_slash_root(self) -> None:
        take = (
            "import itertools\n"
            "def take(seq, n): return list(itertools.islice(seq, n))\n"
        )
        fs = InMemoryFileSystem(_files={"src/a.py": take, "src/b.py": take})
        result = scan_paths(fs, ["src/"])
        assert_that(len(result.groups), equal_to(1))
