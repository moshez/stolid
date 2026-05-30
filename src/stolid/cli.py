"""Public command-line surface for ``python -m stolid``.

This is the public cross-file seam: ``python -m stolid`` and the test suite
drive the workspace scanners through the helpers here rather than reaching
into the private ``_*_scan`` modules directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from ._contract_scan import scan_paths as contract_scan_paths
from ._duplicate_report import report_lines
from ._duplicate_scan import ScanResult, scan_paths
from ._import_graph_extract import ModuleEdges, extract_graph
from ._import_graph_scan import scan_paths as import_graph_scan_paths
from ._report_line import ReportLine, format_line
from ._workspace_walk import FileSystem


class CommandRunner(Protocol):
    """Runs an external command and returns its exit code."""

    def run(self, argv: Sequence[str]) -> int:
        """Run the command described by ``argv`` and return its exit code."""
        ...


class OutputSink(Protocol):
    """Receives stdout and stderr lines from the duplicate CLI."""

    def stdout(self, line: str) -> None:
        """Emit ``line`` on the standard-output stream."""
        ...

    def stderr(self, line: str) -> None:
        """Emit ``line`` on the standard-error stream."""
        ...


@dataclass(frozen=True, slots=True, kw_only=True)
class Invocation:
    """A stolid run: scan ``paths`` plus ``flake8_options`` forwarded to flake8."""

    paths: Sequence[str]
    flake8_options: Sequence[str]


def _flake8_argv(invocation: Invocation) -> list[str]:
    return ["flake8", *invocation.flake8_options, *invocation.paths]


def _emit_results(
    result: ScanResult, rows: Sequence[ReportLine], sink: OutputSink
) -> int:
    for path in result.syntax_errors:
        sink.stderr(f"{path}: syntax error; skipped")
    for line in rows:
        sink.stdout(format_line(line))
    if rows or result.syntax_errors:
        return 1
    return 0


def duplicate_report(fs: FileSystem, paths: Sequence[str]) -> Sequence[ReportLine]:
    """Return the SLD1xx clone report lines for ``paths`` (read via ``fs``)."""
    return report_lines(fs, scan_paths(fs, list(paths)))


def contract_report(fs: FileSystem, paths: Sequence[str]) -> Sequence[ReportLine]:
    """Return the SLD80x contract report lines for ``paths`` (read via ``fs``)."""
    return contract_scan_paths(fs, list(paths))


def import_graph_report(fs: FileSystem, paths: Sequence[str]) -> Sequence[ReportLine]:
    """Return the SLD83x import-graph report lines for ``paths`` (read via ``fs``)."""
    return import_graph_scan_paths(fs, list(paths))


def import_edges(fs: FileSystem, paths: Sequence[str]) -> Sequence[ModuleEdges]:
    """Return the workspace import-graph edges for ``paths`` (read via ``fs``)."""
    return extract_graph(fs, list(paths))


def run_duplicate_scan(fs: FileSystem, sink: OutputSink, paths: Sequence[str]) -> int:
    """Scan ``paths`` via ``fs``; emit reports to ``sink``; return the exit code."""
    result = scan_paths(fs, list(paths))
    lines = report_lines(fs, result)
    return _emit_results(result, lines, sink)


def _emit_rows(sink: OutputSink, rows: Sequence[ReportLine]) -> int:
    for line in rows:
        sink.stdout(format_line(line))
    return 1 if rows else 0


def run_contract_scan(fs: FileSystem, sink: OutputSink, paths: Sequence[str]) -> int:
    """Scan ``paths`` for SLD80x violations; emit reports to ``sink``; return exit code.

    Uses ``fs`` to read every ``.py`` file under each path.
    """
    return _emit_rows(sink, contract_scan_paths(fs, list(paths)))


def run_import_graph_scan(
    fs: FileSystem, sink: OutputSink, paths: Sequence[str]
) -> int:
    """Scan ``paths`` for SLD83x violations; emit reports to ``sink``; return exit code.

    Uses ``fs`` to read every ``.py`` file under each path and computes
    architectural metrics over the workspace import graph.
    """
    return _emit_rows(sink, import_graph_scan_paths(fs, list(paths)))


def run_stolid(
    runner: CommandRunner,
    fs: FileSystem,
    sink: OutputSink,
    invocation: Invocation,
) -> int:
    """Run flake8 via ``runner`` then the cross-file scanners over ``invocation``.

    Uses ``fs`` to read files and ``sink`` to emit diagnostics. Returns the
    merged exit code (the maximum across flake8, duplicate scan, contract
    scan, and import-graph scan).
    """
    paths = invocation.paths
    flake8_exit = runner.run(_flake8_argv(invocation))
    duplicate_exit = run_duplicate_scan(fs, sink, paths)
    contract_exit = run_contract_scan(fs, sink, paths)
    import_graph_exit = run_import_graph_scan(fs, sink, paths)
    return max(flake8_exit, duplicate_exit, contract_exit, import_graph_exit)


def resolve_paths(argv: Sequence[str]) -> Sequence[str]:
    """Return the list of paths from argv, defaulting to ``["."]``."""
    return argv if argv else ["."]


def parse_argv(argv: Sequence[str]) -> Invocation:
    """Return an :class:`Invocation` parsed from ``argv``.

    Tokens beginning with ``-`` are flake8 options forwarded to the flake8
    subprocess; the rest are scan paths, defaulting to ``["."]``.
    """
    options = [arg for arg in argv if arg.startswith("-")]
    paths = [arg for arg in argv if not arg.startswith("-")]
    return Invocation(paths=resolve_paths(paths), flake8_options=options)
