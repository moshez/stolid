"""Tests for SLD83x: import-graph architectural rules."""

from __future__ import annotations

import unittest
from typing import Sequence

from hamcrest import assert_that, equal_to, has_length

from ._sld83x_shared import (
    all_to_all,
    importers_of,
    scan_codes,
    scan_to_pairs,
    targets_of,
)


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


def _cycle_files(n: int) -> dict[str, str]:
    return _cycle_imports([f"m{i}" for i in range(n)])


def _no_init_chain(n: int) -> dict[str, str]:
    files: dict[str, str] = {}
    for i in range(n):
        files[f"m{i}.py"] = f"import m{i + 1}\n" if i + 1 < n else ""
    return files


def _shallow_with_base(leaves: int) -> dict[str, str]:
    files: dict[str, str] = {"pkg/__init__.py": "", "pkg/base.py": ""}
    for i in range(leaves):
        files[f"pkg/m{i}.py"] = "from pkg import base\n"
    return files


def _mudball_ring(count: int) -> dict[str, str]:
    cycle_subs = list("abcdefgh"[:count])
    files: dict[str, str] = {"pkg/__init__.py": ""}
    for sub in cycle_subs:
        files[f"pkg/{sub}/__init__.py"] = ""
    for index, sub in enumerate(cycle_subs):
        nxt = cycle_subs[(index + 1) % len(cycle_subs)]
        files[f"pkg/{sub}/m.py"] = f"from pkg.{nxt} import m\n"
    return files


PKG_FIRST = "pkg.a"
PKG_SECOND = "pkg.b"


_COUNT_CASES: list[tuple[str, dict[str, str], str, int]] = [
    ("SLD831_at_16", _cycle_files(16), "SLD831", 1),
    ("SLD832_weight_14", _cross_pkg_cycle(count_per_sub=6), "SLD832", 1),
    ("SLD833_chain_10", _chain_imports(10), "SLD833", 1),
    ("SLD835_all_to_all_8", all_to_all(8), "SLD835", 1),
]


_ABSENT_CASES: list[tuple[str, dict[str, str], str]] = [
    ("SLD831_at_15", _cycle_files(15), "SLD831"),
    ("SLD831_dag", _chain_imports(20), "SLD831"),
    ("SLD832_weight_10", _cross_pkg_cycle(count_per_sub=4), "SLD832"),
    ("SLD832_flat_pkg", _cycle_files(12), "SLD832"),
    ("SLD833_below_min_nodes", _no_init_chain(9), "SLD833"),
    ("SLD833_shallow", _shallow_with_base(10), "SLD833"),
    ("SLD835_chain", _chain_imports(10), "SLD835"),
]


class TestRuleFiring(unittest.TestCase):
    """Each SLD83x rule fires once at its threshold."""

    def test_fires(self) -> None:
        """Verify the firing-count cases produce the expected number of diagnostics."""
        for name, files, code, count in _COUNT_CASES:
            with self.subTest(name=name):
                assert_that(scan_codes(files).count(code), equal_to(count))


class TestRuleSilence(unittest.TestCase):
    """Each SLD83x rule stays silent for its negative cases."""

    def test_silent(self) -> None:
        """Verify the absent-cases do not emit the expected diagnostic."""
        for name, files, code in _ABSENT_CASES:
            with self.subTest(name=name):
                assert_that(code in scan_codes(files), equal_to(False))


class TestSLD831Anchor(unittest.TestCase):
    """SLD831 diagnostic anchors on the package's ``__init__.py``."""

    def test_anchor(self) -> None:
        """Verify the diagnostic anchors on the package's ``__init__.py``."""
        rows = scan_to_pairs(_cycle_files(16))
        anchors = {path for path, msg in rows if "SLD831" in msg}
        assert_that(anchors, equal_to({"pkg/__init__.py"}))


