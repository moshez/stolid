"""In-memory test doubles for stolid's duplicate-detector tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass(frozen=True, slots=True, kw_only=True)
class InMemoryFileSystem:
    """A virtual filesystem keyed by path string."""

    _files: dict[str, str]

    def walk(self, root: str) -> Iterator[str]:
        """Yield every stored path beneath ``root``."""
        prefix = "" if root in ("", ".") else root.rstrip("/") + "/"  # noqa: SLD304
        for path in self._files:
            if not prefix or path.startswith(prefix):
                yield path

    def read(self, path: str) -> str:
        """Return the stored contents of ``path`` or raise ``FileNotFoundError``."""
        if path not in self._files:
            raise FileNotFoundError(path)
        return self._files[path]


@dataclass(frozen=True, slots=True, kw_only=True)
class FixedRunner:
    """A CommandRunner that returns a preset exit code and records its argv.

    The ``calls`` list captures every ``argv`` passed to :meth:`run`.
    """

    _exit_code: int
    calls: list[list[str]] = field(default_factory=list)

    def run(self, argv: list[str]) -> int:
        """Record ``argv`` in ``self.calls`` and return the preset exit code."""
        self.calls.append(list(argv))
        return self._exit_code


@dataclass(frozen=True, slots=True, kw_only=True)
class CapturedSink:
    """An OutputSink that records stdout and stderr lines.

    Field ``out`` collects stdout lines; ``err`` collects stderr lines.
    """

    out: list[str] = field(default_factory=list)
    err: list[str] = field(default_factory=list)

    def stdout(self, line: str) -> None:  # noqa: SLD303
        """Append ``line`` to ``self.out``."""
        self.out.append(line)

    def stderr(self, line: str) -> None:  # noqa: SLD303
        """Append ``line`` to ``self.err``."""
        self.err.append(line)
