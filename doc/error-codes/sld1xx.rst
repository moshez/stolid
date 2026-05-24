SLD1xx - Testing and Dynamic Execution
======================================================================

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

