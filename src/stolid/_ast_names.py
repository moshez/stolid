# Forbidden-word name checks (SLD701) and the shared bad-name error type.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import AbstractSet, Iterator, Protocol, Sequence, TypeVar

BAD_NAME_WORDS: AbstractSet[str] = frozenset(
    {"help", "helper", "helpers", "util", "utils", "manage", "manager", "managers"}
)

# Pattern to split identifiers into words:
# - Split on underscores
# - Split on CamelCase boundaries (lowercase followed by uppercase)
_WORD_SPLIT_PATTERN = re.compile(r"_|(?<=[a-z])(?=[A-Z])")


def split_identifier_into_words(name: str) -> Sequence[str]:
    """Split identifier ``name`` into its words and return them.

    Splits on underscores and CamelCase boundaries. For example,
    ``"DiskUtil"`` -> ``["Disk", "Util"]``, ``"disk_util"`` ->
    ``["disk", "util"]``, ``"Futile"`` -> ``["Futile"]``, and
    ``"MyHelperClass"`` -> ``["My", "Helper", "Class"]``.

    Args:
        name: The identifier to split into words.

    Returns:
        The words of ``name``, in order, with empty parts dropped.
    """
    return [word for word in _WORD_SPLIT_PATTERN.split(name) if word]


def find_bad_name_word(name: str) -> str | None:
    """Return the first forbidden word in identifier ``name``, or ``None`` if absent.

    Args:
        name: The identifier to inspect for forbidden words.

    Returns:
        The first forbidden word found (lower-cased), or ``None`` if none.
    """
    parts = split_identifier_into_words(name)
    for word in parts:
        if word.lower() in BAD_NAME_WORDS:
            return word.lower()
    return None


SLD701 = "SLD701 Name '{}' contains forbidden word '{}' (use a more specific name)"


@dataclass(frozen=True, slots=True, kw_only=True)
class BadNameError:
    """A bad-name violation.

    ``lineno`` and ``col_offset`` locate the offending name; ``message``
    is the formatted SLD701 diagnostic.

    Attributes:
        lineno: The line number of the offending name.
        col_offset: The column offset of the offending name.
        message: The formatted SLD701 diagnostic message.
    """

    lineno: int
    col_offset: int
    message: str


def bad_name_errors(name: str, lineno: int, col_offset: int) -> Iterator[BadNameError]:
    """Yield SLD701 if ``name`` contains a forbidden word.

    ``lineno`` and ``col_offset`` locate the offending name.

    Args:
        name: The identifier to inspect.
        lineno: The line number of the offending name.
        col_offset: The column offset of the offending name.

    Yields:
        A :class:`BadNameError` when ``name`` contains a forbidden word.
    """
    bad_word = find_bad_name_word(name)
    if bad_word is not None:
        yield BadNameError(
            lineno=lineno, col_offset=col_offset, message=SLD701.format(name, bad_word)
        )


_E = TypeVar("_E", covariant=True)


class _BadNameErrorFactory(Protocol[_E]):
    def __call__(  # noqa: E704
        self, *, lineno: int, col_offset: int, message: str
    ) -> _E: ...


def bad_name_errors_as(
    name: str, lineno: int, col_offset: int, factory: _BadNameErrorFactory[_E]
) -> Iterator[_E]:
    """Yield ``factory(...)``-wrapped SLD701 errors for ``name``.

    ``factory`` is called with ``lineno``, ``col_offset``, and ``message``
    keyword arguments; use it to lift the shared ``BadNameError`` into
    each module's local error dataclass.

    Args:
        name: The identifier to inspect.
        lineno: The line number of the offending name.
        col_offset: The column offset of the offending name.
        factory: Callable building each module's local error dataclass.

    Yields:
        Each SLD701 error built by ``factory`` for ``name``.
    """
    for err in bad_name_errors(name, lineno, col_offset):
        yield factory(lineno=err.lineno, col_offset=err.col_offset, message=err.message)
