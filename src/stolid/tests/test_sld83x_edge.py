"""Edge-case tests for the SLD83x scanner and its extraction helpers."""

from __future__ import annotations

import textwrap
import unittest
from typing import Mapping

from hamcrest import assert_that, equal_to, has_length

from .._duplicate_cli import run_stolid
from .._import_graph_extract import anchor_for_prefix, extract_graph
from .._import_graph_scan import scan_paths
from .fakes import CapturedSink, FixedRunner, InMemoryFileSystem

PKG_FIRST = "pkg.a"
PKG_SECOND = "pkg.b"


def _dedent(files: Mapping[str, str]) -> Mapping[str, str]:
    return {
        path: textwrap.dedent(source).lstrip("\n") for path, source in files.items()
    }


def _scan_files(files: Mapping[str, str]) -> list[tuple[str, str]]:
    fs = InMemoryFileSystem(_files=_dedent(files))
    return [(line.path, line.message) for line in scan_paths(fs, ["."])]


class TestTypeCheckingForms(unittest.TestCase):
    """Verifying the different syntactic spellings of ``TYPE_CHECKING``."""

    def test_attribute_form_excluded(self) -> None:
        """Verify ``if typing.TYPE_CHECKING:`` imports are excluded from edges."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": (
                "import typing\n" "if typing.TYPE_CHECKING:\n" "    from pkg import b\n"
            ),
            "pkg/b.py": "",
        }
        fs = InMemoryFileSystem(_files=_dedent(files))
        edges = extract_graph(fs, ["."])
        a_edges = next(e for e in edges if e.importer == PKG_FIRST)
        assert_that(a_edges.targets, has_length(0))

    def test_non_type_checking_if_kept(self) -> None:
        """Verify ``if SOMETHING_ELSE:`` does not exclude the imports."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "if True:\n    from pkg import b\n",
            "pkg/b.py": "",
        }
        fs = InMemoryFileSystem(_files=_dedent(files))
        edges = extract_graph(fs, ["."])
        a_edges = next(e for e in edges if e.importer == PKG_FIRST)
        assert_that(PKG_SECOND in a_edges.targets, equal_to(True))


class TestModuleNameResolution(unittest.TestCase):
    """Verifying module-name derivation from a file path."""

    def test_top_level_init_skipped(self) -> None:
        """Verify a bare ``__init__.py`` at the workspace root has no module name."""
        files = {"__init__.py": "x = 1\n"}
        fs = InMemoryFileSystem(_files=_dedent(files))
        edges = extract_graph(fs, ["."])
        assert_that(edges, equal_to([]))

    def test_self_import_dropped(self) -> None:
        """Verify ``import pkg.a`` inside ``pkg/a.py`` is dropped (self-loop)."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "import pkg.a\n",
        }
        fs = InMemoryFileSystem(_files=_dedent(files))
        edges = extract_graph(fs, ["."])
        a_edges = next(e for e in edges if e.importer == PKG_FIRST)
        assert_that(a_edges.targets, has_length(0))

    def test_top_level_module_no_package(self) -> None:
        """Verify a ``.py`` file outside any package becomes a bare module."""
        files = {"script.py": "import other\n", "other.py": ""}
        fs = InMemoryFileSystem(_files=_dedent(files))
        edges = extract_graph(fs, ["."])
        names = {e.importer for e in edges}
        assert_that(names, equal_to({"script", "other"}))


class TestRelativeImportTooDeep(unittest.TestCase):
    """``from ... import X`` past the package root is dropped silently."""

    def test_excess_dots_resolve_to_nothing(self) -> None:
        """Verify a relative import past the root produces no edge."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "from ... import x\n",
            "pkg/x.py": "",
        }
        fs = InMemoryFileSystem(_files=_dedent(files))
        edges = extract_graph(fs, ["."])
        a_edges = next(e for e in edges if e.importer == PKG_FIRST)
        assert_that("pkg.x" in a_edges.targets, equal_to(False))

    def test_from_dot_in_top_module_skipped(self) -> None:
        """Verify ``from . import x`` in a top-level module resolves to nothing."""
        files = {
            "top.py": "from . import other\n",
            "other.py": "",
        }
        fs = InMemoryFileSystem(_files=_dedent(files))
        edges = extract_graph(fs, ["."])
        top = next(e for e in edges if e.importer == "top")
        assert_that(top.targets, has_length(0))


