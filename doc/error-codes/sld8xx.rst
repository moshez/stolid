SLD8xx - Cross-File Contracts, Documentation, and Architecture
======================================================================

The 800-series checks are split into three groups that each require
a workspace-wide view: cross-file public contracts (SLD80x),
documentation symmetry (SLD81x / SLD82x), and the runtime import
graph (SLD83x).

SLD80x - Cross-File Public Contracts
----------------------------------------------------------------------

SLD80x are **cross-file** checks: they require a workspace-wide view and
therefore do not run as part of the flake8 plugin. They are emitted by the
``python -m stolid`` runner, which scans every ``.py`` file under the
given paths (honoring ``.gitignore``) and then re-walks each file to
classify every public annotation against the workspace symbol table.

A public annotation may only name a contract (``Protocol``, ``ABC``,
``TypedDict``, ``NamedTuple``, ``Enum``, or a data-only ``@dataclass``),
a primitive (``int``, ``str``, ``bool``, ...), or compose those through
an abstract container from ``collections.abc`` / ``typing`` (``Mapping``,
``Sequence``, ``Iterable``, ...) or a union. Naming an open concrete
class commits callers to that exact type; the rule rejects it so that
implementations stay swappable behind their contracts.

A "data-only ``@dataclass``" is a ``@dataclass``-decorated class whose
body declares only public annotated fields (optionally with a
docstring): no methods, no private (``_``-prefixed) fields. Such a class
is a pure record -- its annotations *are* its contract -- so callers may
safely depend on it, assuming the field types are themselves allowed.

"Public" surface here is decided by *name*, not by the module a
definition lives in: top-level functions, public classes and their
public methods, and public class-level fields whose names do not start
with a single underscore. A public-named definition is on the contract
surface **even inside a private (``_``-prefixed) module** — callers can
still import and depend on it, so its annotations are still a commitment.
Only private *members* (``_``-prefixed functions, classes, fields, and
members nested in public classes) are skipped.

This is deliberately stricter than the module-based privacy used by the
documentation checks below (SLD81x / SLD82x): a private module exempts
its members from *docstring* requirements, but not from the public
*contract*. If a function in a private module should be free to name
concrete types, give it a ``_``-prefixed name so it is genuinely
private.

Diagnostics honor per-line ``# noqa`` markers exactly like SLD801.

**SLD802**: Public annotation references a workspace-defined concrete
class. A concrete class is any ``class X:`` that is not a Protocol, ABC,
TypedDict, NamedTuple, Enum, or data-only ``@dataclass``. Names that are
not defined anywhere in the scanned workspace are treated as
out-of-scope third-party references and are silently allowed.

.. code-block:: python

    # Bad: backend.py
    from dataclasses import dataclass

    @dataclass(frozen=True, slots=True, kw_only=True)
    class RealBackend:
        name: str

        def fetch(self, key: str) -> bytes: ...

    # api.py
    from .backend import RealBackend

    def run(b: RealBackend) -> None: ...

    # Good: backend.py
    from typing import Protocol

    class Backend(Protocol):
        def fetch(self, key: str) -> bytes: ...

    # api.py
    from .backend import Backend

    def run(b: Backend) -> None: ...

**SLD803**: Public annotation uses a concrete builtin container
(``list``, ``dict``, ``set``, ``frozenset``). Use ``Mapping``,
``Sequence``, ``AbstractSet``, ``Iterable``, or another abstract from
``collections.abc`` / ``typing`` -- callers should commit to the
operations they need, not to the concrete container that produces them.

.. code-block:: python

    # Bad
    def collect(items: list[str], counts: dict[str, int]) -> set[str]: ...

    # Good
    from typing import Iterable, Mapping, AbstractSet

    def collect(
        items: Iterable[str], counts: Mapping[str, int]
    ) -> AbstractSet[str]: ...

**SLD804**: Public annotation uses a variadic tuple (``tuple[X, ...]``).
A variadic tuple is a homogeneous, indefinitely-long sequence; express
that with ``Sequence[X]`` or ``Iterable[X]``. Fixed-arity tuples
(``tuple[int, str]``) are fine -- they describe a precise structure.

.. code-block:: python

    # Bad
    def pack(xs: tuple[int, ...]) -> None: ...

    # Good
    from typing import Sequence

    def pack(xs: Sequence[int]) -> None: ...

SLD81x / SLD82x - Documentation
----------------------------------------------------------------------

stolid takes a strict, symmetric view of docstrings:

- Public surfaces **must** carry a docstring (SLD81x).
- Private surfaces **must not** carry a docstring — implementation notes
  belong in ``#`` comments (SLD82x).

A module is public when its filename does not start with a single
underscore (``__init__.py`` is treated as public because the package
itself usually is). A class, function, or method is public when its
name does not start with an underscore. Dunder names (``__str__``,
``__eq__``, ...) are exempt from both policies: they implement
protocols, not API. Inner functions — functions defined inside another
function — are also exempt, regardless of name. The content checks
(SLD814/SLD815/SLD816) apply only once a docstring is present.

**SLD811**: Public module missing a module docstring. Add a top-level
string literal as the first statement.

.. code-block:: python

    # Bad
    import os

    x = 1

    # Good
    """Brief description of this module."""

    import os

    x = 1

**SLD812**: Public class missing a docstring (applies even when the
class lives in a private module).

.. code-block:: python

    # Bad
    class Reporter:
        ...

    # Good
    class Reporter:
        """Render diagnostic lines for the duplicate scanner."""

