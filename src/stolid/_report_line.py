# Lightweight container and formatter for one cross-file diagnostic line.
#
# Lives in its own module so cross-file scanners (``_contract_scan``,
# ``_import_graph_scan``) can build report lines without dragging in the
# duplicate detector's chain.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportLine:
    """A single flake8-format diagnostic line.

    Fields ``path``, ``line``, and ``col`` locate the diagnostic; ``message``
    is the human-readable text.

    Attributes:
        path: The file path where the diagnostic was found.
        line: The 1-based line number of the diagnostic.
        col: The 0-based column offset of the diagnostic.
        message: The human-readable diagnostic text.
    """

    path: str
    line: int
    col: int
    message: str


def format_line(line: ReportLine) -> str:
    """Render report ``line`` as ``path:line:col: message`` and return the string.

    Args:
        line: The report line to format.

    Returns:
        A flake8-format string of the form ``path:line:col: message``.
    """
    return f"{line.path}:{line.line}:{line.col}: {line.message}"
