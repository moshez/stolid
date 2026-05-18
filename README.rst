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

Stolid integrates directly with flake8:

.. code-block:: bash

    flake8 your_code.py

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
