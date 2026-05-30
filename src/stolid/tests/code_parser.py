"""Shared test helpers for stolid tests."""

from __future__ import annotations

import ast
import textwrap
import unittest
from importlib.metadata import entry_points
from typing import Iterable, Iterator, Mapping, Protocol, Sequence

from hamcrest import assert_that, contains_string, equal_to, has_item

from ..cli import contract_report, duplicate_report
from .fakes import InMemoryFileSystem


class _CheckerRun(Protocol):
    # A constructed per-module stolid checker.

    def run(self) -> Iterator[tuple[int, int, str, type]]:
        """Yield ``(line, col, message, type)`` tuples for the module.

        Returns:
            An iterator of ``(line, col, message, type)`` diagnostic tuples.
        """
        ...


class _CheckerFactory(Protocol):
    # Constructs a checker from one parsed module's tree, lines, and filename.

    def __call__(
        self, *, tree: ast.Module, lines: Sequence[str], filename: str
    ) -> _CheckerRun:
        """Return a checker for the given module.

        Args:
            tree: The parsed AST of the module.
            lines: The raw source lines of the module.
            filename: The filename associated with the module.

        Returns:
            A checker instance ready to run against the module.
        """
        ...


def _load_checker() -> _CheckerFactory:
    # Discover the stolid plugin the way flake8 does: by its registered
    # ``flake8.extension`` entry-point name. Tests drive this class rather
    # than importing ``stolid.checker`` directly.
    extensions = entry_points(group="flake8.extension")
    (endpoint,) = [ep for ep in extensions if ep.name == "SLD"]
    factory: _CheckerFactory = endpoint.load()
    return factory


_CHECKER = _load_checker()


def check_code(code: str, filename: str = "") -> Sequence[tuple[int, int, str]]:
    """Parse ``code`` (under ``filename``) and return ``(line, col, msg)`` errors.

    Args:
        code: The Python source code to check.
        filename: The filename to associate with the module.

    Returns:
        A sequence of ``(line, col, msg)`` diagnostic tuples.
    """
    dedented = textwrap.dedent(code)
    tree = ast.parse(dedented)
    lines = dedented.splitlines()
    checker = _CHECKER(tree=tree, lines=lines, filename=filename)
    return [(line, col, msg) for line, col, msg, _ in checker.run()]


def get_error_codes(code: str, filename: str = "") -> Sequence[str]:
    """Parse ``code`` (under ``filename``) and return the list of error codes only.

    Args:
        code: The Python source code to check.
        filename: The filename to associate with the module.

    Returns:
        A sequence of diagnostic code tokens (e.g. ``SLD601``).
    """
    errors = check_code(code, filename=filename)
    return [msg.split()[0] for _, _, msg in errors]


def dedent_files(files: Mapping[str, str]) -> Mapping[str, str]:
    """Return ``files`` with each source dedented and the leading newline stripped.

    Args:
        files: A ``path -> source`` mapping of raw source strings.

    Returns:
        A new mapping with each source dedented and its leading newline removed.
    """
    return {
        path: textwrap.dedent(source).lstrip("\n") for path, source in files.items()
    }


def check_multifile(
    files: Mapping[str, str], roots: Sequence[str] | None = None
) -> Sequence[tuple[str, int, int, str]]:
    """Run the cross-file scanners over virtual ``files`` under ``roots``.

    Returns a list of report entries from the duplicate and contract scanners.

    Args:
        files: A ``path -> source`` mapping of virtual source files.
        roots: The root directories to scan; defaults to ``["."]``.

    Returns:
        A sequence of ``(path, line, col, message)`` report entries.
    """
    sources = dedent_files(files)
    fs = InMemoryFileSystem(_files=sources)
    targets = list(roots) if roots is not None else ["."]
    lines = list(duplicate_report(fs, targets)) + list(contract_report(fs, targets))
    return [(item.path, item.line, item.col, item.message) for item in lines]


def multifile_codes(files: Mapping[str, str]) -> Sequence[str]:
    """Run the duplicate scanner over ``files`` and return just the error codes.

    Args:
        files: A ``path -> source`` mapping of virtual source files.

    Returns:
        A sequence of diagnostic code tokens from the cross-file scan.
    """
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

    Args:
        test_case: The test case used to run subtests.
        cases: Pairs of ``(name, source)`` to check.
        sld_code: The diagnostic code expected in each result.
        filename: The filename passed to the checker for each source snippet.
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

    Args:
        test_case: The test case used to run subtests.
        cases: Pairs of ``(name, source)`` to check.
        sld_code: The diagnostic code expected to be absent from each result.
        filename: The filename passed to the checker for each source snippet.
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

    Args:
        test_case: The test case used to run subtests.
        cases: Triples of ``(name, source, expected_count)`` to check.
        sld_code: The diagnostic code to count in each result.
    """
    for name, code, count in cases:
        with test_case.subTest(name=name):
            assert_that(get_error_codes(code).count(sld_code), equal_to(count))


def assert_source_absent(source: str, sld_code: str) -> None:
    """Assert ``sld_code`` is not produced when checking ``source``.

    For one-off edge cases that don't fit the table-driven helpers above.

    Args:
        source: The Python source code to check.
        sld_code: The diagnostic code expected to be absent.
    """
    assert_that(sld_code in get_error_codes(source), equal_to(False))


def _matching_messages(code: str, sld_code: str) -> list[str]:
    return [msg for _, _, msg in check_code(code) if sld_code in msg]


def assert_message_contains(code: str, sld_code: str, expected: str) -> None:
    """Assert the first ``sld_code`` message from ``code`` contains ``expected``.

    Args:
        code: The Python source code to check.
        sld_code: The diagnostic code to filter messages by.
        expected: The substring the first matching message must contain.
    """
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

    Args:
        test_case: The test case used to run subtests.
        code: The Python source code to check.
        sld_code: The diagnostic code to filter messages by.
        wanted: The substrings that must all appear in the first matching message.
    """
    messages = _matching_messages(code, sld_code)
    for one in wanted:
        with test_case.subTest(want=one):
            assert_that(messages[0], contains_string(one))