**SLD813**: Public function or method missing a docstring (applies even
inside a private module or private class). Inner functions never need
one.

.. code-block:: python

    # Bad
    def parse(source):
        ...

    # Good
    def parse(source):
        """Parse ``source`` and return an AST."""
        ...

**SLD814**: Function docstring does not mention an argument by name.
Types are documented via mypy; the docstring describes the semantics of
each parameter. ``self`` and ``cls`` are exempt.

.. code-block:: python

    # Bad
    def add(a: int, b: int) -> int:
        """Add things and return the result."""
        return a + b

    # Good
    def add(a: int, b: int) -> int:
        """Return the sum of ``a`` and ``b``."""
        return a + b

**SLD815**: Function docstring does not mention the return value. The
docstring must contain one of ``return``, ``returns``, ``yield``, or
``yields`` (case-insensitive) unless the function is annotated to return
``None`` (or has no return annotation).

.. code-block:: python

    # Bad
    def first(seq: list[int]) -> int:
        """The first element of ``seq``."""
        return seq[0]

    # Good
    def first(seq: list[int]) -> int:
        """Return the first element of ``seq``."""
        return seq[0]

**SLD816**: Dataclass docstring does not mention a non-private field.
Document every public field by name in the class docstring, or annotate
it with ``field(doc=...)`` so its documentation lives at the field
itself. Fields whose name starts with ``_`` are exempt.

.. code-block:: python

    # Bad
    @dataclass(frozen=True, slots=True, kw_only=True)
    class Point:
        """A 2D point."""

        x: int
        y: int

    # Good
    @dataclass(frozen=True, slots=True, kw_only=True)
    class Point:
        """A 2D point with coordinates ``x`` and ``y``."""

        x: int
        y: int

**SLD821**: Private module (filename starts with ``_``) has a module
docstring. Convert it to a top-of-file ``#`` comment block.

.. code-block:: python

    # Bad: _internals.py
    """Implementation details for the duplicate scanner."""

    import ast
    ...

    # Good: _internals.py
    # Implementation details for the duplicate scanner.

    import ast
    ...

**SLD822**: Private class has a docstring. Convert it to a ``#`` comment
immediately above the body (or before the ``class`` line).

.. code-block:: python

    # Bad
    class _State:
        """Traversal state for the visitor."""

        depth: int = 0

    # Good
    class _State:
        # Traversal state for the visitor.

        depth: int = 0

**SLD823**: Private function or method has a docstring. Use a ``#``
comment instead.

.. code-block:: python

    # Bad
    def _normalize(text):
        """Lowercase and strip ``text``."""
        return text.strip().lower()

    # Good
    # Lowercase and strip ``text``.
    def _normalize(text):
        return text.strip().lower()

SLD83x - Import Graph Architecture
----------------------------------------------------------------------

SLD83x are **workspace-wide architectural checks**: they require a global
view of every ``.py`` file and therefore run via ``python -m stolid``,
not as flake8 plugin rules. They analyze the runtime import graph,
collapsing each level of the package hierarchy into a *quotient* graph
and applying graph-theoretic primitives (strongly connected components,
condensation depth, reach density) at each level.

Imports under ``if TYPE_CHECKING:`` (and ``typing.TYPE_CHECKING`` /
``t.TYPE_CHECKING`` aliases) are excluded — they do not execute at
runtime and are a legitimate way to break otherwise-unavoidable cycles.
The rules measure runtime architectural structure, not the strictly
larger graph of conceptual coupling.

Per-line ``# noqa`` markers are not honored for SLD83x: these are
workspace-wide claims, not per-line, and silencing one ``__init__.py``
would be a poor expression of "this whole architecture is fine."

**SLD831**: Cyclic dependency cluster contains more than 15 modules.
Small cycles (``requests`` has 8, ``click`` 11, ``flask`` 14) remain
comprehensible; clusters past ~15 modules begin to function as
undifferentiated mud where every module can reach every other and
refactors propagate unpredictably.

**SLD832**: Cross-package cyclic dependency at any level ≥ 2 whose
constituent subpackages cover more than 10 modules total. This is the
rule that catches the architectural failure where individual modules
are arranged hierarchically but subpackages reach across each other
circularly. The threshold is on per-SCC module weight: a cycle between
two 100-module subpackages is much worse than a cycle between two
3-module subpackages even though both involve 2 nodes at the quotient
level.

**SLD833**: Condensation depth exceeds 8 at any level with at least
10 nodes. The condensation depth is the smallest number of layers any
valid ``import-linter`` layered contract would need; eight is generous
— most well-organized architectures have three to five. The 10-node
minimum prevents the rule from firing on tiny levels where depth is
mechanically constrained by node count anyway. Fires once per level
that exceeds the threshold; level 4 and level 5 both firing yields
two diagnostics because each level represents an independent
architectural slice.

**SLD834**: At any level ≥ 2 with at least 10 nodes, the largest SCC
contains more than 60% of the level's total module weight. This rule
names the architecture where the majority of code lives in one
mutually-reachable cluster of subpackages — not a layered
architecture, just a directory hierarchy stretched over a single
component.

**SLD835**: Module-level reach density exceeds 0.6, where density is
the count of ordered transitively-reachable pairs plus an SCC bonus,
normalized by ``n * (n - 1)``. A fully-reachable chain scores 0.5;
fully-mutually-reachable modules score above 1.0. This rule catches
the small-package failure mode: most modules importing most modules
transitively, just without the structure being large enough to
trigger SLD831 or to have a meaningful level ≥ 2 for SLD832/SLD834.

