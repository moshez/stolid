"""Tests for SLD801 CLI integration (exit codes, path handling)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, empty, equal_to, has_length, is_not

from ._sld8xx_shared import TAKE_BODY
from .._duplicate_cli import resolve_paths, run_stolid
from .fakes import CapturedSink, FixedRunner, InMemoryFileSystem


def _run_with(
    files: dict[str, str], exit_code: int
) -> tuple[int, CapturedSink, FixedRunner]:
    fs = InMemoryFileSystem(_files=files)
    runner = FixedRunner(_exit_code=exit_code)
    sink = CapturedSink()
    result = run_stolid(runner=runner, fs=fs, sink=sink, paths=["."])
    return result, sink, runner


_EXIT_CASES: list[tuple[str, dict[str, str], int, int]] = [
    (
        "exit_code_merge_flake8_wins",
        {f"f{i}.py": TAKE_BODY for i in range(2)},
        2,
        2,
    ),
    (
        "duplicate_exit_when_no_flake8_failure",
        {f"f{i}.py": TAKE_BODY for i in range(2)},
        0,
        1,
    ),
    (
        "clean_exit_zero",
        {"f.py": "x = 1\n"},
        0,
        0,
    ),
]


_RESOLVE_CASES: list[tuple[str, list[str], list[str]]] = [
    ("default_paths_empty", [], ["."]),
    ("explicit_paths", ["src", "tests"], ["src", "tests"]),
]


class TestCLIIntegration(unittest.TestCase):
    """CLI integration: exit code merging, path defaults, paths."""

    def test_exit_codes(self) -> None:
        for name, files, flake8_exit, expected in _EXIT_CASES:
            with self.subTest(name=name):
                result, _, _ = _run_with(files, flake8_exit)
                assert_that(result, equal_to(expected))

    def test_resolve_paths(self) -> None:
        for name, argv, expected in _RESOLVE_CASES:
            with self.subTest(name=name):
                assert_that(resolve_paths(argv), equal_to(expected))

    def test_multiple_paths_routed_to_flake8(self) -> None:
        fs = InMemoryFileSystem(_files={"src/f.py": TAKE_BODY})
        runner = FixedRunner(_exit_code=0)
        sink = CapturedSink()
        run_stolid(runner=runner, fs=fs, sink=sink, paths=["src", "tests"])
        assert_that(runner.calls, has_length(1))
        assert_that(runner.calls[0][1:], equal_to(["src", "tests"]))

    def test_syntax_error_produces_stderr(self) -> None:
        result, sink, _ = _run_with({"a.py": "def f(\n"}, 0)
        assert_that(sink.err, is_not(empty()))
        assert_that(result, equal_to(1))
