# Pure graph-analysis primitives for the SLD83x rules.
#
# Functions in this module take a NetworkX ``DiGraph`` whose nodes carry a
# ``size`` attribute (the number of leaf modules they cover) and produce
# the per-level scoring used by ``_import_graph_scan``. There is no I/O,
# no AST, no filesystem -- everything is testable against hand-built
# graphs.

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import networkx as nx


@dataclass(frozen=True, slots=True, kw_only=True)
class LevelScore:
    """Aggregate metrics computed at one quotient level.

    Field ``level`` is the truncation depth. ``node_count`` is the number
    of distinct prefixes at that level. ``total_weight`` sums the leaf
    counts. ``sccs`` lists each non-trivial strongly-connected component
    as ``(members, weight)``. ``largest_scc_weight`` is the heaviest
    non-trivial SCC's total module weight, or 0 if none. ``condensation_depth``
    is the longest-path length in the condensation DAG.
    """

    level: int
    node_count: int
    total_weight: int
    sccs: tuple[tuple[tuple[str, ...], int], ...]
    largest_scc_weight: int
    condensation_depth: int


def _quotient_node(name: str, level: int) -> str:
    parts = name.split(".")
    return ".".join(parts[:level])


def _bump_node(graph: nx.DiGraph, name: str) -> None:
    if graph.has_node(name):
        graph.nodes[name]["size"] += 1
    else:
        graph.add_node(name, size=1)


def _accept_edge(graph: nx.DiGraph, source: str, target: str) -> None:
    if source == target:
        return
    if graph.has_node(source) and graph.has_node(target):
        graph.add_edge(source, target)


def quotient_at_level(graph: nx.DiGraph, level: int) -> nx.DiGraph:
    """Return the level-``level`` quotient of ``graph`` with node-weight sizes.

    Each leaf module collapses to the prefix of its dotted name of length
    ``min(level, depth)``. The resulting graph has the same node set as the
    distinct prefixes, edges aggregated, and a ``size`` attribute equal to
    the leaf count covered by each prefix. Self-loops introduced by
    collapsing are dropped.
    """
    mapping: dict[str, str] = {
        node: _quotient_node(node, level) for node in graph.nodes()
    }
    quotient = _init_with_nodes(mapping.values())
    for u, v in graph.edges():
        head, tail = mapping[u], mapping[v]
        if head == tail:
            continue
        quotient.add_edge(head, tail)
    return quotient


def _condensation_longest_path(graph: nx.DiGraph) -> int:
    condensed = nx.condensation(graph)
    if condensed.number_of_nodes() == 0:
        return 0
    return len(nx.dag_longest_path(condensed))


def _non_trivial_sccs(
    graph: nx.DiGraph,
) -> list[tuple[tuple[str, ...], int]]:
    result: list[tuple[tuple[str, ...], int]] = []
    for scc in nx.strongly_connected_components(graph):
        if len(scc) < 2:
            continue
        members = tuple(sorted(scc))
        weight = sum(graph.nodes[member]["size"] for member in members)
        result.append((members, weight))
    return result


def score_level(graph: nx.DiGraph, level: int) -> LevelScore:
    """Score ``graph`` at quotient ``level`` and return the aggregated metrics."""
    quotient = quotient_at_level(graph, level)
    sccs = _non_trivial_sccs(quotient)
    total_weight = sum(quotient.nodes[node]["size"] for node in quotient.nodes())
    largest = max((weight for _, weight in sccs), default=0)
    depth = _condensation_longest_path(quotient)
    return LevelScore(
        level=level,
        node_count=quotient.number_of_nodes(),
        total_weight=total_weight,
        sccs=tuple(sccs),
        largest_scc_weight=largest,
        condensation_depth=depth,
    )


def max_module_depth(graph: nx.DiGraph) -> int:
    """Return the deepest dotted-name segment count across nodes in ``graph``."""
    if graph.number_of_nodes() == 0:
        return 0
    return max(node.count(".") + 1 for node in graph.nodes())


def reach_score(graph: nx.DiGraph) -> int:
    """Return ``graph``'s reach score: ordered reachable pairs plus an SCC bonus.

    For every ordered pair ``(u, v)`` with ``u != v`` and ``v`` reachable from
    ``u``, add one. For every unordered pair of distinct modules in the same
    non-trivial strongly-connected component, add an additional one.
    """
    if graph.number_of_nodes() == 0:
        return 0
    closure = nx.transitive_closure(graph, reflexive=False)
    ordered = sum(1 for u, v in closure.edges() if u != v)
    scc_bonus = 0
    for scc in nx.strongly_connected_components(graph):
        size = len(scc)
        if size < 2:
            continue
        scc_bonus += size * (size - 1) // 2
    return ordered + scc_bonus


def reach_density(graph: nx.DiGraph) -> float:
    """Return ``reach_score(graph)`` normalized by ``n * (n - 1)``.

    Returns 0.0 when the graph has fewer than two nodes.
    """
    n = graph.number_of_nodes()
    if n < 2:
        return 0.0
    return reach_score(graph) / (n * (n - 1))


def _init_with_nodes(names: Iterable[str]) -> nx.DiGraph:
    graph: nx.DiGraph = nx.DiGraph()
    for n in names:
        _bump_node(graph, n)
    return graph


def build_graph(nodes: list[str], edges: list[tuple[str, str]]) -> nx.DiGraph:
    """Return a NetworkX ``DiGraph`` with the given ``nodes`` and ``edges``.

    Each node gets a ``size`` attribute of 1. Self-loops are dropped.
    """
    graph = _init_with_nodes(nodes)
    for u, v in edges:
        _accept_edge(graph, u, v)
    return graph
