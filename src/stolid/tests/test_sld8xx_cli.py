"""Tests for SLD801 CLI integration (exit codes, path handling)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, greater_than, has_length

from ._sld8xx_shared import TAKE_BODY
from .._duplicate_cli import Invocation, parse_argv, resolve_paths, run_stolid
from .fakes import CapturedSink, FixedRunner, InMemoryFileSystem


def _run_with(
    files: dict[str, str], exit_code: int
) -> tuple[int, CapturedSink, FixedRunner]:
    fs = InMemoryFileSystem(_files=files)
    runner = FixedRunner(_exit_code=exit_code)
    sink = CapturedSink()
    invocation = Invocation(paths=["."], flake8_options=[])
    result = run_stolid(runner=runner, fs=fs, sink=sink, invocation=invocation)
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


_PARSE_CASES: list[tuple[str, list[str], list[str], list[str]]] = [
    ("no_args_defaults_path", [], ["."], []),
    ("paths_only", ["src", "tests"], ["src", "tests"], []),
    (
        "options_and_path",
        ["--max-line-length=88", "--ignore=E203", "src/"],
        ["src/"],
        ["--max-line-length=88", "--ignore=E203"],
    ),
    (
        "options_only_defaults_path",
        ["--max-line-length=88"],
        ["."],
        ["--max-line-length=88"],
    ),
]


class TestCLIIntegration(unittest.TestCase):
    """CLI integration: exit code merging, path defaults, paths."""

    def test_exit_codes(self) -> None:
        """Verify exit codes."""
        for name, files, flake8_exit, expected in _EXIT_CASES:
            with self.subTest(name=name):
                result, _, _ = _run_with(files, flake8_exit)
                assert_that(result, equal_to(expected))

    def test_resolve_paths(self) -> None:
        """Verify resolve paths."""
        for name, argv, expected in _RESOLVE_CASES:
            with self.subTest(name=name):
                assert_that(resolve_paths(argv), equal_to(expected))

    def test_parse_argv(self) -> None:
        """Verify argv splits into flake8 options and scan paths."""
        for name, argv, paths, options in _PARSE_CASES:
            with self.subTest(name=name):
                invocation = parse_argv(argv)
                assert_that(invocation.paths, equal_to(paths))
                assert_that(invocation.flake8_options, equal_to(options))

    def test_multiple_paths_routed_to_flake8(self) -> None:
        """Verify multiple paths routed to flake8."""
        fs = InMemoryFileSystem(_files={"src/f.py": TAKE_BODY})
        runner = FixedRunner(_exit_code=0)
        sink = CapturedSink()
        invocation = Invocation(paths=["src", "tests"], flake8_options=[])
        run_stolid(runner=runner, fs=fs, sink=sink, invocation=invocation)
        assert_that(runner.calls, has_length(1))
        assert_that(runner.calls[0][1:], equal_to(["src", "tests"]))

    def test_flake8_options_forwarded(self) -> None:
        """Verify flake8 options precede the paths in the flake8 argv."""
        fs = InMemoryFileSystem(_files={"src/f.py": TAKE_BODY})
        runner = FixedRunner(_exit_code=0)
        sink = CapturedSink()
        invocation = Invocation(
            paths=["src"], flake8_options=["--max-line-length=88", "--ignore=E203"]
        )
        run_stolid(runner=runner, fs=fs, sink=sink, invocation=invocation)
        assert_that(
            runner.calls[0],
            equal_to(["flake8", "--max-line-length=88", "--ignore=E203", "src"]),
        )

    def test_syntax_error_produces_stderr(self) -> None:
        """Verify syntax error produces stderr."""
        result, sink, _ = _run_with({"a.py": "def f(\n"}, 0)
        assert_that(len(sink.err), greater_than(0))
        assert_that(result, equal_to(1))

    def test_contract_violation_emitted_on_stdout(self) -> None:
        """Verify SLD80x diagnostics flow through ``sink.stdout`` with exit 1."""
        result, sink, _ = _run_with({"a.py": "def f(xs: list[int]) -> None: ...\n"}, 0)
        assert_that(
            len([line for line in sink.out if "SLD803" in line]), greater_than(0)
        )
        assert_that(result, equal_to(1))
