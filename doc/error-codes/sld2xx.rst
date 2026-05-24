SLD2xx - Abstract Base Classes
======================================================================

**SLD201**: Prohibits importing ``ABC`` from the ``abc`` module.

**SLD202**: Prohibits using ``@abstractmethod`` decorator.

**SLD203**: Prohibits ``typing.cast``. Casts bypass runtime safety; if you
genuinely need one, silence with ``# noqa: SLD203`` to make the choice
visible at the call site.

Use ``typing.Protocol`` for interfaces instead:

.. code-block:: python

    # Bad
    from abc import ABC, abstractmethod

    class HTTPClient(ABC):
        @abstractmethod
        def get(self, url: str) -> Response:
            ...

    # Good
    from typing import Protocol

    class HTTPClient(Protocol):
        def get(self, url: str) -> Response:
            ...

**SLD205**: Flags too many distinct names imported from a single module
via ``from Y import ...``. Heavy reliance on one dependency is a
refactoring liability: changes to that module ripple through every
importer, and the wide surface area is hard to test, replace, or
summarize at the boundary.

The limit is **7 distinct names per module**, aggregated across every
``from Y import ...`` statement in the module. A name imported in two
statements counts once. The diagnostic is reported on the first such
statement.

Exemptions:

- ``typing`` and ``ast`` are allowlisted: both are broad-API stdlib
  namespaces where reaching for many members is structural rather
  than coupling.
- Imports inside ``if TYPE_CHECKING:`` blocks are ignored entirely
  (the ``else:`` branch of such an ``if`` still runs at runtime and
  is checked).
- ``from . import ...`` (relative import with no module name) is
  skipped — the package boundary is already drawn by the dot.

To fix a real violation, either split the dependency across more
focused call sites (so no single file carries the whole surface) or
wrap the wide API behind a narrower local abstraction — a small
class, function, or module facade that exposes only the operations
this code actually uses.

.. code-block:: python

    # Bad (8 names from one module)
    from somelib import a, b, c, d, e, f, g, h

    # Bad (split statements still aggregate per module)
    from somelib import a, b, c, d
    from somelib import e, f, g, h

    # Good (allowlisted)
    from typing import Any, Iterable, Iterator, List, Mapping, Optional, Protocol

    # Good (typing-only block ignored)
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from somelib import A, B, C, D, E, F, G, H

    # Good (relative import — package boundary)
    from . import a, b, c, d, e, f, g, h

    # Good (wrap the wide API behind a narrower facade)
    # somelib_facade.py
    from somelib import a, b, c  # only what callers actually need

    def do_thing(x):
        return b(a(x)) + c()

    # callers/...
    from .somelib_facade import do_thing

**SLD206**: Prohibits any reference to ``NotImplementedError`` outside the
body of a function directly decorated with ``functools.singledispatch``.
``NotImplementedError`` is the conventional marker for an abstract method
that subclasses must override; stolid rejects subclassing for behavior
(see SLD201/SLD202/SLD401), so the only legitimate use is the default body
of a ``singledispatch`` generic function, where it signals that no
registered overload matched the argument type. Registered overloads
(``@f.register``) are not exempt — they implement the work and should
either handle the case or not be registered.

.. code-block:: python

    # Bad
    class Handler:
        def handle(self, event):
            raise NotImplementedError

    def parse(source):
        raise NotImplementedError("subclass this")

    # Good
    import functools

    @functools.singledispatch
    def serialize(obj) -> bytes:
        raise NotImplementedError(f"no serializer for {type(obj)}")

    @serialize.register
    def _(obj: User) -> bytes:
        return json.dumps({"name": obj.name}).encode()

**SLD207**: Flags too many distinct attribute accesses on a single
module bound by ``import Y`` (or ``import Y as A``). Like SLD205, this
is a coupling smell: the importer touches a wide swath of one
module's public surface, so any change there ripples through every
caller.

The limit is **7 distinct attribute names per bound module**.
Repeated accesses to the same attribute count once. The diagnostic
is reported on the ``import`` statement.

SLD205 and SLD207 are independent budgets: mixing ``from somelib
import ...`` with ``import somelib; somelib.x`` does not compound.
Each pattern must exceed 7 on its own to fire.

Exemptions:

- ``typing`` and ``ast`` are allowlisted: both are broad-API stdlib
  namespaces where reaching for many members is structural rather
  than coupling.
- Attribute accesses inside ``if TYPE_CHECKING:`` blocks are ignored
  entirely (the ``else:`` branch of such an ``if`` still runs at
  runtime and is checked).

To fix, either split the dependency across more focused call sites
or wrap the wide API behind a narrower local abstraction.

.. code-block:: python

    # Bad (8 distinct attribute accesses on one module)
    import somelib
    use(somelib.a, somelib.b, somelib.c, somelib.d,
        somelib.e, somelib.f, somelib.g, somelib.h)

    # Bad (alias does not help)
    import somelib as sl
    use(sl.a, sl.b, sl.c, sl.d, sl.e, sl.f, sl.g, sl.h)

    # Good (allowlisted)
    import typing
    x: typing.Any = ...

    # Good (typing-only block ignored)
    from typing import TYPE_CHECKING
    import somelib
    if TYPE_CHECKING:
        use(somelib.A, somelib.B, somelib.C, somelib.D,
            somelib.E, somelib.F, somelib.G, somelib.H)

