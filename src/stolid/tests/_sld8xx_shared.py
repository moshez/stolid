# Shared constants and helpers for SLD8xx test modules.

from __future__ import annotations

import unittest
from typing import Mapping, Sequence

from hamcrest import assert_that, equal_to, has_item

from .code_parser import multifile_codes

TAKE_BODY = (
    "import itertools\n"
    "def take(seq, n):\n"
    "    return list(itertools.islice(seq, n))\n"
)


def files(**code: str) -> Mapping[str, str]:
    """Bundle ``code`` keyword mappings and return them as a ``path -> source`` dict.

    Args:
        **code: Keyword arguments mapping path names to source strings.

    Returns:
        A ``path -> source`` dict built from the given keyword arguments.
    """
    return dict(code)


def just_801(
    result: Sequence[tuple[str, int, int, str]],
) -> Sequence[tuple[str, int, int, str]]:
    """Return the entries of ``result`` whose message mentions SLD801.

    Args:
        result: The full sequence of ``(path, line, col, message)`` report entries.

    Returns:
        Only the entries whose message contains ``SLD801``.
    """
    return [item for item in result if "SLD801" in item[3]]


def _pair_codes(first: str, second: str) -> Sequence[str]:
    return multifile_codes(files(**{"a.py": first, "b.py": second}))


def assert_pair_positive(
    test_case: unittest.TestCase, cases: Sequence[tuple[str, str, str]]
) -> None:
    """Assert SLD801 is reported for each ``(name, a, b)`` in ``cases``.

    Subtests run on ``test_case``.

    Args:
        test_case: The test case used to run subtests.
        cases: Triples of ``(name, source_a, source_b)`` to check.
    """
    for name, a, b in cases:
        with test_case.subTest(name=name):
            assert_that(_pair_codes(a, b), has_item("SLD801"))


def assert_pair_negative(
    test_case: unittest.TestCase, cases: Sequence[tuple[str, str, str]]
) -> None:
    """Assert SLD801 is NOT reported for each ``(name, a, b)`` in ``cases``.

    Subtests run on ``test_case``.

    Args:
        test_case: The test case used to run subtests.
        cases: Triples of ``(name, source_a, source_b)`` to check.
    """
    for name, a, b in cases:
        with test_case.subTest(name=name):
            assert_that("SLD801" in _pair_codes(a, b), equal_to(False))
