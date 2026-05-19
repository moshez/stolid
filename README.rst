stolid
======

A flake8 plugin that enforces opinionated Python coding conventions for clean,
maintainable code.

Stolid encourages:

- **Composition over inheritance**
- **Dependency injection over mocking**
- **Protocol-based typing over abstract base classes**
- **Immutable dataclasses**
- **Small, focused functions and classes**

Installation
------------

.. code-block:: bash

    pip install stolid

Usage
-----

Run stolid as a module to check your code:

.. code-block:: bash

    python -m stolid your_package/

``python -m stolid`` is the unified entry point. It runs the flake8
plugin (which emits every per-file SLDxxx code) and then the cross-file
scanners that produce the SLD80x public-contract diagnostics, exiting
with the worst of the two stages' exit codes. Paths default to ``.`` if
none are given.

Running ``flake8`` directly still works and is fine for editor
integration, but it only loads the in-file plugin — the SLD80x
cross-file checks require the workspace-wide view that ``python -m
stolid`` provides:

.. code-block:: bash

    flake8 your_code.py  # in-file SLDxxx only, no SLD80x

Error Codes
-----------

SLD1xx - Testing and Dynamic Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**SLD102**: Prohibits use of ``patch`` and ``patch.object`` from ``unittest.mock``.

Use dependency injection instead of mocking:

.. code-block:: python

    # Bad
    from unittest.mock import patch

    @patch("mymodule.requests.get")
    def test_fetch(mock_get):
        ...

    # Good
    class TestFetch(unittest.TestCase):
        def test_fetch(self) -> None:
            fake_client = FakeHTTPClient(response={"data": 1})
            fetcher = DataFetcher(client=fake_client)
            result = fetcher.fetch()
            assert_that(result, equal_to(1))

**SLD103**: Prohibits any reference to the dynamic-execution builtins
``exec``, ``eval``, and ``__import__``. These almost always indicate
metaprogramming shenanigans that deserve a careful review; if you
genuinely need one, silence with ``# noqa: SLD103`` so the choice is
visible at the call site. Bare references (e.g. ``f = exec``) are flagged
too, since aliasing is just calling with extra steps.

.. code-block:: python

    # Bad
    def run_user_code(source: str) -> None:
        exec(source)

    result = eval(expression)
    mod = __import__(name)

    # Good
    import importlib

    def run_user_code(source: str) -> None:
        compiled = compile_in_sandbox(source)
        compiled.run()

    mod = importlib.import_module(name)

SLD2xx - Abstract Base Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

**SLD205**: Flags broad coupling to a single module. Heavy reliance on
one dependency is a refactoring liability: changes to that module
ripple through every importer, and the wide surface area is hard to
test, replace, or summarize at the boundary.

The limit is **7 distinct references per module**, tracked
independently for the two import patterns:

- ``from Y import a, b, c, ...`` — distinct names imported from
  ``Y``, aggregated across every ``from Y import ...`` statement in
  the module. A name imported in two statements counts once. The
  diagnostic is reported on the first such statement.
- ``import Y`` (or ``import Y as A``) — distinct attribute names
  accessed via ``Y.x`` / ``A.x``. Repeated accesses to the same
  attribute count once. The diagnostic is reported on the ``import``
  statement.

The two budgets are independent: mixing ``from somelib import ...``
with ``import somelib; somelib.x`` does not compound. Each pattern
must exceed 7 on its own to fire.

Exemptions:

- ``typing`` and ``ast`` are allowlisted: both are broad-API stdlib
  namespaces where reaching for many members is structural rather
  than coupling.
- Imports and uses inside ``if TYPE_CHECKING:`` blocks are ignored
  entirely (the ``else:`` branch of such an ``if`` still runs at
  runtime and is checked).
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

    # Bad (8 distinct attribute accesses on one module)
    import somelib
    use(somelib.a, somelib.b, somelib.c, somelib.d,
        somelib.e, somelib.f, somelib.g, somelib.h)

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

SLD3xx - Object-Oriented Design
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**SLD301**: Prohibits ``__init__`` and ``__post_init__`` methods.

