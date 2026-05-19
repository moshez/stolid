"""Tests for SLD83x: import-graph architectural rules."""

from __future__ import annotations

import textwrap
import unittest
from typing import Mapping, Sequence

from hamcrest import assert_that, equal_to, has_length

from .._import_graph_extract import extract_graph
from .._import_graph_scan import scan_paths
from .fakes import InMemoryFileSystem


def _dedent_files(files: Mapping[str, str]) -> Mapping[str, str]:
    return {
        path: textwrap.dedent(source).lstrip("\n") for path, source in files.items()
    }


def _scan(files: Mapping[str, str]) -> Sequence[tuple[str, str]]:
    fs = InMemoryFileSystem(_files=_dedent_files(files))
    rows = scan_paths(fs, ["."])
    return [(line.path, line.message) for line in rows]


def _codes(files: Mapping[str, str]) -> Sequence[str]:
    return [msg.split()[0] for _, msg in _scan(files)]


def _chain_imports(n: int) -> dict[str, str]:
    files: dict[str, str] = {"pkg/__init__.py": ""}
    for i in range(n):
        if i + 1 < n:
            files[f"pkg/m{i}.py"] = f"from pkg import m{i + 1}\n"
        else:
            files[f"pkg/m{i}.py"] = ""
    return files


def _cycle_imports(modules: Sequence[str], parent: str = "pkg") -> dict[str, str]:
    files: dict[str, str] = {f"{parent}/__init__.py": ""}
    for index, stem in enumerate(modules):
        nxt = modules[(index + 1) % len(modules)]
        files[f"{parent}/{stem}.py"] = f"from {parent} import {nxt}\n"
    return files


def _cross_pkg_cycle(count_per_sub: int) -> dict[str, str]:
    # Build two subpackages each with ``count_per_sub`` modules; each
    # subpackage's first module imports the other subpackage's first
    # module, creating a cycle at level 2 even though no single module
    # cycle exists at the leaf level.
    files: dict[str, str] = {
        "pkg/__init__.py": "",
        "pkg/aa/__init__.py": "",
        "pkg/bb/__init__.py": "",
    }
    files["pkg/aa/m0.py"] = "from pkg.bb import m0\n"
    files["pkg/bb/m0.py"] = "from pkg.aa import m0\n"
    for i in range(1, count_per_sub):
        files[f"pkg/aa/m{i}.py"] = "from pkg.aa import m0\n"
        files[f"pkg/bb/m{i}.py"] = "from pkg.bb import m0\n"
    return files


def _extract(files: Mapping[str, str]) -> list:
    fs = InMemoryFileSystem(_files=_dedent_files(files))
    return list(extract_graph(fs, ["."]))


PKG_FIRST = "pkg.a"
PKG_SECOND = "pkg.b"


class TestSLD831CyclicClusterTooLarge(unittest.TestCase):
    """Cyclic dependency cluster of > 15 modules."""

    def test_fires_above_threshold(self) -> None:
        """Verify SLD831 fires for an SCC of 16 mutually-importing modules."""
        stems = [f"m{i}" for i in range(16)]
        codes = _codes(_cycle_imports(stems))
        assert_that(codes.count("SLD831"), equal_to(1))

    def test_silent_at_threshold(self) -> None:
        """Verify SLD831 is silent for an SCC of exactly 15 modules."""
        stems = [f"m{i}" for i in range(15)]
        codes = _codes(_cycle_imports(stems))
        assert_that("SLD831" in codes, equal_to(False))

    def test_silent_for_dag(self) -> None:
        """Verify SLD831 is silent for a DAG (no SCCs)."""
        codes = _codes(_chain_imports(20))
        assert_that("SLD831" in codes, equal_to(False))

    def test_anchor_is_package_init(self) -> None:
        """Verify the diagnostic anchors on the package's ``__init__.py``."""
        stems = [f"m{i}" for i in range(16)]
        rows = _scan(_cycle_imports(stems))
        anchors = {path for path, msg in rows if "SLD831" in msg}
        assert_that(anchors, equal_to({"pkg/__init__.py"}))


