# Iterate Python source files under a workspace root, honoring .gitignore.

from __future__ import annotations

from typing import Iterator, Protocol

import pathspec
from pathspec.patterns.gitignore.basic import GitIgnoreBasicPattern


class FileSystem(Protocol):
    """Filesystem operations the walker depends on."""

    def walk(self, root: str) -> Iterator[str]:  # noqa: E704
        """Yield every file path beneath ``root``."""
        ...

    def read(self, path: str) -> str:  # noqa: E704
        """Return the text contents of the file at ``path``."""
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
    """
    spec = _read_gitignore(fs, root)
    for path in fs.walk(root):
        if not path.endswith(".py"):
            continue
        if spec.match_file(path):
            continue
        yield path
