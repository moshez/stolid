# Shared test helpers for the SLD83x import-graph rule tests.

from __future__ import annotations

from typing import AbstractSet, Mapping, Protocol, Sequence

from ..cli import import_edges, import_graph_report
from .code_parser import dedent_files
from .fakes import InMemoryFileSystem


class _Edge(Protocol):
    # One module's resolved import-graph edges.

    @property
    def importer(self) -> str:
        """Return the dotted name of the importing module."""
        ...

    @property
    def targets(self) -> AbstractSet[str]:
        """Return the dotted names this module imports within the workspace."""
        ...


def extract_edges(files: Mapping[str, str]) -> Sequence[_Edge]:
    """Return the import-graph edges extracted from in-memory ``files``."""
    fs = InMemoryFileSystem(_files=dedent_files(files))
    return list(import_edges(fs, ["."]))


def targets_of(files: Mapping[str, str], importer: str) -> AbstractSet[str]:
    """Return the resolved import targets of module ``importer`` in ``files``."""
    return next(e.targets for e in extract_edges(files) if e.importer == importer)


def scan_to_pairs(files: Mapping[str, str]) -> Sequence[tuple[str, str]]:
    """Scan ``files`` and return ``(path, message)`` pairs for each report line."""
    fs = InMemoryFileSystem(_files=dedent_files(files))
    return [(line.path, line.message) for line in import_graph_report(fs, ["."])]


def importers_of(files: Mapping[str, str]) -> AbstractSet[str]:
    """Return the set of dotted module names extracted from ``files``."""
    return frozenset(e.importer for e in extract_edges(files))


def scan_codes(files: Mapping[str, str]) -> Sequence[str]:
    """Return the SLD83x diagnostic codes produced by scanning ``files``."""
    return [msg.split()[0] for _, msg in scan_to_pairs(files)]


def all_to_all(n: int, prefix: str = "pkg") -> Mapping[str, str]:
    """Return ``files`` for ``n`` modules under ``prefix`` each importing every other.

    With ``prefix='pkg'``, includes a ``pkg/__init__.py``; with ``prefix=''``,
    the modules live at the workspace root with no package wrapper.
    """
    stems = [f"m{i}" for i in range(n)]
    files: dict[str, str] = {}
    if prefix:
        files[f"{prefix}/__init__.py"] = ""
    for s in stems:
        others = [other for other in stems if other != s]
        rhs = "".join(_one_import(prefix, other) for other in others)
        path = f"{prefix}/{s}.py" if prefix else f"{s}.py"
        files[path] = rhs
    return files


def _one_import(prefix: str, name: str) -> str:
    if prefix:
        return f"from {prefix} import {name}\n"
    return f"import {name}\n"
