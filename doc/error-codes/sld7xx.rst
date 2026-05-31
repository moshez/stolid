SLD7xx - Naming
======================================================================

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

Dunder names (the ``__name__`` form, such as ``__init__``, ``__add__``,
or ``__all__``) are never flagged: they are mandated by Python and a
user cannot rename them to disambiguate, so pairs like ``__add__`` /
``__and__`` are exempt.

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

**SLD704**: Flags any function or method whose name starts with ``is_``
(optionally prefixed with leading underscores, e.g. ``_is_ready``) but
whose return annotation is not ``bool`` (or ``TypeGuard[...]`` /
``TypeIs[...]``, which are bool-valued by definition). The ``is_``
prefix is a strong convention for boolean predicates -- naming a
function ``is_open`` and then returning a string, an integer, or
``None`` lies to every caller and breaks idioms like
``if is_open(x):``.

Functions with no return annotation are not flagged: with no claim
about the return type there is no claim to contradict. To force the
issue, add an explicit annotation. Names that merely happen to start
with the letters ``is`` (``isolate``, ``island``, ``issue``) are not
matched -- only the ``is_`` prefix triggers the rule.

.. code-block:: python

    # Bad
    def is_ready() -> str:
        return "yes"

    def is_count() -> int:
        return 0

    class Job:
        def is_open(self) -> str | None:
            ...

    # Good
    def is_ready() -> bool:
        return True

    from typing import TypeGuard

    def is_str(x: object) -> TypeGuard[str]:
        return isinstance(x, str)

    # Good (no annotation -- nothing to contradict)
    def is_ready():
        return True

