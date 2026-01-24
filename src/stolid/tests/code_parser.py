"""Shared test helpers for stolid tests."""

from __future__ import annotations

import ast
import textwrap

from ..checker import Checker


def check_code(code: str, filename: str = "") -> list[tuple[int, int, str]]:
    """Parse code and return list of (line, col, message) errors."""
    dedented = textwrap.dedent(code)
    tree = ast.parse(dedented)
    lines = dedented.splitlines()
    checker = Checker(tree=tree, lines=lines, filename=filename)
    return [(line, col, msg) for line, col, msg, _ in checker.run()]


def get_error_codes(code: str) -> list[str]:
    """Parse code and return list of error codes only."""
    errors = check_code(code)
    return [msg.split()[0] for _, _, msg in errors]
