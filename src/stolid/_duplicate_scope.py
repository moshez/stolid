# Scope tracking for duplicate-detector name normalization.
#
# Maintains a stack of binding frames. Each frame records the bindings created
# in a function, lambda, or comprehension, in order of first appearance. A
# ``Name`` is normalized to one of three forms:
#
# - ``$n`` if it is bound in the current frame (positional placeholder).
# - ``^d.$n`` if it is bound in an enclosing frame ``d`` levels up.
# - the raw identifier otherwise (free name; globals, builtins, imports).

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass(frozen=True, slots=True, kw_only=True)
class Frame:
    """A binding frame for a function, lambda, or comprehension."""

    _bindings: dict[str, int] = field(default_factory=dict)

    def add(self, name: str) -> None:
        """Record ``name`` in this frame, assigning it the next positional slot."""
        if name not in self._bindings:
            self._bindings[name] = len(self._bindings)

    def position(self, name: str) -> int | None:
        """Return ``name``'s positional slot in this frame, or ``None`` if unbound."""
        return self._bindings.get(name)


@dataclass(frozen=True, slots=True, kw_only=True)
class ScopeStack:
    """Stack of frames, supporting enter/exit and name lookup."""

    _frames: list[Frame] = field(default_factory=list)

    def enter(self, frame: Frame) -> None:
        """Push ``frame`` onto the stack as the new innermost scope."""
        self._frames.append(frame)

    def exit(self) -> None:
        """Pop the innermost frame, restoring the prior scope."""
        self._frames.pop()

    def normalize(self, name: str) -> str:
        """Return the normalized form of ``name`` relative to this stack."""
        if not self._frames:
            return name
        current_pos = self._frames[-1].position(name)
        if current_pos is not None:
            return f"${current_pos}"
        for depth, frame in enumerate(_enclosing(self._frames), start=1):
            pos = frame.position(name)
            if pos is not None:
                return f"^{depth}.${pos}"
        return name


def _enclosing(stack: list[Frame]) -> Iterator[Frame]:
    for frame in reversed(stack[:-1]):
        yield frame