Other dunder methods (``__str__``, ``__repr__``, ``__eq__``, ``__hash__``,
``__call__``, etc.) are allowed.

Use ``@dataclass`` with ``default_factory`` for attributes, or ``@classmethod``
for parameter computation:

.. code-block:: python

    # Bad
    class Processor:
        def __init__(self, client, config):
            self.client = client
            self.config = config

    # Good
    from dataclasses import dataclass

    @dataclass(frozen=True, slots=True, kw_only=True)
    class Processor:
        client: HTTPClient
        config: Config

**SLD302**: Prohibits private methods (starting with ``_``).

Extract private methods into separate classes:

.. code-block:: python

    # Bad
    class Processor:
        def _validate(self, data):
            ...

    # Good
    class Validator:
        def validate(self, data):
            ...

**SLD303**: Flags methods that only access public members of ``self``.

Convert to module-level functions or use ``functools.singledispatch``:

.. code-block:: python

    # Bad
    class User:
        name: str

        def display_name(self) -> str:
            return self.name.title()

    # Good
    def display_name(user: User) -> str:
        return user.name.title()

**SLD304**: Flags an expression compared (via ``==``, ``!=``, or ``in`` against
a tuple/list/set literal) with two or more distinct string literals within a
single function or module scope. Single ``x == "foo"`` comparisons are fine
(parsers commonly need them); the smell is having multiple candidate values.

.. code-block:: python

    # Bad
    def handle(status: str) -> int:
        if status == "open":
            return 1
        if status == "closed":
            return 2
        return 0

    # Good
    from enum import Enum

    class Status(Enum):
        OPEN = "open"
        CLOSED = "closed"

    def handle(status: Status) -> int:
        if status is Status.OPEN:
            return 1
        if status is Status.CLOSED:
            return 2
        return 0

**SLD305**: Flags ``match`` statements with two or more string-literal ``case``
patterns (including ``case "a" | "b":`` alternatives). Pattern matching on
string values is a strong enum smell.

.. code-block:: python

    # Bad
    def handle(status):
        match status:
            case "open":
                return 1
            case "closed":
                return 2

**SLD306**: Flags any string literal that appears in equality contexts (``==``,
``!=``, ``in`` collection, or a ``match`` case) three or more times across the
module. A value special enough to be checked from many sites should be a
named enum member.

**SLD307**: Flags ``Literal[...]`` annotations whose arguments include string
literals. ``Literal["a", "b"]`` is a lightweight alternative to an enum, but
this project prefers a real ``Enum`` for the readability and refactoring wins.

.. code-block:: python

    # Bad
    from typing import Literal

    def handle(status: Literal["open", "closed"]) -> int: ...

    # Good
    from enum import Enum

    class Status(Enum):
        OPEN = "open"
        CLOSED = "closed"

    def handle(status: Status) -> int: ...

**SLD308**: Flags two or more peer module-level string constants whose values
are valid Python identifiers (e.g. ``READ = "read"``). A cluster of such
constants is almost always an enum waiting to be written; defining them
loosely lets the rest of the SLD30x checks miss them (the literal never
appears in a comparison or ``match`` — only the name does). The check
ignores values that aren't ``str.isidentifier()``-true, so things like
``HOST = "example.com"`` or ``GREETING = "hello world"`` don't fire.

.. code-block:: python

    # Bad
    READ = "read"
    WRITE = "write"
    DELETE = "delete"

    # Good
    from enum import Enum, auto

    class Action(Enum):
        READ = auto()
        WRITE = auto()
        DELETE = auto()

**SLD309**: Flags ``Enum`` subclasses (including ``StrEnum``, ``IntEnum``,
``Flag``, ``IntFlag``) where every string-constant member has an
identifier-shaped value. Such enums leak a stringly-typed backdoor:
``MyEnum("read")`` round-trips a bare string into a member. Use
``auto()`` instead — it generates unique values without exposing
identifier-shaped strings. Non-identifier values (``"#ff0000"``,
``"application/json"``) are kept; the check only fires when every
string member is identifier-shaped.

