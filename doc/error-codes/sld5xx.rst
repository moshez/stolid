SLD5xx - Dataclass Configuration
======================================================================

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

**SLD504**: Class is not decorated with ``@dataclass``. Plain ``class
Foo:`` definitions usually grow ad-hoc ``__init__`` methods and mutable
attributes; ``@dataclass`` makes the data shape explicit and pairs with
SLD501/SLD502/SLD503 to keep it immutable, slotted, and keyword-only.
Classes that inherit from an allowed non-dataclass base (``Protocol``,
``Generic``, ``Enum``/``IntEnum``/``StrEnum``/``Flag``/``IntFlag``,
``Exception``/``BaseException``, ``TestCase``, ``TypedDict``,
``NamedTuple``) are exempt -- those bases define the class's shape on
their own. The four dataclass concerns ("is a dataclass", "is frozen",
"is slotted", "is kw_only") are deliberately split across SLD504,
SLD501, SLD502, and SLD503 so a project can silence each independently.

.. code-block:: python

    # Bad
    class Settings:
        timeout: int

    # Good
    @dataclass(frozen=True, slots=True, kw_only=True)
    class Settings:
        timeout: int

    # Good (allowed base -- exempt from SLD504)
    class Backend(Protocol):
        def fetch(self, key: str) -> bytes: ...

