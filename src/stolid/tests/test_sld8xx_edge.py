"""Tests for SLD801 edge cases: filesystem, dominance, reporting."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, has_length

from ._sld8xx_shared import (
    TAKE_BODY,
    assert_pair_negative,
    assert_pair_positive,
    files,
    just_801,
)
from .._duplicate_scan import scan_paths
from .code_parser import check_multifile, multifile_codes
from .fakes import InMemoryFileSystem

_NEGATIVE_PAIRS: list[tuple[str, str, str]] = [
    (
        "decorator_participates_in_hash",
        "class A:\n    @property\n" "    def name(self):\n        return self._name\n",
        "class B:\n    def name(self):\n        return self._name\n",
    ),
]


_POSITIVE_PAIRS: list[tuple[str, str, str]] = [
    (
        "method_self_normalized",
        "import itertools\n"
        "class A:\n"
        "    def foo(self, seq, n):\n"
        "        return list(itertools.islice(seq, n))\n",
        "import itertools\n"
        "class B:\n"
        "    def bar(self, items, count):\n"
        "        return list(itertools.islice(items, count))\n",
    ),
]


def _node_counts(result: list[tuple[str, int, int, str]]) -> set[int]:
    return {int(msg.split("(")[1].split(" ")[0]) for _, _, _, msg in result}


class TestSubtreeReporting(unittest.TestCase):
    """Reporting of subtree positions and parent-dominates."""

    def test_parent_dominates(self) -> None:
        """Verify parent dominates."""
        a = (
            "import itertools\n"
            "def take(seq, n): return list(itertools.islice(seq, n))\n"
        )
        result = just_801(check_multifile({"a.py": a, "b.py": a}))
        assert_that(result, has_length(2))
        assert_that(_node_counts(result), equal_to({17}))


class TestEdgeCases(unittest.TestCase):
    """Edge cases: syntax errors, non-.py, gitignore, decorators."""

    def test_syntax_error_continues(self) -> None:
        """Verify syntax error continues."""
        broken = "def take(seq, n: return list(\n"
        result = check_multifile(
            files(**{"a.py": broken, "b.py": TAKE_BODY, "c.py": TAKE_BODY})
        )
        codes = [msg.split()[0] for _, _, _, msg in result]
        assert_that(codes.count("SLD801"), equal_to(2))

    def test_non_py_files_ignored(self) -> None:
        """Verify non py files ignored."""
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
        """Verify gitignore honored."""
        codes = multifile_codes(
            {
                ".gitignore": "ignored.py\n",
                "a.py": TAKE_BODY,
                "ignored.py": TAKE_BODY,
            }
        )
        assert_that("SLD801" in codes, equal_to(False))

    def test_pair_negative(self) -> None:
        """Verify pair negative."""
        assert_pair_negative(self, _NEGATIVE_PAIRS)

    def test_pair_positive(self) -> None:
        """Verify pair positive."""
        assert_pair_positive(self, _POSITIVE_PAIRS)


class TestSubtreeDomination(unittest.TestCase):
    """Tests for parent-dominates suppression."""

    def test_non_dominated_groups_reported(self) -> None:
        """Verify non dominated groups reported."""
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
        assert_that(len(_node_counts(result)) >= 1, equal_to(True))


class TestSameFileTwoClones(unittest.TestCase):
    """A small clone earlier in a file plus a larger one later: both reported."""

    def test_both_groups_reported(self) -> None:
        """Verify both groups reported."""
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
        assert_that(len(_node_counts(result)) >= 2, equal_to(True))


class TestPathRoots(unittest.TestCase):
    """Tests for root path handling (trailing slash)."""

    def test_trailing_slash_root(self) -> None:
        """Verify trailing slash root."""
        take = (
            "import itertools\n"
            "def take(seq, n): return list(itertools.islice(seq, n))\n"
        )
        fs = InMemoryFileSystem(_files={"src/a.py": take, "src/b.py": take})
        result = scan_paths(fs, ["src/"])
        assert_that(len(result.groups), equal_to(1))
