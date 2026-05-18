"""Tests for SLD801 noqa handling."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, equal_to, has_item

from ._sld8xx_shared import files, just_801
from .code_parser import check_multifile

_TAKE_PLAIN = (
    "import itertools\n"
    "def take(seq, n):\n"
    "    return list(itertools.islice(seq, n))\n"
)


def _take_with_noqa(marker: str) -> str:
    return (
        "import itertools\n"
        f"def take(seq, n):  # {marker}\n"
        "    return list(itertools.islice(seq, n))\n"
    )


_SUPPRESSING_MARKERS: list[tuple[str, str]] = [
    ("sld801_only", "noqa: SLD801"),
    ("bare_noqa", "noqa"),
    ("multi_code_includes_sld801", "noqa: SLD301,SLD801"),
]


class TestNoqa(unittest.TestCase):
    """noqa handling."""

    def test_noqa_suppresses(self) -> None:
        """Verify noqa suppresses."""
        for name, marker in _SUPPRESSING_MARKERS:
            with self.subTest(name=name):
                result = just_801(
                    check_multifile(
                        files(**{"a.py": _take_with_noqa(marker), "b.py": _TAKE_PLAIN})
                    )
                )
                paths = [path for path, _, _, _ in result]
                assert_that("a.py" in paths, equal_to(False))
                assert_that(paths, has_item("b.py"))

    def test_wrong_code_noqa_does_not_suppress(self) -> None:
        """Verify wrong code noqa does not suppress."""
        a = _take_with_noqa("noqa: SLD802")
        result = just_801(check_multifile(files(**{"a.py": a, "b.py": _TAKE_PLAIN})))
        paths = [path for path, _, _, _ in result]
        for expected in ("a.py", "b.py"):
            with self.subTest(path=expected):
                assert_that(paths, has_item(expected))

    def test_noqa_sld801_suppresses_one_of_three(self) -> None:
        """Verify noqa sld801 suppresses one of three."""
        a = _take_with_noqa("noqa: SLD801")
        result = just_801(
            check_multifile(
                files(**{"a.py": a, "b.py": _TAKE_PLAIN, "c.py": _TAKE_PLAIN})
            )
        )
        paths = [path for path, _, _, _ in result]
        assert_that("a.py" in paths, equal_to(False))
        for path in ("b.py", "c.py"):
            with self.subTest(path=path):
                assert_that(paths.count(path), equal_to(1))

    def test_noqa_still_in_also_at(self) -> None:
        """Verify noqa still in also at."""
        a = _take_with_noqa("noqa: SLD801")
        result = just_801(
            check_multifile(
                files(**{"a.py": a, "b.py": _TAKE_PLAIN, "c.py": _TAKE_PLAIN})
            )
        )
        for _, _, _, msg in result:
            with self.subTest(msg=msg):
                assert_that(msg, contains_string("a.py:2"))
