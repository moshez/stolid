"""Shared test helpers for stolid tests."""

from __future__ import annotations

import ast
import textwrap
import unittest
from typing import Iterable, Mapping, Sequence

from hamcrest import assert_that, contains_string, equal_to, has_item

from .._contract_scan import scan_paths as contract_scan_paths
from .._duplicate_report import report_lines
from .._duplicate_scan import scan_paths
from ..checker import Checker
from .fakes import InMemoryFileSystem


def check_code(code: str, filename: str = "") -> Sequence[tuple[int, int, str]]:
    """Parse ``code`` (under ``filename``) and return ``(line, col, msg)`` errors."""
    dedented = textwrap.dedent(code)
    tree = ast.parse(dedented)
    lines = dedented.splitlines()
    checker = Checker(tree=tree, lines=lines, filename=filename)
    return [(line, col, msg) for line, col, msg, _ in checker.run()]


def get_error_codes(code: str, filename: str = "") -> Sequence[str]:
    """Parse ``code`` (under ``filename``) and return the list of error codes only."""
    errors = check_code(code, filename=filename)
    return [msg.split()[0] for _, _, msg in errors]


def dedent_files(files: Mapping[str, str]) -> Mapping[str, str]:
    """Return ``files`` with each source dedented and the leading newline stripped."""
    return {
        path: textwrap.dedent(source).lstrip("\n") for path, source in files.items()
    }


def check_multifile(
    files: Mapping[str, str], roots: Sequence[str] | None = None
) -> Sequence[tuple[str, int, int, str]]:
    """Run the cross-file scanners over virtual ``files`` under ``roots``.

    Returns a list of report entries from the duplicate and contract scanners.
    """
    sources = dedent_files(files)
    fs = InMemoryFileSystem(_files=sources)
    targets = list(roots) if roots is not None else ["."]
    duplicate_lines = report_lines(fs, scan_paths(fs, targets))
    contract_lines = contract_scan_paths(fs, targets)
    return [
        (item.path, item.line, item.col, item.message)
        for item in duplicate_lines + contract_lines
    ]


def multifile_codes(files: Mapping[str, str]) -> Sequence[str]:
    """Run the duplicate scanner over ``files`` and return just the error codes."""
    return [msg.split()[0] for _, _, _, msg in check_multifile(files)]


def assert_present(
    test_case: unittest.TestCase,
    cases: Iterable[tuple[str, str]],
    sld_code: str,
    *,
    filename: str = "",
) -> None:
    """Assert ``sld_code`` is present for each ``(name, code)`` in ``cases``.

    Each entry is checked under ``filename`` (default ``""``); subtests
    run on ``test_case``.
    """
    for name, code in cases:
        with test_case.subTest(name=name):
            assert_that(get_error_codes(code, filename), has_item(sld_code))


def assert_absent(
    test_case: unittest.TestCase,
    cases: Iterable[tuple[str, str]],
    sld_code: str,
    *,
    filename: str = "",
) -> None:
    """Assert ``sld_code`` is absent for each ``(name, code)`` in ``cases``.

    Each entry is checked under ``filename`` (default ``""``); subtests
    run on ``test_case``.
    """
    for name, code in cases:
        with test_case.subTest(name=name):
            assert_that(sld_code in get_error_codes(code, filename), equal_to(False))


def assert_count(
    test_case: unittest.TestCase,
    cases: Iterable[tuple[str, str, int]],
    sld_code: str,
) -> None:
    """Assert ``sld_code`` appears with the given count for each entry in ``cases``.

    Subtests run on ``test_case``.
    """
    for name, code, count in cases:
        with test_case.subTest(name=name):
            assert_that(get_error_codes(code).count(sld_code), equal_to(count))


def assert_source_absent(source: str, sld_code: str) -> None:
    """Assert ``sld_code`` is not produced when checking ``source``.

    For one-off edge cases that don't fit the table-driven helpers above.
    """
    assert_that(sld_code in get_error_codes(source), equal_to(False))


def _matching_messages(code: str, sld_code: str) -> list[str]:
    return [msg for _, _, msg in check_code(code) if sld_code in msg]


def assert_message_contains(code: str, sld_code: str, expected: str) -> None:
    """Assert the first ``sld_code`` message from ``code`` contains ``expected``."""
    messages = _matching_messages(code, sld_code)
    assert_that(messages[0], contains_string(expected))


def assert_message_contains_all(
    test_case: unittest.TestCase,
    code: str,
    sld_code: str,
    wanted: Iterable[str],
) -> None:
    """Assert the first ``sld_code`` message from ``code`` contains every ``wanted``.

    Each wanted substring runs in its own subtest on ``test_case``.
    """
    messages = _matching_messages(code, sld_code)
    for one in wanted:
        with test_case.subTest(want=one):
            assert_that(messages[0], contains_string(one))
