# Reserved names that global definitions must not shadow.

from __future__ import annotations

import builtins
import sys
import typing
from typing import AbstractSet


def _public_names(module: object) -> frozenset[str]:
    return frozenset(name for name in dir(module) if not name.startswith("_"))


BUILTIN_NAMES: AbstractSet[str] = _public_names(builtins)
TYPING_NAMES: AbstractSet[str] = _public_names(typing)
STDLIB_NAMES: AbstractSet[str] = frozenset(sys.stdlib_module_names)


def reserved_name_source(name: str) -> str | None:
    """Return a human-readable reference for a reserved name, else None.

    Args:
        name: The identifier to look up in builtins, typing, and stdlib.

    Returns:
        A human-readable string identifying the source, or None if not reserved.
    """
    if name in BUILTIN_NAMES:
        return f"builtin '{name}'"
    if name in TYPING_NAMES:
        return f"typing.{name}"
    if name in STDLIB_NAMES:
        return f"stdlib module '{name}'"
    return None
