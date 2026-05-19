# Per-line ``# noqa`` parsing for stolid's cross-file scanners.
#
# A bare ``# noqa`` suppresses every code on the line; ``# noqa: CODE,...``
# suppresses only the listed codes (case-insensitive, whitespace tolerant).

from __future__ import annotations

import re

_NOQA_RE = re.compile(r"#\s*noqa(?::\s*([A-Z]+\d+(?:\s*,\s*[A-Z]+\d+)*))?", re.I)


def is_suppressed(line_text: str, code: str) -> bool:
    """Return True iff ``line_text`` carries a ``# noqa`` marker covering ``code``."""
    match = _NOQA_RE.search(line_text)
    if match is None:
        return False
    codes = match.group(1)
    if codes is None:
        return True
    parsed = frozenset(part.strip().upper() for part in codes.split(","))
    return code in parsed