.. code-block:: python

    # Bad
    from enum import Enum

    class Action(Enum):
        READ = "read"
        WRITE = "write"

    # Good
    from enum import Enum, auto

    class Action(Enum):
        READ = auto()
        WRITE = auto()

SLD4xx - Inheritance
~~~~~~~~~~~~~~~~~~~~

**SLD401**: Prohibits inheritance from concrete classes.

Allowed base classes:

- Typing: ``Protocol``, ``Generic``
- Exceptions: ``Exception``, ``BaseException``
- Testing: ``TestCase``
- Enums: ``Enum``, ``IntEnum``, ``StrEnum``, ``Flag``, ``IntFlag``
- Other: ``TypedDict``, ``NamedTuple``

.. code-block:: python

    # Bad
    class MyHandler(BaseHandler):
        ...

    # Good
    @dataclass(frozen=True, slots=True, kw_only=True)
    class MyHandler:
        validator: Validator
        processor: Processor

SLD5xx - Dataclass Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All dataclasses must have:

**SLD501**: ``frozen=True`` (immutability)

**SLD502**: ``slots=True`` (memory efficiency)

**SLD503**: ``kw_only=True`` (keyword-only arguments)

.. code-block:: python

    # Bad
    @dataclass
    class Settings:
        timeout: int

    # Good
    @dataclass(frozen=True, slots=True, kw_only=True)
    class Settings:
        timeout: int

SLD6xx - Code Complexity
~~~~~~~~~~~~~~~~~~~~~~~~

**SLD601**: Functions limited to a weighted complexity of 30. A flat
function still costs ~1 per line, so the budget reads roughly like a line
count for unnested code. Each body line's weight is

::

    1.3 ** (indent_depth + max(0, bracket_depth - 1))