class TestSLD834SubpackageMudBall(unittest.TestCase):
    """Largest SCC at quotient level covers > 60% of total module weight."""

    def test_fires_above_threshold(self) -> None:
        """Verify SLD834 fires when level-2 SCC covers > 60% of modules."""
        # 8 subpackages in a ring cycle at level 2, plus 4 unrelated
        # subpackages. Level 2 nodes: 8 + 4 + 1 = 13 (>= 10). SCC weight =
        # 16, total weight = 24, fraction = 67%.
        files = _mudball_ring(8)
        for sub in ("p", "q", "r", "s"):
            files[f"pkg/{sub}/__init__.py"] = ""
            files[f"pkg/{sub}/m.py"] = ""
        assert_that(scan_codes(files).count("SLD834"), equal_to(1))

    def test_silent_when_scc_small(self) -> None:
        """Verify SLD834 is silent when no SCC covers a majority."""
        files: dict[str, str] = {"pkg/__init__.py": ""}
        for sub in ("aa", "bb", "cc", "dd", "ee", "ff"):
            files[f"pkg/{sub}/__init__.py"] = ""
            for i in range(2):
                files[f"pkg/{sub}/m{i}.py"] = ""
        assert_that("SLD834" in scan_codes(files), equal_to(False))


_TYPE_CHECKING_ONLY_CYCLE = {
    "pkg/__init__.py": "",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from pkg import b\n"
    ),
    "pkg/b.py": "from pkg import a\n",
}

_RUNTIME_ELSE_BRANCH = {
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

_RELATIVE_FROM_DOT_Y = {
    "pkg/__init__.py": "",
    "pkg/sub/__init__.py": "",
    "pkg/sub/a.py": "from .b import thing\n",
    "pkg/sub/b.py": "thing = 1\n",
}

_RELATIVE_FROM_DOT_IN_INIT = {
    "pkg/__init__.py": "from . import a\n",
    "pkg/a.py": "",
}

_EXTERNAL_IMPORTS_ONLY = {
    "pkg/__init__.py": "",
    "pkg/a.py": "import os\nfrom typing import Any\n",
}

_STAR_IMPORT = {
    "pkg/__init__.py": "",
    "pkg/a.py": "from pkg.b import *\n",
    "pkg/b.py": "",
}


_TARGET_PRESENT_CASES: list[tuple[str, dict[str, str], str, str]] = [
    ("runtime_else_branch", _RUNTIME_ELSE_BRANCH, PKG_FIRST, PKG_SECOND),
    ("relative_from_dot_y", _RELATIVE_FROM_DOT_Y, "pkg.sub.a", "pkg.sub.b"),
    ("relative_from_dot_init", _RELATIVE_FROM_DOT_IN_INIT, "pkg", PKG_FIRST),
    ("star_import_keeps_module", _STAR_IMPORT, PKG_FIRST, PKG_SECOND),
]


class TestTargetResolution(unittest.TestCase):
    """``targets_of`` resolves every documented edge form."""

    def test_target_present(self) -> None:
        """Verify each case lists the expected target in the importer's edges."""
        for name, files, importer, expected in _TARGET_PRESENT_CASES:
            with self.subTest(name=name):
                assert_that(expected in targets_of(files, importer), equal_to(True))

    def test_external_imports_ignored(self) -> None:
        """Verify imports of names outside the workspace are not in the graph."""
        assert_that(targets_of(_EXTERNAL_IMPORTS_ONLY, PKG_FIRST), has_length(0))

    def test_type_checking_only_cycle_silent(self) -> None:
        """Verify a TYPE_CHECKING-only back-edge does not create an SLD831 cycle."""
        assert_that("SLD831" in scan_codes(_TYPE_CHECKING_ONLY_CYCLE), equal_to(False))

    def test_syntax_error_file_skipped(self) -> None:
        """Verify a file with a syntax error is silently skipped."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "def broken(\n",
            "pkg/b.py": "",
        }
        importers = importers_of(files)
        assert_that(PKG_FIRST in importers, equal_to(False))
        assert_that(PKG_SECOND in importers, equal_to(True))


class TestEmptyWorkspace(unittest.TestCase):
    """The scanner on workspaces with no Python files."""

    def test_no_files_no_diagnostics(self) -> None:
        """Verify an empty workspace produces no diagnostics."""
        rows = scan_to_pairs({"README.txt": "hello"})
        assert_that(rows, equal_to([]))
