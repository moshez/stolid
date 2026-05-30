"""``python -m stolid`` entry point.

Runs flake8 first, then the cross-file duplicate scanner. Exits with the
maximum exit code of the two stages. Contains only boundary glue; the
testable logic lives in :mod:`stolid._duplicate_cli`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterator, Sequence

from .cli import parse_argv, run_stolid


@dataclass(frozen=True, slots=True, kw_only=True)
class _RealFileSystem:
    def walk(self, root: str) -> Iterator[str]:  # noqa: SLD303
        """Yield every file path under ``root`` (os.walk-based)."""
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                yield os.path.join(dirpath, name)

    def read(self, path: str) -> str:  # noqa: SLD303
        """Return the UTF-8 text contents of the file at ``path``."""
        with open(path, encoding="utf-8") as handle:
            return handle.read()


@dataclass(frozen=True, slots=True, kw_only=True)
class _RealRunner:
    def run(self, argv: Sequence[str]) -> int:  # noqa: SLD303
        """Run subprocess with ``argv`` and return its exit code."""
        return subprocess.call(list(argv))


@dataclass(frozen=True, slots=True, kw_only=True)
class _RealSink:
    def stdout(self, line: str) -> None:  # noqa: SLD303
        """Print ``line`` to standard output."""
        print(line)

    def stderr(self, line: str) -> None:  # noqa: SLD303
        """Print ``line`` to standard error."""
        print(line, file=sys.stderr)


def main() -> int:
    """Run stolid as ``python -m stolid``; returns the merged exit code."""
    invocation = parse_argv(sys.argv[1:])
    return run_stolid(
        runner=_RealRunner(),
        fs=_RealFileSystem(),
        sink=_RealSink(),
        invocation=invocation,
    )


if __name__ == "__main__":
    sys.exit(main())