where ``indent_depth`` counts indentation past the function body's
baseline (one step = 4 spaces) and ``bracket_depth`` is the deepest stack
of ``(``, ``[``, ``{`` opened on that line. Blank lines weigh 0;
comment-only lines weigh 1 unweighted. Deep nesting and dense expressions
are penalized exponentially -- four levels of ``if``/``for`` cost roughly
2.86x per line, pushing functions toward early returns or extraction.

.. code-block:: python

    # Bad (passes line count, fails complexity)
    def process(items):
        for item in items:
            if item.active:
                for child in item.children:
                    if child.valid:
                        if check(child):
                            do_work(child)  # depth 5, weight ~3.7

    # Good (guard clauses keep weights near 1.0 per line)
    def process(items):
        for item in items:
            if not item.active:
                continue
            for child in item.children:
                if not child.valid or not check(child):
                    continue
                do_work(child)

**SLD602**: Functions limited to 4 arguments (excludes ``self``/``cls``)

**SLD603**: Classes limited to 15 methods (excludes dunder methods)

**SLD604**: Modules limited to 400 lines

**SLD605**: Flags nested ``with`` statements that can be flattened into a
single ``contextlib.ExitStack``. The check fires on a ``with`` statement
whose body's *last* statement is another ``with`` — every ``__exit__``
in the chain runs at the same point at the end, so an ``ExitStack``
preserves the exact semantics with one level of indentation. Statements
*between* the ``with``\ s are fine, and anything after the whole nest
(outside the outermost ``with``) is fine; only stuff sandwiched between
an inner ``with`` and the end of its enclosing ``with`` blocks the
refactor, and that case is left alone.

.. code-block:: python

    # Bad
    with acquire() as resource:
        prepared = prepare(resource)
        with process(prepared) as handle:
            do_work(handle)
    print("done")

    # Good
    from contextlib import ExitStack

    with ExitStack() as stack:
        resource = stack.enter_context(acquire())
        prepared = prepare(resource)
        handle = stack.enter_context(process(prepared))
        do_work(handle)
    print("done")

**SLD606**: Flags ``try``/``finally`` statements outside of
``@contextlib.contextmanager`` (or ``@contextlib.asynccontextmanager``)
generators. ``try``/``finally`` is the bare-knuckles version of a
context manager: the cleanup belongs behind a ``with`` either way, so
either reuse an existing context manager or define one. The exemption
is the natural body of a ``@contextmanager``-decorated generator,
where ``try``/``finally`` around ``yield`` is the conventional shape.

.. code-block:: python

    # Bad
    def process(path):
        f = open(path)
        try:
            return f.read()
        finally:
            f.close()

    # Good (reuse an existing context manager)
    def process(path):
        with open(path) as f:
            return f.read()

    # Good (define your own context manager)
    from contextlib import contextmanager

    @contextmanager
    def acquire(resource):
        resource.lock()
        try:
            yield resource
        finally:
            resource.unlock()

**SLD607**: Flags ``try``/``except`` blocks whose handlers are all
just ``pass``. The intent — swallow these exceptions — lands in a
single line with ``contextlib.suppress``, and the noise of the
``try``/``except`` scaffolding goes away. Handlers that do real work
are untouched; a mix of pass-only and real handlers is also left
alone. ``else`` and ``finally`` clauses are not handled by
``suppress``, so their presence disables the check.

.. code-block:: python

    # Bad
    try:
        config.remove(key)
    except KeyError:
        pass

    # Good
    from contextlib import suppress

    with suppress(KeyError):
        config.remove(key)

**SLD608**: Dataclasses limited to 10 fields (excludes ``ClassVar``
annotations, which are class attributes rather than instance fields).
A dataclass that needs more than ten fields is usually two ideas
crammed into one — split it, or group related fields into a nested
dataclass.

.. code-block:: python

    # Bad
    @dataclass(frozen=True, slots=True, kw_only=True)
    class Order:
        id: int
        customer_name: str
        customer_email: str
        customer_phone: str
        billing_street: str
        billing_city: str
        billing_zip: str
        shipping_street: str
        shipping_city: str
        shipping_zip: str
        total: int

    # Good (group related fields into nested dataclasses)
    @dataclass(frozen=True, slots=True, kw_only=True)
    class Order:
        id: int
        customer: Customer
        billing: Address
        shipping: Address
        total: int

SLD7xx - Naming
~~~~~~~~~~~~~~~

**SLD701**: Names must not contain vague words (``helper``, ``util``,
``manager``, etc.).

**SLD702**: Module-level names (functions, classes, top-level assignments)
must not shadow names from ``builtins``, the ``typing`` module, or any
stdlib module:

.. code-block:: python

    # Bad
    def list():  # shadows builtin 'list'
        ...

    def sys():  # shadows stdlib module 'sys'
        ...

    def Optional():  # shadows typing.Optional
        ...

Imports of these names are fine — only definitions are flagged.

**SLD703**: Flags any pair of names bound in the same scope (module,
function, class, lambda, or comprehension) whose identifiers differ by
exactly one inserted, deleted, or substituted *letter*. The classic
``node`` / ``nodes`` and ``code`` / ``codes`` pairs are confusable at a
glance and obscure intent — use distinct names instead.

The single carve-out is single-letter names bound only as iteration
targets: ``for i, thing in items:`` is fine, including pairings like
``for i in xs: ... for j in ys: ...`` where ``i`` and ``j`` co-occur in
the same scope. Multi-letter loop variables are *not* exempt; rewrite
``for node in nodes:`` as ``for n in nodes:`` or rename one of the names.

The differing character must be a letter (a-z, A-Z) for the rule to
fire — names that differ only in digits or punctuation
(``SLD304`` / ``SLD305``, ``foo_1`` / ``foo_2``, ``foo`` / ``_foo``)
are intentionally allowed.

.. code-block:: python

    # Bad
    nodes = collect()
    for node in nodes:  # 'node' vs 'nodes' — confusable
        process(node)

    def fn(foo, fooo):  # 'foo' vs 'fooo' — confusable
        return foo

    mosh = 1
    mish = 2  # 'mosh' vs 'mish' — one substitution

    moshe = 1
    mosh = 2  # 'moshe' vs 'mosh' — one insertion

    # Good
    nodes = collect()
    for n in nodes:  # single-letter loop var — exempt
        process(n)

    def fn(first, second):
        return first

    # Good (digit-only differences are allowed)
    SLD304 = "..."
    SLD305 = "..."

SLD80x - Cross-File Public Contracts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SLD80x are **cross-file** checks: they require a workspace-wide view and
therefore do not run as part of the flake8 plugin. They are emitted by the
``python -m stolid`` runner, which scans every ``.py`` file under the
given paths (honoring ``.gitignore``) and then re-walks each file to
classify every public annotation against the workspace symbol table.

A public annotation may only name a contract (``Protocol``, ``ABC``,
``TypedDict``, ``NamedTuple``, ``Enum``), a primitive (``int``, ``str``,
``bool``, ...), or compose those through an abstract container from
``collections.abc`` / ``typing`` (``Mapping``, ``Sequence``, ``Iterable``,
...) or a union. Naming an open concrete class commits callers to that
exact type; the rule rejects it so that implementations stay swappable
behind their contracts.

"Public" surface here means: top-level functions and methods of public
classes in modules whose filename does not start with ``_``
(``__init__.py`` is treated as public). Private modules, private
top-level classes, and private members of public classes are skipped.

Diagnostics honor per-line ``# noqa`` markers exactly like SLD801.

**SLD802**: Public annotation references a workspace-defined concrete
class. A concrete class is any ``class X:`` that is not a Protocol, ABC,
TypedDict, NamedTuple, or Enum subclass. Names that are not defined
anywhere in the scanned workspace are treated as out-of-scope
third-party references and are silently allowed.

.. code-block:: python

    # Bad: backend.py
    from dataclasses import dataclass

    @dataclass(frozen=True, slots=True, kw_only=True)
    class RealBackend:
        name: str

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

SLD9xx - Privacy
~~~~~~~~~~~~~~~~

The checker enforces Python's underscore-prefix convention across class
attributes, module attributes, and submodule imports. Dunder names
(``__init__``, ``__class__``, ``__future__``) are not flagged. Relative
imports are exempt — the syntax itself draws the package boundary.

**SLD901**: External read of a private attribute. ``obj._attr`` is only
permitted on the privileged first argument (``self``, ``cls``, or whatever
the method's first parameter is named) of an instance or class method.

.. code-block:: python

    # Bad
    def render(thing):
        return thing._cached_html

    # Good
    class Renderer:
        def render(self):
            return self._cached_html

**SLD902**: External write of a private attribute. Same predicate as SLD901
but for assignment, augmented assignment, and ``del``. Tracked as a separate
code so codebases can adopt different policies for reads and writes.

.. code-block:: python

    # Bad
    session._token = new_token
    del session._cache

**SLD903**: Absolute import of a private name. Use a relative import to stay
intra-package, or expose a public re-export.

.. code-block:: python

    # Bad
    from pkg import _internal_helper

    # Good
    from . import _internal_helper
    from ._submodule import public

**SLD904**: Import of or from a private submodule. The dotted path may not
contain a segment starting with ``_`` (other than dunders).

.. code-block:: python

    # Bad
    from numpy._core import multiarray
    import numpy._core.umath

    # Good
    from ._core import multiarray

**SLD905**: Private attribute access on an imported name. The post-import
counterpart to SLD903 and SLD904.

.. code-block:: python

    import numpy as np

    # Bad
    np._core.something

    # Good
    np.array(...)

Configuration
-------------

Stolid follows standard flake8 configuration. Add to your ``setup.cfg`` or
``.flake8``:

.. code-block:: ini

    [flake8]
    extend-ignore = SLD301,SLD302

Or use per-file ignores:

.. code-block:: ini

    [flake8]
    per-file-ignores =
        tests/*:SLD301,SLD302

Development
-----------

.. code-block:: bash

    pip install nox

    # Run all checks
    nox

    # Run specific sessions
    nox -s tests    # Run tests with coverage
    nox -s lint     # Run black and flake8
    nox -s mypy     # Run type checking

License
-------

MIT License. See LICENSE for details.
