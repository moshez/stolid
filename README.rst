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

Every diagnostic is an ``SLDxxx`` code, grouped by leading digit so a
whole family can be reasoned about — or silenced — together:

- **SLD1xx** — testing and dynamic execution: no ``unittest.mock.patch``,
  no ``exec`` / ``eval`` / ``__import__``.
- **SLD2xx** — abstract base classes: prefer ``Protocol`` over ``ABC``,
  and keep any single module's imported surface narrow.
- **SLD3xx** — object-oriented design: boring constructors, no private
  methods, and real enums instead of stringly-typed values.
- **SLD4xx** — inheritance: no subclassing of concrete classes.
- **SLD5xx** — dataclass configuration: ``frozen``, ``slots``, and
  ``kw_only`` on every dataclass.
- **SLD6xx** — code complexity: bounded function weight, argument and
  method counts, and context-manager-friendly cleanup.
- **SLD7xx** — naming: no vague words, no shadowing of stdlib names, no
  confusable near-duplicate names.
- **SLD8xx** — cross-file contracts, documentation, and import-graph
  architecture: the checks that need a workspace-wide view and run via
  ``python -m stolid``.
- **SLD9xx** — privacy: the underscore-prefix convention across
  attributes, modules, and imports.

The full catalog — every code with its rationale and bad/good examples —
lives in the documentation under ``doc/error-codes/`` (one page per
family).

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
