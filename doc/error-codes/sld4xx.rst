SLD4xx - Inheritance
======================================================================

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

