"""Edge-case tests for the SLD83x scanner and its extraction helpers."""

from __future__ import annotations

import unittest
from typing import Mapping

from hamcrest import assert_that, equal_to, has_length

from .._duplicate_cli import run_stolid
from .._import_graph_extract import anchor_for_prefix
from ._sld83x_shared import (
    all_to_all,
    extract_edges,
    importers_of,
    scan_to_pairs,
    targets_of,
)
from .code_parser import dedent_files
from .fakes import CapturedSink, FixedRunner, InMemoryFileSystem

PKG_FIRST = "pkg.a"
PKG_SECOND = "pkg.b"


def _anchor_of(files: Mapping[str, str], prefix: str) -> str:
    return anchor_for_prefix(prefix, extract_edges(files))


_TYPING_DOTTED_GUARD = {
    "pkg/__init__.py": "",
    "pkg/a.py": (
        "import typing\n" "if typing.TYPE_CHECKING:\n" "    from pkg import b\n"
    ),
    "pkg/b.py": "",
}

_NON_TYPE_CHECKING_IF = {
    "pkg/__init__.py": "",
    "pkg/a.py": "if True:\n    from pkg import b\n",
    "pkg/b.py": "",
}

_SELF_IMPORT = {
    "pkg/__init__.py": "",
    "pkg/a.py": "import pkg.a\n",
}

_RELATIVE_TOO_DEEP = {
    "pkg/__init__.py": "",
    "pkg/a.py": "from ... import x\n",
    "pkg/x.py": "",
}

_TOP_LEVEL_RELATIVE = {
    "top.py": "from . import other\n",
    "other.py": "",
}


_EMPTY_TARGETS_CASES: list[tuple[str, dict[str, str], str]] = [
    ("typing_dotted_guard", _TYPING_DOTTED_GUARD, PKG_FIRST),
    ("self_import", _SELF_IMPORT, PKG_FIRST),
    ("top_level_relative", _TOP_LEVEL_RELATIVE, "top"),
]


class TestEmptyTargetCases(unittest.TestCase):
    """Cases where the resolved import set should be empty."""

    def test_empty(self) -> None:
        """Verify each case's importer has zero workspace targets."""
        for name, files, importer in _EMPTY_TARGETS_CASES:
            with self.subTest(name=name):
                assert_that(targets_of(files, importer), has_length(0))


class TestTargetInclusion(unittest.TestCase):
    """Cases where a specific module must appear in the importer's targets."""

    def test_non_type_checking_if_kept(self) -> None:
        """Verify ``if SOMETHING_ELSE:`` does not exclude the imports."""
        targets = targets_of(_NON_TYPE_CHECKING_IF, PKG_FIRST)
        assert_that(PKG_SECOND in targets, equal_to(True))

    def test_excess_dots_resolve_to_nothing(self) -> None:
        """Verify a relative import past the root produces no edge."""
        targets = targets_of(_RELATIVE_TOO_DEEP, PKG_FIRST)
        assert_that("pkg.x" in targets, equal_to(False))


class TestModuleNameResolution(unittest.TestCase):
    """Verifying module-name derivation from a file path."""

    def test_top_level_init_skipped(self) -> None:
        """Verify a bare ``__init__.py`` at the workspace root has no module name."""
        files = {"__init__.py": "x = 1\n"}
        assert_that(extract_edges(files), equal_to([]))

    def test_top_level_module_no_package(self) -> None:
        """Verify a ``.py`` file outside any package becomes a bare module."""
        files = {"script.py": "import other\n", "other.py": ""}
        assert_that(importers_of(files), equal_to(frozenset({"script", "other"})))


