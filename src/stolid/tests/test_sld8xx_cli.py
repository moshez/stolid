"""Tests for SLD801 CLI integration (exit codes, path handling)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, empty, equal_to, has_length, is_not

from ._sld8xx_shared import TAKE_BODY
from .._duplicate_cli import resolve_paths, run_stolid
from .fakes import CapturedSink, FixedRunner, InMemoryFileSystem


class TestCLIIntegration(unittest.TestCase):
    """CLI integration: exit code merging, path defaults, paths."""

    def test_exit_code_merge(self) -> None:
        fs = InMemoryFileSystem(_files={f"f{i}.py": TAKE_BODY for i in range(2)})
        runner = FixedRunner(_exit_code=2)
        sink = CapturedSink()
        result = run_stolid(runner=runner, fs=fs, sink=sink, paths=["."])
        assert_that(result, equal_to(2))

    def test_duplicate_exit_when_no_flake8_failure(self) -> None:
        fs = InMemoryFileSystem(_files={f"f{i}.py": TAKE_BODY for i in range(2)})
        runner = FixedRunner(_exit_code=0)
        sink = CapturedSink()
        result = run_stolid(runner=runner, fs=fs, sink=sink, paths=["."])
        assert_that(result, equal_to(1))

    def test_clean_exit_zero(self) -> None:
        fs = InMemoryFileSystem(_files={"f.py": "x = 1\n"})
        runner = FixedRunner(_exit_code=0)
        sink = CapturedSink()
        result = run_stolid(runner=runner, fs=fs, sink=sink, paths=["."])
        assert_that(result, equal_to(0))

    def test_default_paths(self) -> None:
        assert_that(resolve_paths([]), equal_to(["."]))

    def test_explicit_paths(self) -> None:
        assert_that(resolve_paths(["src", "tests"]), equal_to(["src", "tests"]))

    def test_multiple_paths_routed_to_flake8(self) -> None:
        fs = InMemoryFileSystem(_files={"src/f.py": TAKE_BODY})
        runner = FixedRunner(_exit_code=0)
        sink = CapturedSink()
        run_stolid(runner=runner, fs=fs, sink=sink, paths=["src", "tests"])
        assert_that(runner._calls, has_length(1))
        assert_that(runner._calls[0][1:], equal_to(["src", "tests"]))

    def test_syntax_error_produces_stderr(self) -> None:
        fs = InMemoryFileSystem(_files={"a.py": "def f(\n"})
        runner = FixedRunner(_exit_code=0)
        sink = CapturedSink()
        result = run_stolid(runner=runner, fs=fs, sink=sink, paths=["."])
        assert_that(sink._err, is_not(empty()))
        assert_that(result, equal_to(1))
