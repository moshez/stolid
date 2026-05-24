SLD6xx - Code Complexity
======================================================================

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

**SLD609**: Flags a function parameter whose only role inside the
body is to select a branch -- it is tested in an ``if``, ``while``,
ternary, ``assert``, or ``match`` and nothing else flows from its
value. A function that branches on a parameter is doing two jobs
under one name; lift the choice out of the parameter and up into
which function the caller calls.

The analysis is intraprocedural by design. A parameter that is passed
onward to a callee counts as a data use, so a pure forwarder is not
flagged -- the callee gets flagged on its own once it has a branching
parameter, and the next run flags the forwarder once it has to choose
which split to call. Attribute access (``p.x``), indexing (``p[0]``),
and arithmetic (``p + 1``) all count as data uses too: the parameter
is being consumed for its value, not directly tested. ``self`` /
``cls`` and ``*args`` / ``**kwargs`` are never reported. Parameters
used only inside a nested function or lambda are conservatively
uncounted (they look like closure captures, not branch tests).

Membership is treated by the right-hand side. ``p in ("a", "b")`` (a
literal, or a tuple/list/set of literals) is a branch test -- a finite
set of compile-time choices the caller could pick between -- so ``p``
is flagged. But ``p in haystack`` where ``haystack`` is a runtime value
makes ``p`` a *search needle*: its value is consumed like an index, not
tested against a fixed set, so it counts as a data use and is not
flagged. ``==`` / ``!=`` remain branch tests against any right-hand
side. (A consequence: ``p in NAMED_CONSTANT`` is read as runtime and
not flagged, and ``p in "literal_string"`` is read as a finite choice
and flagged -- rare enough to silence with ``# noqa: SLD609`` when the
string is really a search target.)

.. code-block:: python

    # Bad
    def fetch_user(user_id, mark_seen):
        user = db.get(user_id)
        if mark_seen:
            user.touch()
        return user

    def render(data, fmt):
        if fmt == "json":
            return to_json(data)
        return to_xml(data)

    # Good (split the function)
    def fetch_user(user_id):
        return db.get(user_id)

    def fetch_user_and_mark(user_id):
        user = fetch_user(user_id)
        user.touch()
        return user

    # Good (parameter flows into data, not just a branch)
    def set_enabled(widget, enabled):
        widget.enabled = enabled

    # Good (parameter is passed onward -- forwarder)
    def forward(x, flag):
        return helper(x, flag)

    # Good (``None``-default idiom: control AND data use of ``opts``)
    def parse(text, opts=None):
        if opts is None:
            opts = default_opts()
        return run(text, opts)