class TestAnchorForPrefix(unittest.TestCase):
    """Verifying ``anchor_for_prefix`` over a few module layouts."""

    def test_prefix_with_only_module_files(self) -> None:
        """Verify the lexicographically-first module file is the fallback."""
        files = {
            "top1.py": "",
            "top2.py": "import top1\n",
        }
        # Empty prefix matches everything; no __init__ exists, so fallback.
        assert_that(_anchor_of(files, ""), equal_to("top1.py"))

    def test_modules_outside_prefix_skipped(self) -> None:
        """Verify ``anchor_for_prefix`` ignores modules outside the prefix."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "",
            "other.py": "",
        }
        assert_that(_anchor_of(files, "pkg"), equal_to("pkg/__init__.py"))

    def test_descendant_init_preferred_over_sibling_modules(self) -> None:
        """Verify ``__init__.py`` paths win over plain module files."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "",
            "pkg/sub/__init__.py": "",
            "pkg/sub/b.py": "",
        }
        assert_that(_anchor_of(files, "pkg"), equal_to("pkg/__init__.py"))


class TestSLD834SilentFraction(unittest.TestCase):
    """SLD834 silent when level has ≥ 10 nodes but no SCC dominates."""

    def test_many_subpackages_no_majority_scc(self) -> None:
        """Verify SLD834 is silent when ≥ 10 subpackages have no dominant SCC."""
        files: dict[str, str] = {"pkg/__init__.py": ""}
        for sub in "abcdefghij":
            files[f"pkg/{sub}/__init__.py"] = ""
            files[f"pkg/{sub}/m.py"] = ""
        # 11 level-2 nodes (pkg + 10 subs); no SCC at level 2.
        codes = [msg.split()[0] for _, msg in scan_to_pairs(files)]
        assert_that("SLD834" in codes, equal_to(False))


class TestSCCAnchorEdgeCases(unittest.TestCase):
    """Anchor selection for SCCs whose members share a non-trivial prefix."""

    def test_scc_with_init_and_descendant(self) -> None:
        """Verify an SCC of ``pkg`` and a descendant anchors on the init."""
        # Build a tight cycle where the package itself imports a deeply
        # nested module that imports back, with enough mass to trip SLD831.
        files: dict[str, str] = {"pkg/__init__.py": "from pkg import m0\n"}
        # All m_i import next and import back to pkg via __init__ chain.
        for i in range(16):
            nxt = (i + 1) % 16
            files[f"pkg/m{i}.py"] = f"from pkg import m{nxt}\n"
        rows = scan_to_pairs(files)
        anchors = {path for path, msg in rows if "SLD831" in msg}
        assert_that(anchors, equal_to({"pkg/__init__.py"}))


class TestFirstInitFallback(unittest.TestCase):
    """``_first_init`` falls back when no ``__init__.py`` exists."""

    def test_density_diagnostic_with_only_modules(self) -> None:
        """Verify SLD835 anchors on a module file when no init is present."""
        rows = scan_to_pairs(all_to_all(8, prefix=""))
        sld835 = [(path, msg) for path, msg in rows if "SLD835" in msg]
        assert_that(sld835, has_length(1))
        assert_that(sld835[0][0], equal_to("m0.py"))


class TestCLIIntegrationExitCode(unittest.TestCase):
    """``run_stolid`` exit code merges in the SLD83x scan result."""

    def test_import_graph_violation_emitted_on_stdout(self) -> None:
        """Verify SLD83x diagnostics flow through ``sink.stdout`` with exit 1."""
        stems = [f"m{i}" for i in range(16)]
        files: dict[str, str] = {"pkg/__init__.py": ""}
        for index, s in enumerate(stems):
            nxt = stems[(index + 1) % len(stems)]
            files[f"pkg/{s}.py"] = f"from pkg import {nxt}\n"
        fs = InMemoryFileSystem(_files=dedent_files(files))
        runner = FixedRunner(_exit_code=0)
        sink = CapturedSink()
        exit_code = run_stolid(runner=runner, fs=fs, sink=sink, paths=["."])
        assert_that(exit_code, equal_to(1))
        out_codes = [line for line in sink.out if "SLD831" in line]
        assert_that(out_codes, has_length(1))
