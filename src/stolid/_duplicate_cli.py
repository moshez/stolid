# Command-line entry point for ``python -m stolid``.

from __future__ import annotations

from typing import Protocol

from ._duplicate_report import ReportLine, format_line, report_lines
from ._duplicate_scan import FileSystem, ScanResult, scan_paths


class CommandRunner(Protocol):
    """Runs an external command and returns its exit code."""

    def run(self, argv: list[str]) -> int:  # noqa: E704
        """Run the command described by ``argv`` and return its exit code."""
        ...


class OutputSink(Protocol):
    """Receives stdout and stderr lines from the duplicate CLI."""

    def stdout(self, line: str) -> None:  # noqa: E704
        """Emit ``line`` on the standard-output stream."""
        ...

    def stderr(self, line: str) -> None:  # noqa: E704
        """Emit ``line`` on the standard-error stream."""
        ...


def _flake8_argv(paths: list[str]) -> list[str]:
    return ["flake8", *paths]


def _emit_results(result: ScanResult, lines: list[ReportLine], sink: OutputSink) -> int:
    for path in result.syntax_errors:
        sink.stderr(f"{path}: syntax error; skipped")
    for line in lines:
        sink.stdout(format_line(line))
    if lines or result.syntax_errors:
        return 1
    return 0


def run_duplicate_scan(fs: FileSystem, sink: OutputSink, paths: list[str]) -> int:
    """Scan ``paths`` via ``fs``; emit reports to ``sink``; return the exit code."""
    result = scan_paths(fs, paths)
    lines = report_lines(fs, result)
    return _emit_results(result, lines, sink)


def run_stolid(
    runner: CommandRunner,
    fs: FileSystem,
    sink: OutputSink,
    paths: list[str],
) -> int:
    """Run flake8 via ``runner`` then the duplicate scanner over ``paths``.

    Uses ``fs`` to read files and ``sink`` to emit diagnostics. Returns the
    merged exit code (the maximum of the two stages).
    """
    flake8_exit = runner.run(_flake8_argv(paths))
    duplicate_exit = run_duplicate_scan(fs, sink, paths)
    return max(flake8_exit, duplicate_exit)


def resolve_paths(argv: list[str]) -> list[str]:
    """Return the list of paths from argv, defaulting to ``["."]``."""
    return argv if argv else ["."]
