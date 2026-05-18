"""Shared constants and helpers for SLD8xx test modules."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, has_item

from .code_parser import multifile_codes

TAKE_BODY = (
    "import itertools\n"
    "def take(seq, n):\n"
    "    return list(itertools.islice(seq, n))\n"
)


def files(**code: str) -> dict[str, str]:
    """Bundle ``code`` keyword mappings and return them as a ``path -> source`` dict."""
    return dict(code)


def just_801(
    result: list[tuple[str, int, int, str]],
) -> list[tuple[str, int, int, str]]:
    """Return the entries of ``result`` whose message mentions SLD801."""
    return [item for item in result if "SLD801" in item[3]]


def _pair_codes(a: str, b: str) -> list[str]:
    return multifile_codes(files(**{"a.py": a, "b.py": b}))


def assert_pair_positive(
    test_case: unittest.TestCase, cases: list[tuple[str, str, str]]
) -> None:
    """Assert SLD801 is reported for each ``(name, a, b)`` in ``cases``.

    Subtests run on ``test_case``.
    """
    for name, a, b in cases:
        with test_case.subTest(name=name):
            assert_that(_pair_codes(a, b), has_item("SLD801"))


def assert_pair_negative(
    test_case: unittest.TestCase, cases: list[tuple[str, str, str]]
) -> None:
    """Assert SLD801 is NOT reported for each ``(name, a, b)`` in ``cases``.

    Subtests run on ``test_case``.
    """
    for name, a, b in cases:
        with test_case.subTest(name=name):
            assert_that("SLD801" in _pair_codes(a, b), equal_to(False))