class TestSLD832CrossPackageCycle(unittest.TestCase):
    """Cross-package cycles whose total module weight > 10."""

    def test_fires_above_weight_threshold(self) -> None:
        """Verify SLD832 fires when subpackage cycle covers > 10 modules."""
        # count_per_sub=6 -> 6 leaves + 1 ``__init__.py`` per subpackage = 7
        # modules each, total weight 14.
        codes = _codes(_cross_pkg_cycle(count_per_sub=6))
        assert_that(codes.count("SLD832"), equal_to(1))

    def test_silent_below_weight_threshold(self) -> None:
        """Verify SLD832 is silent when cycle covers 10 or fewer modules."""
        # count_per_sub=4 -> 5 modules per subpackage = 10 total weight.
        codes = _codes(_cross_pkg_cycle(count_per_sub=4))
        assert_that("SLD832" in codes, equal_to(False))

    def test_silent_for_flat_package(self) -> None:
        """Verify SLD832 doesn't fire when no level-2 quotient exists."""
        # Modules are all at depth 2 (``pkg.m0``..``pkg.m15``); the only level
        # the rule could apply is the module level, which is excluded.
        stems = [f"m{i}" for i in range(12)]
        codes = _codes(_cycle_imports(stems))
        assert_that("SLD832" in codes, equal_to(False))


class TestSLD833ExcessiveCondensationDepth(unittest.TestCase):
    """Excessive condensation depth (> 8) at any level with at least 10 nodes."""

    def test_fires_above_threshold(self) -> None:
        """Verify SLD833 fires when a chain of 10 modules exceeds depth 8."""
        codes = _codes(_chain_imports(10))
        assert_that(codes.count("SLD833"), equal_to(1))

    def test_silent_below_minimum_nodes(self) -> None:
        """Verify SLD833 is silent on a deep chain with fewer than 10 nodes."""
        # 9 top-level modules in a chain (no package wrapper):
        # nodes=9 < 10, doesn't trigger even though depth=9.
        files: dict[str, str] = {}
        for i in range(9):
            files[f"m{i}.py"] = f"import m{i + 1}\n" if i + 1 < 9 else ""
        codes = _codes(files)
        assert_that("SLD833" in codes, equal_to(False))

    def test_silent_for_shallow_graph(self) -> None:
        """Verify SLD833 is silent when condensation depth fits the threshold."""
        # 10 leaves importing a common base: nodes=11, depth=2.
        files: dict[str, str] = {"pkg/__init__.py": "", "pkg/base.py": ""}
        for i in range(10):
            files[f"pkg/m{i}.py"] = "from pkg import base\n"
        codes = _codes(files)
        assert_that("SLD833" in codes, equal_to(False))


class TestSLD834SubpackageMudBall(unittest.TestCase):
    """Largest SCC at quotient level covers > 60% of total module weight."""

    def test_fires_above_threshold(self) -> None:
        """Verify SLD834 fires when level-2 SCC covers > 60% of modules."""
        # 8 subpackages in a ring cycle at level 2, plus 4 unrelated
        # subpackages. Level 2 nodes: 8 + 4 + 1 = 13 (>= 10). SCC weight =
        # 16, total weight = 24, fraction = 67%.
        cycle_subs = list("abcdefgh")
        files: dict[str, str] = {"pkg/__init__.py": ""}
        for sub in cycle_subs:
            files[f"pkg/{sub}/__init__.py"] = ""
        for index, sub in enumerate(cycle_subs):
            nxt = cycle_subs[(index + 1) % len(cycle_subs)]
            files[f"pkg/{sub}/m.py"] = f"from pkg.{nxt} import m\n"
        for sub in ("p", "q", "r", "s"):
            files[f"pkg/{sub}/__init__.py"] = ""
            files[f"pkg/{sub}/m.py"] = ""
        codes = _codes(files)
        assert_that(codes.count("SLD834"), equal_to(1))

    def test_silent_when_scc_small(self) -> None:
        """Verify SLD834 is silent when no SCC covers a majority."""
        files: dict[str, str] = {
            "pkg/__init__.py": "",
            "pkg/aa/__init__.py": "",
            "pkg/bb/__init__.py": "",
            "pkg/cc/__init__.py": "",
            "pkg/dd/__init__.py": "",
            "pkg/ee/__init__.py": "",
            "pkg/ff/__init__.py": "",
        }
        # Each subpackage has a few independent leaf modules.
        for sub in ("aa", "bb", "cc", "dd", "ee", "ff"):
            for i in range(2):
                files[f"pkg/{sub}/m{i}.py"] = ""
        codes = _codes(files)
        assert_that("SLD834" in codes, equal_to(False))


