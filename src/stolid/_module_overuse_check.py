# Check for broad coupling to a single dependency. Two independent
# patterns are scored:
#
#   - SLD205: ``from Y import a, b, c, ...`` aggregated across every
#     ``from Y import ...`` statement in the module.
#   - SLD207: ``import Y [as A]`` plus distinct attribute names accessed
#     via ``Y.x`` / ``A.x``.
#
# Each pattern fires when the distinct-reference count exceeds the limit.
#
# ``typing`` and ``ast`` are allowlisted: both are broad-API stdlib
# namespaces where reaching for many members is structural, not a
# coupling smell (type annotations need many typing names; AST tools
# inherently touch many ``ast.*`` node classes). Imports and uses inside
# ``if TYPE_CHECKING:`` blocks are also ignored, since they exist only
# for the type checker.

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Iterator

from ._ast_inspection import iter_runtime_nodes
from ._constants import MAX_MODULE_REFERENCES

SLD205 = (
    "SLD205 Module '{}' is over-imported: {} distinct names imported "
    "(limit: {}); split the dependency or narrow the imports"
)
SLD207 = (
    "SLD207 Module '{}' is overused: {} distinct attributes accessed "
    "(limit: {}); split the dependency or wrap it behind a narrower API"
)

_ALLOWED_MODULES: frozenset[str] = frozenset({"typing", "ast"})


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleOveruseError:
    """A module-overuse violation.

    ``lineno`` and ``col_offset`` locate the offending import statement;
    ``message`` is the formatted SLD205 or SLD207 diagnostic.

    Attributes:
        lineno: Line number of the offending import statement.
        col_offset: Column offset of the offending import statement.
        message: The formatted SLD205 or SLD207 diagnostic string.
    """

    lineno: int
    col_offset: int
    message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _State:
    # First ``from Y import ...`` statement seen per module ``Y``.
    from_first: dict[str, ast.ImportFrom] = field(default_factory=dict)
    # Distinct imported names aggregated per module.
    from_names: dict[str, set[str]] = field(default_factory=dict)
    # Local-name -> (original module name, ``ast.Import`` node).
    aliases: dict[str, tuple[str, ast.Import]] = field(default_factory=dict)
    # Local-name -> distinct attribute names accessed.
    attrs: dict[str, set[str]] = field(default_factory=dict)


def _record_from(stmt: ast.ImportFrom, state: _State) -> None:
    module = stmt.module
    if module is None or module in _ALLOWED_MODULES:
        return
    state.from_first.setdefault(module, stmt)
    names = state.from_names.setdefault(module, set())
    for alias in stmt.names:
        names.add(alias.name)


def _record_import(stmt: ast.Import, state: _State) -> None:
    for alias in stmt.names:
        if alias.name in _ALLOWED_MODULES:
            continue
        bound = alias.asname or alias.name.split(".")[0]
        state.aliases[bound] = (alias.name, stmt)


def _record_attribute(node: ast.Attribute, state: _State) -> None:
    value = node.value
    if not isinstance(value, ast.Name):
        return
    if value.id not in state.aliases:
        return
    state.attrs.setdefault(value.id, set()).add(node.attr)


def _collect(tree: ast.Module) -> _State:
    state = _State()
    for node in iter_runtime_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            _record_from(node, state)
        elif isinstance(node, ast.Import):
            _record_import(node, state)
        elif isinstance(node, ast.Attribute):
            _record_attribute(node, state)
    return state


def _from_errors(state: _State) -> Iterator[ModuleOveruseError]:
    for module, names in state.from_names.items():
        if len(names) <= MAX_MODULE_REFERENCES:
            continue
        stmt = state.from_first[module]
        yield ModuleOveruseError(
            lineno=stmt.lineno,
            col_offset=stmt.col_offset,
            message=SLD205.format(module, len(names), MAX_MODULE_REFERENCES),
        )


def _import_errors(state: _State) -> Iterator[ModuleOveruseError]:
    for bound, (module, stmt) in state.aliases.items():
        attrs = state.attrs.get(bound, set())
        if len(attrs) <= MAX_MODULE_REFERENCES:
            continue
        yield ModuleOveruseError(
            lineno=stmt.lineno,
            col_offset=stmt.col_offset,
            message=SLD207.format(module, len(attrs), MAX_MODULE_REFERENCES),
        )


def check_module_overuse(tree: ast.Module) -> Iterator[ModuleOveruseError]:
    """Yield SLD205/SLD207 errors when ``tree``'s reference counts exceed the limit.

    Args:
        tree: The module AST to check for over-imported or overused modules.

    Yields:
        One error per module whose distinct reference count exceeds the limit.
    """
    state = _collect(tree)
    yield from _from_errors(state)
    yield from _import_errors(state)
