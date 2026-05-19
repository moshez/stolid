# Filesystem walk, parsing, and clone grouping for the duplicate detector.

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass, field

from ._constants import MIN_CLONE_NODES, MIN_CLONE_SCORE
from ._duplicate_fingerprint import Occurrence, fingerprint
from ._duplicate_scope import ScopeStack
from ._duplicate_score import subtree_score
from ._workspace_walk import FileSystem, iter_python_files


@dataclass(frozen=True, slots=True, kw_only=True)
class Location:
    """A position within a source file.

    ``path`` is the file location; ``line`` and ``col`` give the 1-based line
    number and 0-based column offset within it.
    """

    path: str
    line: int
    col: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CloneOccurrence:
    """An occurrence of a clone, with its ``location`` and size.

    ``node_count`` is the total number of AST nodes in the cloned subtree;
    ``end_line`` is the 1-based last line the subtree spans.
    """

    location: Location
    node_count: int
    end_line: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CloneGroup:
    """A group of structurally identical subtree occurrences.

    ``digest`` is the shared Merkle hash and ``occurrences`` lists every
    place that subtree was found.
    """

    digest: bytes
    occurrences: tuple[CloneOccurrence, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ScanResult:
    """The output of a duplicate scan.

    ``groups`` lists the clone groups found; ``syntax_errors`` lists paths
    that could not be parsed.
    """

    groups: list[CloneGroup] = field(default_factory=list)
    syntax_errors: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class _PathOccurrence:
    path: str
    occurrence: Occurrence


def _parse_file(path: str, source: str) -> ast.Module | None:
    try:
        return ast.parse(source, filename=path)
    except SyntaxError:
        return None


def _is_eligible(occurrence: Occurrence) -> bool:
    if isinstance(occurrence.node, ast.Module):
        return False
    if getattr(occurrence.node, "lineno", None) is None:
        return False
    if occurrence.node_count < MIN_CLONE_NODES:
        return False
    return subtree_score(occurrence.node) >= MIN_CLONE_SCORE


def _node_end_line(node: ast.AST) -> int:
    end = getattr(node, "end_lineno", None)
    if end is not None:
        return int(end)
    return int(getattr(node, "lineno", 1))  # pragma: no cover


def _to_clone_occurrence(path: str, occurrence: Occurrence) -> CloneOccurrence:
    node = occurrence.node
    return CloneOccurrence(
        location=Location(
            path=path,
            line=getattr(node, "lineno", 1),
            col=getattr(node, "col_offset", 0),
        ),
        node_count=occurrence.node_count,
        end_line=_node_end_line(node),
    )


def _group_clones(entries: list[_PathOccurrence]) -> list[CloneGroup]:
    buckets: dict[bytes, list[_PathOccurrence]] = defaultdict(list)
    for entry in entries:
        buckets[entry.occurrence.digest].append(entry)
    groups: list[CloneGroup] = []
    for digest, items in buckets.items():
        if len(items) < 2:
            continue
        occurrences = tuple(
            _to_clone_occurrence(item.path, item.occurrence) for item in items
        )
        groups.append(CloneGroup(digest=digest, occurrences=occurrences))
    return groups


def _contains(parent: CloneOccurrence, child: CloneOccurrence) -> bool:
    if parent.location.path != child.location.path:
        return False
    if parent.location.line > child.location.line:
        return False
    return parent.end_line >= child.end_line


def _dominated(group: CloneGroup, larger: list[CloneGroup]) -> bool:
    for parent in larger:
        if all(
            any(_contains(parent_occ, occ) for parent_occ in parent.occurrences)
            for occ in group.occurrences
        ):
            return True
    return False


def _drop_dominated(clones: list[CloneGroup]) -> list[CloneGroup]:
    ordered = sorted(
        clones, key=lambda group: group.occurrences[0].node_count, reverse=True
    )
    kept: list[CloneGroup] = []
    for group in ordered:
        if not _dominated(group, kept):
            kept.append(group)
    return kept


def _scan_one_file(
    fs: FileSystem,
    path: str,
    entries: list[_PathOccurrence],
    syntax_errors: list[str],
) -> None:
    source = fs.read(path)
    tree = _parse_file(path, source)
    if tree is None:
        syntax_errors.append(path)
        return
    occurrences: list[Occurrence] = []
    fingerprint(tree, ScopeStack(), occurrences)
    for found in occurrences:
        if _is_eligible(found):
            entries.append(_PathOccurrence(path=path, occurrence=found))


def _scan_root(
    fs: FileSystem,
    root: str,
    entries: list[_PathOccurrence],
    syntax_errors: list[str],
) -> None:
    for path in iter_python_files(fs, root):
        _scan_one_file(fs, path, entries, syntax_errors)


def scan_paths(fs: FileSystem, roots: list[str]) -> ScanResult:
    """Scan ``roots`` (via filesystem ``fs``) and return the clone groups found."""
    entries: list[_PathOccurrence] = []
    syntax_errors: list[str] = []
    for path in roots:
        _scan_root(fs, path, entries, syntax_errors)
    groups = _group_clones(entries)
    groups = _drop_dominated(groups)
    return ScanResult(groups=groups, syntax_errors=syntax_errors)
