# Formatting and noqa filtering for duplicate-detector reports.

from __future__ import annotations

from typing import Protocol, Sequence

from ._duplicate_scan import CloneGroup, CloneOccurrence, ScanResult
from ._noqa import is_suppressed
from ._report_line import ReportLine, format_line

__all__ = ["ReportLine", "SourceReader", "format_line", "report_lines"]

SLD801 = "SLD801 duplicated structure ({} nodes); also at {}"


class SourceReader(Protocol):
    """Reads the textual content of a source file."""

    def read(self, path: str) -> str:
        """Return the text contents of the file at ``path``."""
        ...


def _format_others(occurrence: CloneOccurrence, group: CloneGroup) -> str:
    others = [other for other in group.occurrences if other is not occurrence]
    return ", ".join(f"{other.location.path}:{other.location.line}" for other in others)


def _occurrence_to_line(occurrence: CloneOccurrence, group: CloneGroup) -> ReportLine:
    return ReportLine(
        path=occurrence.location.path,
        line=occurrence.location.line,
        col=occurrence.location.col,
        message=SLD801.format(occurrence.node_count, _format_others(occurrence, group)),
    )


def _line_text(source: str, line_number: int) -> str:
    lines = source.splitlines()
    index = line_number - 1
    assert 0 <= index < len(lines)  # line_number comes from this source's own AST
    return lines[index]


def report_lines(reader: SourceReader, result: ScanResult) -> Sequence[ReportLine]:
    """Format ``result`` (using ``reader`` to load source lines) into report lines.

    Returns flake8-style diagnostic lines and honors per-line ``noqa`` markers.
    """
    sources: dict[str, str] = {}
    output: list[ReportLine] = []
    for group in result.groups:
        for occurrence in group.occurrences:
            path = occurrence.location.path
            if path not in sources:
                sources[path] = reader.read(path)
            line_text = _line_text(sources[path], occurrence.location.line)
            if is_suppressed(line_text, "SLD801"):
                continue
            output.append(_occurrence_to_line(occurrence, group))
    return output