class TestAnchorForPrefix(unittest.TestCase):
    """Verifying ``anchor_for_prefix`` over a few module layouts."""

    def test_prefix_with_only_module_files(self) -> None:
        """Verify the lexicographically-first module file is the fallback."""
        files = {
            "top1.py": "",
            "top2.py": "import top1\n",
        }
        fs = InMemoryFileSystem(_files=_dedent(files))
        edges = extract_graph(fs, ["."])
        # Empty prefix matches everything; no __init__ exists, so fallback.
        anchor = anchor_for_prefix("", edges)
        assert_that(anchor, equal_to("top1.py"))

    def test_modules_outside_prefix_skipped(self) -> None:
        """Verify ``anchor_for_prefix`` ignores modules outside the prefix."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "",
            "other.py": "",
        }
        fs = InMemoryFileSystem(_files=_dedent(files))
        edges = extract_graph(fs, ["."])
        anchor = anchor_for_prefix("pkg", edges)
        assert_that(anchor, equal_to("pkg/__init__.py"))

    def test_descendant_init_preferred_over_sibling_modules(self) -> None:
        """Verify ``__init__.py`` paths win over plain module files."""
        files = {
            "pkg/__init__.py": "",
            "pkg/a.py": "",
            "pkg/sub/__init__.py": "",
            "pkg/sub/b.py": "",
        }
        fs = InMemoryFileSystem(_files=_dedent(files))
        edges = extract_graph(fs, ["."])
        anchor = anchor_for_prefix("pkg", edges)
        assert_that(anchor, equal_to("pkg/__init__.py"))


class TestSLD834SilentFraction(unittest.TestCase):
    """SLD834 silent when level has ≥ 10 nodes but no SCC dominates."""

    def test_many_subpackages_no_majority_scc(self) -> None:
        """Verify SLD834 is silent when ≥ 10 subpackages have no dominant SCC."""
        files: dict[str, str] = {"pkg/__init__.py": ""}
        for sub in "abcdefghij":
            files[f"pkg/{sub}/__init__.py"] = ""
            files[f"pkg/{sub}/m.py"] = ""
        # 11 level-2 nodes (pkg + 10 subs); no SCC at level 2.
        codes = [msg.split()[0] for _, msg in _scan_files(files)]
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
        rows = _scan_files(files)
        anchors = {path for path, msg in rows if "SLD831" in msg}
        assert_that(anchors, equal_to({"pkg/__init__.py"}))


class TestFirstInitFallback(unittest.TestCase):
    """``_first_init`` falls back when no ``__init__.py`` exists."""

    def test_density_diagnostic_with_only_modules(self) -> None:
        """Verify SLD835 anchors on a module file when no init is present."""
        stems = [f"m{i}" for i in range(8)]
        files: dict[str, str] = {}
        for s in stems:
            others = [other for other in stems if other != s]
            files[f"{s}.py"] = "".join(f"import {o}\n" for o in others)
        rows = _scan_files(files)
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
        fs = InMemoryFileSystem(_files=_dedent(files))
        runner = FixedRunner(_exit_code=0)
        sink = CapturedSink()
        exit_code = run_stolid(runner=runner, fs=fs, sink=sink, paths=["."])
        assert_that(exit_code, equal_to(1))
        out_codes = [line for line in sink.out if "SLD831" in line]
        assert_that(out_codes, has_length(1))
