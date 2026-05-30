# Workspace-wide architectural scan: builds the import graph and emits
# SLD831-SLD835 diagnostics. Mirrors the layout of ``_contract_scan``.

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence

from ._import_graph_extract import (
    ModuleEdges,
    anchor_for_prefix,
    extract_graph,
)
from ._import_graph_score import (
    ImportGraph,
    LevelScore,
    build_graph,
    max_module_depth,
    reach_density,
    score_level,
)
from ._report_line import ReportLine
from ._workspace_walk import FileSystem

SLD831 = "SLD831 cyclic dependency cluster contains {} modules: {}"
SLD832 = (
    "SLD832 cross-package cycle at level {} covers {} modules "
    "across {} subpackages: {}"
)
SLD833 = "SLD833 condensation at level {} has depth {} (max {})"
SLD834 = "SLD834 largest level-{} SCC covers {}% of modules"
SLD835 = "SLD835 module-level reach density is {:.2f} (max {})"

MAX_SCC_MODULES = 15
MAX_CROSS_PACKAGE_SCC_WEIGHT = 10
MAX_CONDENSATION_DEPTH = 8
MAX_SUBPACKAGE_MUD_FRACTION = 0.60
MIN_LEVEL_NODES = 10
MAX_REACH_DENSITY = 0.60

_PREVIEW = 5


@dataclass(frozen=True, slots=True, kw_only=True)
class _Context:
    edges_list: Sequence[ModuleEdges]
    graph: ImportGraph


def _build_digraph(
    edges_list: Sequence[ModuleEdges],
) -> ImportGraph:
    nodes = [entry.importer for entry in edges_list]
    edges = [
        (entry.importer, target) for entry in edges_list for target in entry.targets
    ]
    return build_graph(nodes, edges)


def _format_members(members: Sequence[str]) -> str:
    if len(members) <= _PREVIEW:
        return ", ".join(members)
    head = ", ".join(members[:_PREVIEW])
    return f"{head}, ... ({len(members) - _PREVIEW} more)"


def _line(path: str, message: str) -> ReportLine:
    return ReportLine(path=path, line=1, col=0, message=message)


def _common_prefix(members: Sequence[str]) -> str:
    split = [name.split(".") for name in members]
    shared: list[str] = []
    for parts in zip(*split):
        first = parts[0]
        if any(part != first for part in parts):
            break
        shared.append(first)
    return ".".join(shared)


def _scc_anchor(members: Sequence[str], ctx: _Context) -> str:
    prefix = _common_prefix(members)
    return anchor_for_prefix(prefix, ctx.edges_list)


def _first_init(ctx: _Context) -> str:
    inits = sorted(
        entry.anchor_path
        for entry in ctx.edges_list
        if entry.anchor_path.endswith("__init__.py")
    )
    if inits:
        return inits[0]
    return sorted(entry.anchor_path for entry in ctx.edges_list)[0]


def _sld831(score: LevelScore, ctx: _Context) -> Iterator[ReportLine]:
    for members, _ in score.sccs:
        if len(members) <= MAX_SCC_MODULES:
            continue
        anchor = _scc_anchor(members, ctx)
        yield _line(anchor, SLD831.format(len(members), _format_members(members)))


def _sld832(score: LevelScore, ctx: _Context) -> Iterator[ReportLine]:
    for members, weight in score.sccs:
        if weight <= MAX_CROSS_PACKAGE_SCC_WEIGHT:
            continue
        anchor = _scc_anchor(members, ctx)
        yield _line(
            anchor,
            SLD832.format(score.level, weight, len(members), _format_members(members)),
        )


def _sld833(score: LevelScore, ctx: _Context) -> Iterator[ReportLine]:
    if score.node_count < MIN_LEVEL_NODES:
        return
    if score.condensation_depth <= MAX_CONDENSATION_DEPTH:
        return
    yield _line(
        _first_init(ctx),
        SLD833.format(score.level, score.condensation_depth, MAX_CONDENSATION_DEPTH),
    )


def _sld834(score: LevelScore, ctx: _Context) -> Iterator[ReportLine]:
    if score.node_count < MIN_LEVEL_NODES:
        return
    assert score.total_weight != 0  # a level with enough nodes has positive weight
    fraction = score.largest_scc_weight / score.total_weight
    if fraction <= MAX_SUBPACKAGE_MUD_FRACTION:
        return
    yield _line(
        _first_init(ctx),
        SLD834.format(score.level, round(fraction * 100)),
    )


def _sld835(ctx: _Context) -> Iterator[ReportLine]:
    density = reach_density(ctx.graph)
    if density <= MAX_REACH_DENSITY:
        return
    yield _line(
        _first_init(ctx),
        SLD835.format(density, MAX_REACH_DENSITY),
    )


def _iter_diagnostics(ctx: _Context) -> Iterator[ReportLine]:
    if ctx.graph.number_of_nodes() == 0:
        return
    deepest = max_module_depth(ctx.graph)
    module_score = score_level(ctx.graph, deepest)
    yield from _sld831(module_score, ctx)
    yield from _sld835(ctx)
    yield from _sld833(module_score, ctx)
    for level in range(2, deepest):
        score = score_level(ctx.graph, level)
        yield from _sld832(score, ctx)
        yield from _sld833(score, ctx)
        yield from _sld834(score, ctx)


def scan_paths(fs: FileSystem, roots: Sequence[str]) -> Sequence[ReportLine]:
    """Walk ``roots`` via ``fs`` and return SLD83x report lines for the workspace.

    Builds the runtime import graph (excluding ``TYPE_CHECKING`` blocks), runs
    the per-level analyses, and emits one line per finding.

    Args:
        fs: The filesystem used to read each path.
        roots: The root directories to walk for Python files.

    Returns:
        The report lines describing any import-graph violations found.
    """
    edges_list = extract_graph(fs, roots)
    graph = _build_digraph(edges_list)
    ctx = _Context(edges_list=edges_list, graph=graph)
    return list(_iter_diagnostics(ctx))
