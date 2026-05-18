# Check for try statements that should be context managers.
#
# SLD606: ``try``/``finally`` is the bare-knuckles version of a context
# manager. Replace it either with an existing ``with`` (the cleanup
# already lives behind ``__exit__``) or with a ``@contextlib.contextmanager``
# generator. The exception is when the try/finally appears directly
# inside a function decorated with ``contextlib.contextmanager`` or
# ``contextlib.asynccontextmanager`` -- that *is* how you write a
# context manager from a generator, so the pattern is legitimate there.
#
# SLD607: ``try``/``except``/``pass`` (handlers whose entire body is
# ``pass``) should be ``with contextlib.suppress(...)``: the intent
# (swallow particular exceptions) lands in one line and the noise goes
# away.

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from ._ast_inspection import (
    FUNCTION_DEF_NODES,
    FunctionType,
    is_attribute_in,
    is_name_among,
)

SLD606 = (
    "SLD606 'try'/'finally' should be replaced with a context manager "
    "(use 'with' or @contextlib.contextmanager)"
)
SLD607 = (
    "SLD607 'try'/'except' with pass-only handlers should be "
    "'with contextlib.suppress(...)'"
)

_CONTEXTMANAGER_NAMES = frozenset({"contextmanager", "asynccontextmanager"})


@dataclass(frozen=True, slots=True, kw_only=True)
class TryError:
    """A try-statement violation.

    ``lineno`` and ``col_offset`` locate the offending ``try``;
    ``message`` is the formatted SLD606 or SLD607 diagnostic.
    """

    lineno: int
    col_offset: int
    message: str


def _emit(node: ast.Try, message: str) -> TryError:
    return TryError(lineno=node.lineno, col_offset=node.col_offset, message=message)


def _is_contextmanager_decorator(node: ast.expr) -> bool:
    # Match @contextmanager / @asynccontextmanager whether bare, dotted
    # (e.g. @contextlib.contextmanager), or invoked (rare for these, but
    # @contextmanager() is syntactically allowed).
    if isinstance(node, ast.Call):
        return _is_contextmanager_decorator(node.func)
    return is_name_among(node, _CONTEXTMANAGER_NAMES) or is_attribute_in(
        node, _CONTEXTMANAGER_NAMES
    )


def _is_contextmanager(func: FunctionType) -> bool:
    return any(_is_contextmanager_decorator(d) for d in func.decorator_list)


def _is_pass_only(body: list[ast.stmt]) -> bool:
    return len(body) == 1 and isinstance(body[0], ast.Pass)


def _all_handlers_pass(handlers: list[ast.ExceptHandler]) -> bool:
    # A try statement reaching this check always has at least one handler:
    # _check_try only calls it when both ``finalbody`` and ``orelse`` are
    # empty, and that leaves ``except`` clauses as the only legal shape.
    return all(_is_pass_only(h.body) for h in handlers)


def _check_try(node: ast.Try, in_contextmanager: bool) -> Iterator[TryError]:
    if node.finalbody and not in_contextmanager:
        yield _emit(node, SLD606)
    if not node.finalbody and not node.orelse and _all_handlers_pass(node.handlers):
        yield _emit(node, SLD607)


def _walk(node: ast.AST, in_contextmanager: bool) -> Iterator[TryError]:
    if isinstance(node, ast.Try):
        yield from _check_try(node, in_contextmanager)
    if isinstance(node, FUNCTION_DEF_NODES):
        in_contextmanager = _is_contextmanager(node)
    for child in ast.iter_child_nodes(node):
        yield from _walk(child, in_contextmanager)


def check_try(tree: ast.Module) -> Iterator[TryError]:
    """Yield SLD606 / SLD607 violations from ``tree``."""
    yield from _walk(tree, in_contextmanager=False)
