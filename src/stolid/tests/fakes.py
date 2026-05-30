"""In-memory test doubles for stolid's duplicate-detector tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, Mapping, MutableSequence, Sequence


@dataclass(frozen=True, slots=True, kw_only=True)
class InMemoryFileSystem:
    """A virtual filesystem keyed by path string."""

    _files: Mapping[str, str]

    def walk(self, root: str) -> Iterator[str]:
        """Yield every stored path beneath ``root``.

        Args:
            root: The directory prefix to filter paths by.

        Yields:
            Each stored path that starts with ``root``.
        """
        prefix = "" if root in ("", ".") else root.rstrip("/") + "/"  # noqa: SLD304
        for path in self._files:
            if not prefix or path.startswith(prefix):
                yield path

    def read(self, path: str) -> str:
        """Return the stored contents of ``path`` or raise ``FileNotFoundError``.

        Args:
            path: The filesystem path to look up.

        Returns:
            The source text stored at ``path``.

        Raises:
            FileNotFoundError: If ``path`` is not in the virtual filesystem.
        """
        if path not in self._files:
            raise FileNotFoundError(path)
        return self._files[path]


@dataclass(frozen=True, slots=True, kw_only=True)
class FixedRunner:
    """A CommandRunner that returns a preset exit code and records its argv.

    The ``calls`` list captures every ``argv`` passed to :meth:`run`.

    Attributes:
        calls: Each ``argv`` passed to :meth:`run`, in order.
    """

    _exit_code: int
    calls: MutableSequence[Sequence[str]] = field(default_factory=list)

    def run(self, argv: Iterable[str]) -> int:
        """Record ``argv`` in ``self.calls`` and return the preset exit code.

        Args:
            argv: The command-line arguments to record.

        Returns:
            The preset exit code.
        """
        self.calls.append(list(argv))
        return self._exit_code


@dataclass(frozen=True, slots=True, kw_only=True)
class CapturedSink:
    """An OutputSink that records stdout and stderr lines.

    Field ``out`` collects stdout lines; ``err`` collects stderr lines.

    Attributes:
        out: Lines written to stdout.
        err: Lines written to stderr.
    """

    out: MutableSequence[str] = field(default_factory=list)
    err: MutableSequence[str] = field(default_factory=list)

    def stdout(self, line: str) -> None:  # noqa: SLD303
        """Append ``line`` to ``self.out``.

        Args:
            line: The stdout line to record.
        """
        self.out.append(line)

    def stderr(self, line: str) -> None:  # noqa: SLD303
        """Append ``line`` to ``self.err``.

        Args:
            line: The stderr line to record.
        """
        self.err.append(line)
