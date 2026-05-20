"""Unit tests for the pure scoring primitives in ``_import_graph_score``."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, close_to, equal_to, has_length

from .._import_graph_score import (
    build_graph,
    max_module_depth,
    quotient_at_level,
    reach_density,
    reach_score,
    score_level,
)


class TestBuildGraph(unittest.TestCase):
    """Verifying ``build_graph`` over hand-built node/edge lists."""

    def test_nodes_have_size_one(self) -> None:
        """Verify every node gets a ``size`` attribute of 1."""
        graph = build_graph(["a", "b"], [("a", "b")])
        for node in graph.nodes():
            assert_that(graph.nodes[node]["size"], equal_to(1))

    def test_invalid_edges_dropped(self) -> None:
        """Verify self-loops and edges to unknown nodes are silently dropped."""
        for name, edges in [
            ("self_loop", [("a", "a")]),
            ("unknown_target", [("a", "ghost")]),
        ]:
            with self.subTest(name=name):
                assert_that(build_graph(["a"], edges).number_of_edges(), equal_to(0))


class TestReachScore(unittest.TestCase):
    """Reach-score and density for a few canonical graphs."""

    def test_chain_density_one_half(self) -> None:
        """Verify a fully-reachable chain of 4 modules has density 0.5."""
        graph = build_graph(["a", "b", "c", "d"], [("a", "b"), ("b", "c"), ("c", "d")])
        assert_that(reach_density(graph), close_to(0.5, 0.001))

    def test_all_mutually_reachable_has_scc_bonus(self) -> None:
        """Verify an all-SCC graph scores the ordered pairs plus SCC bonus."""
        graph = build_graph(
            ["a", "b", "c"],
            [(u, v) for u in "abc" for v in "abc" if u != v],
        )
        # 6 ordered + 3 SCC bonus = 9
        assert_that(reach_score(graph), equal_to(9))

    def test_disconnected_density_zero(self) -> None:
        """Verify disconnected nodes have density zero."""
        graph = build_graph(["a", "b", "c"], [])
        assert_that(reach_density(graph), equal_to(0.0))

    def test_empty_graph_safe(self) -> None:
        """Verify the empty graph returns density 0 and score 0."""
        graph = build_graph([], [])
        assert_that(reach_density(graph), equal_to(0.0))
        assert_that(reach_score(graph), equal_to(0))

    def test_single_node_density_zero(self) -> None:
        """Verify a one-node graph has density 0 (no pairs)."""
        graph = build_graph(["a"], [])
        assert_that(reach_density(graph), equal_to(0.0))


class TestQuotientAtLevel(unittest.TestCase):
    """Verifying quotient collapsing at various levels."""

    def test_level_one_collapses_to_top(self) -> None:
        """Verify level 1 maps every module to its top-level package."""
        graph = build_graph(
            ["pkg.a", "pkg.b.c", "other.x"],
            [("pkg.a", "pkg.b.c"), ("pkg.b.c", "other.x")],
        )
        quotient = quotient_at_level(graph, 1)
        assert_that(set(quotient.nodes()), equal_to({"pkg", "other"}))
        assert_that(quotient.nodes["pkg"]["size"], equal_to(2))
        assert_that(quotient.nodes["other"]["size"], equal_to(1))

    def test_self_loops_after_collapse_dropped(self) -> None:
        """Verify a cross-module edge that becomes a self-loop is dropped."""
        graph = build_graph(["pkg.a", "pkg.b"], [("pkg.a", "pkg.b")])
        quotient = quotient_at_level(graph, 1)
        assert_that(quotient.number_of_edges(), equal_to(0))


class TestScoreLevel(unittest.TestCase):
    """Per-level aggregated metrics returned by ``score_level``."""

    def test_no_sccs_in_chain(self) -> None:
        """Verify a DAG has no non-trivial SCCs and depth equals the chain length."""
        graph = build_graph(["a", "b", "c"], [("a", "b"), ("b", "c")])
        score = score_level(graph, 1)
        assert_that(score.sccs, has_length(0))
        assert_that(score.condensation_depth, equal_to(3))

    def test_scc_weight_sums_node_sizes(self) -> None:
        """Verify SCC weight aggregates the ``size`` attributes of its members."""
        graph = build_graph(
            ["pkg.a.x", "pkg.b.y", "pkg.a.z", "pkg.b.w"],
            [
                ("pkg.a.x", "pkg.b.y"),
                ("pkg.b.y", "pkg.a.z"),
                ("pkg.a.z", "pkg.b.w"),
                ("pkg.b.w", "pkg.a.x"),
            ],
        )
        score = score_level(graph, 2)
        # At level 2: {pkg.a, pkg.b} form an SCC; each covers 2 modules.
        assert_that(score.largest_scc_weight, equal_to(4))


class TestEmptyGraph(unittest.TestCase):
    """Pure scoring functions tolerate an empty graph."""

    def test_score_level_on_empty_graph(self) -> None:
        """Verify ``score_level`` returns zeroed metrics for an empty graph."""
        graph = build_graph([], [])
        score = score_level(graph, 1)
        assert_that(score.node_count, equal_to(0))
        assert_that(score.condensation_depth, equal_to(0))


class TestMaxModuleDepth(unittest.TestCase):
    """Verifying ``max_module_depth``."""

    def test_returns_deepest_dot_count(self) -> None:
        """Verify the deepest dotted-name part count is returned."""
        graph = build_graph(["pkg", "pkg.a", "pkg.a.b.c"], [])
        assert_that(max_module_depth(graph), equal_to(4))

    def test_empty_graph_returns_zero(self) -> None:
        """Verify the empty graph yields depth 0."""
        graph = build_graph([], [])
        assert_that(max_module_depth(graph), equal_to(0))
