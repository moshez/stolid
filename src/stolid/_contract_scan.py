# Cross-file orchestration for the SLD80x public-contract checker.
#
# The scanner runs in two passes:
#
# 1. Build a workspace symbol table by walking every ``.py`` file and
#    classifying every top-level ``class X(...):`` syntactically. The
#    result is a frozenset of names that are *only* concrete -- a name
#    defined as both a Protocol and a concrete class in different files
#    is conservatively treated as a contract (allow rather than false
#    positive).
#
# 2. Re-walk each file. For each public surface annotation, recursively
#    classify it and emit one diagnostic per violation (concrete class,
#    concrete container, or variadic tuple).
#
# Per-line ``# noqa`` markers honored exactly like the duplicate scanner.

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Iterator

from ._ast_inspection import safe_parse
from ._contract_annotation import ContractError, ContractViolation, classify_annotation
from ._contract_classify import ClassKind, classify_class
from ._contract_surface import iter_public_annotations
from ._noqa import is_suppressed
from ._report_line import ReportLine
from ._workspace_walk import FileSystem, iter_python_files

SLD802 = (
    "SLD802 Public annotation references concrete class '{}' "
    "(use a Protocol, ABC, or other contract)"
)
SLD803 = (
    "SLD803 Public annotation uses concrete container '{}' "
    "(use Mapping, Sequence, Iterable, or another abstract from collections.abc)"
)
SLD804 = (
    "SLD804 Public annotation uses variadic tuple "
    "(use a fixed-arity tuple or an abstract Sequence/Iterable)"
)

_MESSAGE_BY_KIND: dict[ContractViolation, str] = {
    ContractViolation.CONCRETE_CLASS: SLD802,
    ContractViolation.CONCRETE_CONTAINER: SLD803,
    ContractViolation.VARIADIC_TUPLE: SLD804,
}

_CODE_BY_KIND: dict[ContractViolation, str] = {
    ContractViolation.CONCRETE_CLASS: "SLD802",
    ContractViolation.CONCRETE_CONTAINER: "SLD803",
    ContractViolation.VARIADIC_TUPLE: "SLD804",
}


@dataclass(frozen=True, slots=True, kw_only=True)
class SymbolTable:
    """Workspace name -> kind information used by the annotation classifier.

    ``concrete_only`` lists names that are defined exclusively as concrete
    classes (never as a Protocol/ABC/TypedDict/NamedTuple/Enum) anywhere
    in the scanned workspace.
    """

    concrete_only: frozenset[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class _ParsedFile:
    path: str
    tree: ast.Module
    source: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _ScanState:
    parsed: list[_ParsedFile] = field(default_factory=list)
    concrete: set[str] = field(default_factory=set)
    contracts: set[str] = field(default_factory=set)


def _classify_top_level(tree: ast.Module, state: _ScanState) -> None:
    for stmt in tree.body:
        if not isinstance(stmt, ast.ClassDef):
            continue
        kind = classify_class(stmt)
        if kind is ClassKind.CONCRETE:
            state.concrete.add(stmt.name)
        else:
            state.contracts.add(stmt.name)


def _parse_one_file(fs: FileSystem, path: str, state: _ScanState) -> None:
    source = fs.read(path)
    tree = safe_parse(source, path)
    if tree is None:
        return
    state.parsed.append(_ParsedFile(path=path, tree=tree, source=source))
    _classify_top_level(tree, state)


def _walk_root(fs: FileSystem, root: str, state: _ScanState) -> None:
    for path in iter_python_files(fs, root):
        _parse_one_file(fs, path, state)


def _suppressed(source_lines: list[str], error: ContractError) -> bool:
    index = error.lineno - 1
    if index < 0 or index >= len(source_lines):
        return False  # pragma: no cover
    return is_suppressed(source_lines[index], _CODE_BY_KIND[error.kind])


def _format(path: str, error: ContractError) -> ReportLine:
    template = _MESSAGE_BY_KIND[error.kind]
    message = template.format(error.name) if error.name else template
    return ReportLine(
        path=path, line=error.lineno, col=error.col_offset, message=message
    )


def _file_diagnostics(
    parsed: _ParsedFile, symbols: SymbolTable
) -> Iterator[ReportLine]:
    source_lines = parsed.source.splitlines()
    for annotation in iter_public_annotations(parsed.tree):
        for error in classify_annotation(annotation, symbols.concrete_only):
            if _suppressed(source_lines, error):
                continue
            yield _format(parsed.path, error)


def build_symbol_table(state: _ScanState) -> SymbolTable:
    """Return the workspace symbol table derived from a completed scan ``state``."""
    return SymbolTable(concrete_only=frozenset(state.concrete - state.contracts))


def scan_paths(fs: FileSystem, roots: list[str]) -> list[ReportLine]:
    """Scan ``roots`` via ``fs`` and return one report line per violation."""
    state = _ScanState()
    for path in roots:
        _walk_root(fs, path, state)
    symbols = build_symbol_table(state)
    output: list[ReportLine] = []
    for parsed in state.parsed:
        output.extend(_file_diagnostics(parsed, symbols))
    return output
