# Shared fixtures and helpers for SLD80x test modules.

from __future__ import annotations

import unittest
from typing import Iterable, Mapping, Sequence

from hamcrest import assert_that, empty, has_item

from .code_parser import multifile_codes

CONCRETE_DEF = (
    "from dataclasses import dataclass\n"
    "@dataclass(frozen=True, slots=True, kw_only=True)\n"
    "class Backend:\n"
    "    name: str\n"
)

PROTOCOL_DEF = (
    "from typing import Protocol\n"
    "class Backend(Protocol):\n"
    "    def fetch(self, key: str) -> bytes: ...\n"
)


def matching_prefix(found: Sequence[str], prefix: str) -> Sequence[str]:
    """Return the entries of ``found`` that start with ``prefix``."""
    return [entry for entry in found if entry.startswith(prefix)]


def assert_present(
    test: unittest.TestCase,
    cases: Iterable[tuple[str, Mapping[str, str]]],
    sld_code: str,
) -> None:
    """Assert ``sld_code`` is reported for each ``(name, files)`` in ``cases``.

    Subtests run on ``test``.
    """
    for name, files in cases:
        with test.subTest(name=name):
            assert_that(multifile_codes(files), has_item(sld_code))


def assert_absent(
    test: unittest.TestCase,
    cases: Iterable[tuple[str, Mapping[str, str]]],
    sld_code: str,
) -> None:
    """Assert ``sld_code`` is not reported for each ``(name, files)`` in ``cases``.

    Subtests run on ``test``.
    """
    for name, files in cases:
        with test.subTest(name=name):
            assert_that(matching_prefix(multifile_codes(files), sld_code), empty())
