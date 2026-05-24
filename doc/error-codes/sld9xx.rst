SLD9xx - Privacy
======================================================================

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

