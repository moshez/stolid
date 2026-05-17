"""Shared test helpers for stolid tests."""

from __future__ import annotations

import ast
import textwrap
import unittest

from hamcrest import assert_that, equal_to, has_item

from .._duplicate_report import report_lines
from .._duplicate_scan import scan_paths
from ..checker import Checker
from .fakes import InMemoryFileSystem


def check_code(code: str, filename: str = "") -> list[tuple[int, int, str]]:
    """Parse code and return list of (line, col, message) errors."""
    dedented = textwrap.dedent(code)
    tree = ast.parse(dedented)
    lines = dedented.splitlines()
    checker = Checker(tree=tree, lines=lines, filename=filename)
    return [(line, col, msg) for line, col, msg, _ in checker.run()]


def get_error_codes(code: str) -> list[str]:
    """Parse code and return list of error codes only."""
    errors = check_code(code)
    return [msg.split()[0] for _, _, msg in errors]


def _dedent_files(files: dict[str, str]) -> dict[str, str]:
    return {
        path: textwrap.dedent(source).lstrip("\n") for path, source in files.items()
    }


def check_multifile(
    files: dict[str, str], roots: list[str] | None = None
) -> list[tuple[str, int, int, str]]:
    """Run the duplicate scanner on a virtual multi-file project."""
    sources = _dedent_files(files)
    fs = InMemoryFileSystem(_files=sources)
    result = scan_paths(fs, roots if roots is not None else ["."])
    lines = report_lines(fs, result)
    return [(item.path, item.line, item.col, item.message) for item in lines]


def multifile_codes(files: dict[str, str]) -> list[str]:
    """Run the duplicate scanner and return just the error codes."""
    return [msg.split()[0] for _, _, _, msg in check_multifile(files)]


def assert_present(
    test_case: unittest.TestCase, cases: list[tuple[str, str]], sld_code: str
) -> None:
    """Assert ``sld_code`` is present for each (name, code) case."""
    for name, code in cases:
        with test_case.subTest(name=name):
            assert_that(get_error_codes(code), has_item(sld_code))


def assert_absent(
    test_case: unittest.TestCase, cases: list[tuple[str, str]], sld_code: str
) -> None:
    """Assert ``sld_code`` is absent for each (name, code) case."""
    for name, code in cases:
        with test_case.subTest(name=name):
            assert_that(sld_code in get_error_codes(code), equal_to(False))


def assert_count(
    test_case: unittest.TestCase,
    cases: list[tuple[str, str, int]],
    sld_code: str,
) -> None:
    """Assert ``sld_code`` appears with the given count for each case."""
    for name, code, count in cases:
        with test_case.subTest(name=name):
            assert_that(get_error_codes(code).count(sld_code), equal_to(count))