class TestSLD835ReachDensity(unittest.TestCase):
    """Module-level reach density > 0.6."""

    def test_fires_above_threshold(self) -> None:
        """Verify SLD835 fires for an all-mutually-importing cluster."""
        stems = [f"m{i}" for i in range(8)]
        files = {f"pkg/{n}.py": "" for n in stems}
        files["pkg/__init__.py"] = ""
        for s in stems:
            others = [other for other in stems if other != s]
            files[f"pkg/{s}.py"] = "".join(f"from pkg import {o}\n" for o in others)
        codes = _codes(files)
        assert_that(codes.count("SLD835"), equal_to(1))

    def test_silent_for_chain(self) -> None:
        """Verify SLD835 is silent for a chain (density 0.5)."""
        codes = _codes(_chain_imports(10))
        assert_that("SLD835" in codes, equal_to(False))


class TestTypeCheckingExclusion(unittest.TestCase):
    """``TYPE_CHECKING`` blocks are excluded from the runtime import graph."""

    def test_imports_inside_type_checking_ignored(self) -> None:
        """Verify TYPE_CHECKING-only edges do not create cycles."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": (
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    from pkg import b\n"
            ),
            "pkg/b.py": "from pkg import a\n",
        }
        codes = _codes(files)
        # a -> b only at type-check time, b -> a at runtime: no cycle.
        assert_that("SLD831" in codes, equal_to(False))

    def test_runtime_else_branch_kept(self) -> None:
        """Verify the ``else:`` branch of a TYPE_CHECKING guard is included."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": (
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    x = 1\n"
                "else:\n"
                "    from pkg import b\n"
            ),
            "pkg/b.py": "from pkg import a\n",  # noqa: SLD306
        }
        edges = _extract(files)
        a_edges = next(e for e in edges if e.importer == PKG_FIRST)
        assert_that(PKG_SECOND in a_edges.targets, equal_to(True))


class TestExtractGraphBasics(unittest.TestCase):
    """Module-resolution and edge-extraction edge cases."""

    def test_relative_import_in_module(self) -> None:
        """Verify ``from .y import z`` resolves relative to the file's package."""
        files = {
            "pkg/__init__.py": "",
            "pkg/sub/__init__.py": "",
            "pkg/sub/a.py": "from .b import thing\n",
            "pkg/sub/b.py": "thing = 1\n",
        }
        edges = _extract(files)
        a_edges = next(e for e in edges if e.importer == "pkg.sub.a")
        assert_that("pkg.sub.b" in a_edges.targets, equal_to(True))

    def test_relative_import_in_init(self) -> None:
        """Verify ``from . import X`` in an ``__init__.py`` targets siblings."""
        files = {
            "pkg/__init__.py": "from . import a\n",
            "pkg/a.py": "",
        }
        edges = _extract(files)
        init_edges = next(e for e in edges if e.importer == "pkg")
        assert_that(PKG_FIRST in init_edges.targets, equal_to(True))  # noqa: SLD306

    def test_external_imports_ignored(self) -> None:
        """Verify imports of names outside the workspace are not in the graph."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "import os\nfrom typing import Any\n",
        }
        edges = _extract(files)
        a_edges = next(e for e in edges if e.importer == PKG_FIRST)
        assert_that(a_edges.targets, has_length(0))

    def test_syntax_error_file_skipped(self) -> None:
        """Verify a file with a syntax error is silently skipped."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "def broken(\n",
            "pkg/b.py": "",
        }
        edges = _extract(files)
        importers = {e.importer for e in edges}
        assert_that(PKG_FIRST in importers, equal_to(False))
        assert_that(PKG_SECOND in importers, equal_to(True))

    def test_star_import_skipped(self) -> None:
        """Verify ``from X import *`` does not synthesize an edge to ``X.*``."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "from pkg.b import *\n",
            "pkg/b.py": "",
        }
        edges = _extract(files)
        a_edges = next(e for e in edges if e.importer == PKG_FIRST)
        assert_that(PKG_SECOND in a_edges.targets, equal_to(True))


class TestEmptyWorkspace(unittest.TestCase):
    """The scanner on workspaces with no Python files."""

    def test_no_files_no_diagnostics(self) -> None:
        """Verify an empty workspace produces no diagnostics."""
        rows = _scan({"README.txt": "hello"})
        assert_that(rows, equal_to([]))
