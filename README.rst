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

SLD1xx - Testing
~~~~~~~~~~~~~~~~

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

SLD2xx - Abstract Base Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**SLD201**: Prohibits importing ``ABC`` from the ``abc`` module.

**SLD202**: Prohibits using ``@abstractmethod`` decorator.

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

**SLD301**: Prohibits ``__init__`` methods.

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

**SLD601**: Functions limited to 30 lines

**SLD602**: Functions limited to 4 arguments (excludes ``self``/``cls``)

**SLD603**: Classes limited to 15 methods (excludes dunder methods)

**SLD604**: Modules limited to 400 lines

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
