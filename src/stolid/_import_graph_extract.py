# Build the workspace import graph from .py files.
#
# Walks every Python file under the given roots, parses it with ``ast``,
# and emits an edge ``importer -> imported`` for every runtime import that
# resolves to another file in the workspace. Imports under
# ``if TYPE_CHECKING:`` (and ``typing.TYPE_CHECKING``/``t.TYPE_CHECKING``
# aliases) are excluded -- they do not execute and using them to break
# import cycles is a legitimate pattern.

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import AbstractSet, Iterator, Sequence

from ._ast_inspection import iter_runtime_nodes, safe_parse
from ._workspace_walk import FileSystem, iter_python_files


@dataclass(frozen=True, slots=True, kw_only=True)
class ModuleEdges:
    """An importer module and the workspace modules it imports at runtime.

    Field ``importer`` is the dotted module name doing the importing;
    ``targets`` is the set of dotted names it imports (filtered to the
    workspace); ``anchor_path`` is the file on disk that defines the
    importer (the ``__init__.py`` for a package, otherwise the module file).
    """

    importer: str
    targets: AbstractSet[str]
    anchor_path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _Parsed:
    path: str
    tree: ast.Module
    module: str
    is_init: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class _ScanState:
    parsed: list[_Parsed] = field(default_factory=list)
    modules: set[str] = field(default_factory=set)
    init_paths: dict[str, str] = field(default_factory=dict)


def _module_name_for(path: str, fs: FileSystem) -> tuple[str, bool]:
    # Return ``(dotted_name, is_init)`` for ``path`` by walking up ancestors
    # that contain ``__init__.py``.
    parts = path.split("/")
    filename = parts[-1]
    stem = filename[: -len(".py")]
    base_parts = parts[:-1]
    package_parts: list[str] = []
    cursor = base_parts
    while cursor:
        init_path = "/".join(cursor) + "/__init__.py"
        try:
            fs.read(init_path)
        except FileNotFoundError:
            break
        package_parts.insert(0, cursor[-1])
        cursor = cursor[:-1]
    if stem == "__init__":
        return ".".join(package_parts), True
    name_parts = [*package_parts, stem] if package_parts else [stem]
    return ".".join(name_parts), False


def _current_package_parts(parsed: _Parsed) -> list[str]:
    parts = parsed.module.split(".")
    return parts if parsed.is_init else parts[:-1]


def _resolve_relative(parsed: _Parsed, level: int, module: str | None) -> str | None:
    # Resolve ``from <dots><module> import ...`` to a dotted target.
    if level == 0:
        return module
    package_parts = _current_package_parts(parsed)
    drop = level - 1
    if drop > len(package_parts):
        return None
    base_parts = package_parts[: len(package_parts) - drop]
    head = ".".join(base_parts)
    if module is None:
        return head or None
    return f"{head}.{module}" if head else module


def _resolve_from(
    parsed: _Parsed, stmt: ast.ImportFrom, modules: frozenset[str]
) -> Iterator[str]:
    target = _resolve_relative(parsed, stmt.level, stmt.module)
    if target is None:
        return
    if target in modules:
        yield target
    for alias in stmt.names:
        if alias.name == "*":
            continue
        candidate = f"{target}.{alias.name}" if target else alias.name
        if candidate in modules:
            yield candidate


def _resolve_import(stmt: ast.Import, modules: frozenset[str]) -> Iterator[str]:
    for alias in stmt.names:
        if alias.name in modules:
            yield alias.name


def _iter_resolved(
    parsed: _Parsed, node: ast.AST, modules: frozenset[str]
) -> Iterator[str]:
    if isinstance(node, ast.ImportFrom):
        yield from _resolve_from(parsed, node, modules)
    elif isinstance(node, ast.Import):
        yield from _resolve_import(node, modules)


def _collect_imports(parsed: _Parsed, modules: frozenset[str]) -> frozenset[str]:
    found: set[str] = set()
    for node in iter_runtime_nodes(parsed.tree):
        for resolved in _iter_resolved(parsed, node, modules):
            if resolved != parsed.module:
                found.add(resolved)
    return frozenset(found)


def _parse_one(fs: FileSystem, path: str, state: _ScanState) -> None:
    tree = safe_parse(fs.read(path), path)
    if tree is None:
        return
    module, is_init = _module_name_for(path, fs)
    if not module:
        return
    state.parsed.append(_Parsed(path=path, tree=tree, module=module, is_init=is_init))
    state.modules.add(module)
    if is_init:
        state.init_paths[module] = path


def extract_graph(fs: FileSystem, roots: Sequence[str]) -> Sequence[ModuleEdges]:
    """Walk ``roots`` via ``fs`` and return the runtime import edges per module.

    The result is one ``ModuleEdges`` per parsed module; edges target only
    other modules present in the workspace. ``TYPE_CHECKING`` blocks are
    excluded.
    """
    state = _ScanState()
    for path in _iter_paths(fs, roots):
        _parse_one(fs, path, state)
    modules = frozenset(state.modules)
    output: list[ModuleEdges] = []
    for parsed in state.parsed:
        anchor = state.init_paths.get(parsed.module, parsed.path)
        targets = _collect_imports(parsed, modules)
        output.append(
            ModuleEdges(importer=parsed.module, targets=targets, anchor_path=anchor)
        )
    return output


def _iter_paths(fs: FileSystem, roots: Sequence[str]) -> Iterator[str]:
    for r in roots:
        yield from iter_python_files(fs, r)


def anchor_for_prefix(prefix: str, edges_list: Sequence[ModuleEdges]) -> str:
    """Return the file path that best anchors a diagnostic about ``prefix``.

    Searches ``edges_list`` (one entry per parsed module) for files whose
    importer matches ``prefix`` or sits below it; prefers the
    lexicographically-first ``__init__.py`` and falls back to the first
    module file in sorted order otherwise.
    """
    inits: list[str] = []
    fallbacks: list[str] = []
    for entry in edges_list:
        name = entry.importer
        if prefix and name != prefix and not name.startswith(prefix + "."):
            continue
        if entry.anchor_path.endswith("/__init__.py"):
            inits.append(entry.anchor_path)
        else:
            fallbacks.append(entry.anchor_path)
    if inits:
        return sorted(inits)[0]
    return sorted(fallbacks)[0]
