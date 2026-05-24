SLD3xx - Object-Oriented Design
======================================================================

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

Methods decorated with ``@override`` (from ``typing`` or
``typing_extensions``) are exempt: the decorator is the author's
declaration that the function lives on the class on purpose, because it
fulfills a parent class's or Protocol's contract — not because it
happens to touch private state.

.. code-block:: python

    from typing import override

    class JSONRenderer:
        @override
        def render(self, value: object) -> str:
            return json.dumps(value)

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

