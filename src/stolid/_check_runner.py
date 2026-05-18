# Wire per-source check outputs into a uniform error stream for Checker.

from __future__ import annotations

import ast
import io
import itertools
import tokenize
from dataclasses import dataclass
from typing import Iterable, Iterator, Protocol

from ._ast_inspection import FunctionComplexity, collect_imports
from ._constants import (
    MAX_FUNCTION_LINES,
    SLD204,
    SLD601,
    SLD901,
    SLD902,
    SLD903,
    SLD904,
    SLD905,
)
from ._import_placement_check import check_import_placement
from ._private_access_check import PrivacyKind, check_private_access


class ErrorLike(Protocol):
    """Structural type for any error a check source yields."""

    @property
    def lineno(self) -> int:  # noqa: E704
        """Return the line number where the error was detected."""  # pragma: no cover

    @property
    def col_offset(self) -> int:  # noqa: E704
        """Return the column offset of the error on its line."""  # pragma: no cover

    @property
    def message(self) -> str:  # noqa: E704
        """Return the formatted SLDxxx diagnostic message."""  # pragma: no cover


@dataclass(frozen=True, slots=True, kw_only=True)
class AdaptedError:
    """An error in the shape consumed by Checker.run.

    ``lineno``/``col_offset`` locate the offending source position;
    ``message`` is the fully-formatted diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckContext:
    """Shared per-module state passed to per-node checks.

    ``patch_names``, ``abstractmethod_names``, and ``cast_names`` are the
    local names bound to ``patch``, ``abstractmethod``, and
    ``typing.cast`` via the module's imports. ``lines`` is the raw source
    of the module under check; ``bracket_depths`` maps each line number
    to the deepest bracket stack opened on that line.
    """

    patch_names: set[str]
    abstractmethod_names: set[str]
    cast_names: set[str]
    lines: list[str]
    bracket_depths: dict[int, int]


_PRIVACY_CODES: dict[PrivacyKind, str] = {
    PrivacyKind.EXTERNAL_PRIVATE_READ: SLD901,
    PrivacyKind.EXTERNAL_PRIVATE_WRITE: SLD902,
    PrivacyKind.ABSOLUTE_PRIVATE_IMPORT: SLD903,
    PrivacyKind.PRIVATE_SUBMODULE_IMPORT: SLD904,
    PrivacyKind.MODULE_PRIVATE_ATTR: SLD905,
}


def import_placement_errors(tree: ast.Module) -> Iterator[AdaptedError]:
    """Yield import-placement errors from ``tree`` with SLD204 attached."""
    for err in check_import_placement(tree):
        yield AdaptedError(lineno=err.lineno, col_offset=err.col_offset, message=SLD204)


def privacy_errors(tree: ast.Module) -> Iterator[AdaptedError]:
    """Yield privacy errors from ``tree`` with the right SLD9xx code formatted in."""
    for err in check_private_access(tree):
        yield AdaptedError(
            lineno=err.lineno,
            col_offset=err.col_offset,
            message=_PRIVACY_CODES[err.kind].format(err.attr),
        )


_OPEN_BRACKETS = frozenset("([{")
_CLOSE_BRACKETS = frozenset(")]}")


def _line_max_bracket_depth(tokens: Iterable[tokenize.TokenInfo]) -> int:
    stack = 0
    max_depth = 0
    for tok in tokens:
        if tok.type != tokenize.OP:
            continue
        if tok.string in _OPEN_BRACKETS:
            stack += 1
            max_depth = max(max_depth, stack)
        elif tok.string in _CLOSE_BRACKETS and stack > 0:
            stack -= 1
    return max_depth


def _token_line(tok: tokenize.TokenInfo) -> int:
    return tok.start[0]


def _bracket_depths_by_line(source: str) -> dict[int, int]:
    # Map line numbers in ``source`` to the deepest bracket stack opened on
    # that line. Only brackets that open on the line are counted: a wrapped
    # continuation line does not inherit the depth from the line that opened
    # the wrap. Closers are tolerated when their opener was on a previous line.
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    groups = itertools.groupby(tokens, key=_token_line)
    return {line: _line_max_bracket_depth(toks) for line, toks in groups if line > 0}


def build_context(tree: ast.AST, lines: list[str]) -> CheckContext:
    """Return per-module state for ``tree`` (source ``lines``) used by node checks."""
    patch_names, abstractmethod_names, cast_names = collect_imports(tree)
    return CheckContext(
        patch_names=patch_names,
        abstractmethod_names=abstractmethod_names,
        cast_names=cast_names,
        lines=lines,
        bracket_depths=_bracket_depths_by_line("\n".join(lines) + "\n"),
    )


def format_sld601(name: str, complexity: FunctionComplexity) -> str:
    """Return the SLD601 message for function ``name`` with ``complexity`` breakdown."""
    return SLD601.format(
        name,
        complexity.weight,
        MAX_FUNCTION_LINES,
        complexity.heaviest_line,
        complexity.heaviest_weight,
        complexity.heaviest_indent,
        complexity.heaviest_brackets,
    )
