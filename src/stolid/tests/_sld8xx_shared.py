"""Shared constants and helpers for SLD8xx test modules."""

from __future__ import annotations

TAKE_BODY = (
    "import itertools\n"
    "def take(seq, n):\n"
    "    return list(itertools.islice(seq, n))\n"
)


def files(**code: str) -> dict[str, str]:
    return dict(code)


def just_801(
    result: list[tuple[str, int, int, str]],
) -> list[tuple[str, int, int, str]]:
    return [item for item in result if "SLD801" in item[3]]
