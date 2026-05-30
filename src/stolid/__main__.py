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
        """Yield every file path under ``root`` (os.walk-based).

        Args:
            root: The directory to walk recursively.

        Yields:
            Each file path found under ``root``.
        """
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                yield os.path.join(dirpath, name)

    def read(self, path: str) -> str:  # noqa: SLD303
        """Return the UTF-8 text contents of the file at ``path``.

        Args:
            path: The path to the file to read.

        Returns:
            The text contents of the file.
        """
        with open(path, encoding="utf-8") as handle:
            return handle.read()


@dataclass(frozen=True, slots=True, kw_only=True)
class _RealRunner:
    def run(self, argv: Sequence[str]) -> int:  # noqa: SLD303
        """Run subprocess with ``argv`` and return its exit code.

        Args:
            argv: The command and its arguments to execute.

        Returns:
            The exit code of the subprocess.
        """
        return subprocess.call(list(argv))


@dataclass(frozen=True, slots=True, kw_only=True)
class _RealSink:
    def stdout(self, line: str) -> None:  # noqa: SLD303
        """Print ``line`` to standard output.

        Args:
            line: The text to print.
        """
        print(line)

    def stderr(self, line: str) -> None:  # noqa: SLD303
        """Print ``line`` to standard error.

        Args:
            line: The text to print.
        """
        print(line, file=sys.stderr)


def main() -> int:
    """Run stolid as ``python -m stolid``; returns the merged exit code.

    Returns:
        The merged exit code across all scan stages.
    """
    invocation = parse_argv(sys.argv[1:])
    return run_stolid(
        runner=_RealRunner(),
        fs=_RealFileSystem(),
        sink=_RealSink(),
        invocation=invocation,
    )


if __name__ == "__main__":
    sys.exit(main())
