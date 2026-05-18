"""Formatting and noqa filtering for duplicate-detector reports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from ._constants import SLD801
from ._duplicate_scan import CloneGroup, CloneOccurrence, ScanResult


class SourceReader(Protocol):
    """Reads the textual content of a source file."""

    def read(self, path: str) -> str:  # noqa: E704
        """Return the text contents of the file at ``path``."""
        ...


_NOQA_RE = re.compile(r"#\s*noqa(?::\s*([A-Z]+\d+(?:\s*,\s*[A-Z]+\d+)*))?", re.I)


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportLine:
    """A single flake8-format diagnostic line.

    Fields ``path``, ``line``, and ``col`` locate the diagnostic; ``message``
    is the human-readable text.
    """

    path: str
    line: int
    col: int
    message: str


def format_line(line: ReportLine) -> str:
    """Render report ``line`` as ``path:line:col: message`` and return the string."""
    return f"{line.path}:{line.line}:{line.col}: {line.message}"


def _noqa_codes_on_line(text: str) -> frozenset[str] | None:
    """Parse the noqa marker on ``text``. None if no marker."""
    match = _NOQA_RE.search(text)
    if match is None:
        return None
    codes = match.group(1)
    if codes is None:
        return frozenset()
    return frozenset(code.strip().upper() for code in codes.split(","))


def _is_suppressed(line_text: str, code: str) -> bool:
    parsed = _noqa_codes_on_line(line_text)
    if parsed is None:
        return False
    if not parsed:
        return True
    return code in parsed


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
    if 0 <= index < len(lines):
        return lines[index]
    return ""  # pragma: no cover


def report_lines(reader: SourceReader, result: ScanResult) -> list[ReportLine]:
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
            if _is_suppressed(line_text, "SLD801"):
                continue
            output.append(_occurrence_to_line(occurrence, group))
    return output
