# Iterate Python source files under a workspace root, honoring .gitignore.

from __future__ import annotations

from typing import Iterator, Protocol

import pathspec
from pathspec.patterns.gitignore.basic import GitIgnoreBasicPattern


class FileSystem(Protocol):
    """Filesystem operations the walker depends on."""

    def walk(self, root: str) -> Iterator[str]:
        """Yield every file path beneath ``root``.

        Args:
            root: The directory path to walk recursively.

        Returns:
            An iterator of file paths found beneath ``root``.
        """
        ...

    def read(self, path: str) -> str:
        """Return the text contents of the file at ``path``.

        Args:
            path: The file path to read.

        Returns:
            The full text contents of the file.
        """
        ...


def _join(root: str, name: str) -> str:
    if root in ("", "."):  # noqa: SLD304
        return name
    if root.endswith("/"):
        return root + name
    return f"{root}/{name}"


def _read_gitignore(
    fs: FileSystem, root: str
) -> pathspec.PathSpec[GitIgnoreBasicPattern]:
    try:
        text = fs.read(_join(root, ".gitignore"))
    except FileNotFoundError:
        text = ""
    return pathspec.PathSpec.from_lines("gitignore", text.splitlines())


def iter_python_files(fs: FileSystem, root: str) -> Iterator[str]:
    """Yield ``.py`` file paths under ``root`` not matched by its ``.gitignore``.

    Uses ``fs`` to walk the tree and read any ``.gitignore`` it finds.

    Args:
        fs: The filesystem abstraction used to walk and read files.
        root: The directory path to search for Python files.

    Yields:
        Each ``.py`` file path under ``root`` not excluded by ``.gitignore``.
    """
    spec = _read_gitignore(fs, root)
    for path in fs.walk(root):
        if not path.endswith(".py"):
            continue
        if spec.match_file(path):
            continue
        yield path
