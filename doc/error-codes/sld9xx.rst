SLD9xx - Privacy
======================================================================

The checker enforces Python's underscore-prefix convention across class
attributes, module attributes, and submodule imports. Dunder names
(``__init__``, ``__class__``, ``__future__``) are not flagged. Only the
current package exposes a private surface you may reach: ``from . import
_x`` binds an own private submodule, and ``from ._sub import public`` reads
its public surface. Reaching *up* into an ancestor (``from .. import _x``,
``from .._sub import y``) or *sideways* into a sibling's private name
(``from .sub import _x``) is flagged just like an absolute private import.

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

**SLD903**: A private name imported across a package boundary. The only
permitted way to import a private name is ``from . import _name``, which
binds the current package's own private submodule. Any module part
(``from .sub import _x``), any ancestor level (``from .. import _x``), and
every absolute import (``from pkg import _x``) is flagged. To consume a
private submodule's contents, import its *public* names instead.

.. code-block:: python

    # Bad
    from pkg import _internal_helper      # absolute
    from .sub import _internal_helper     # sibling's private name
    from .. import _internal_helper       # ancestor's private name

    # Good
    from . import _internal_helper        # own private submodule
    from ._submodule import public        # own submodule's public surface

**SLD904**: An import reaches into a private submodule across a package
boundary. A private segment (one starting with ``_``, other than a dunder)
in the dotted path is permitted only for the current package's own private
submodule — a single-dot relative import. Absolute paths and ancestor
(``..`` or deeper) paths are flagged.

.. code-block:: python

    # Bad
    from numpy._core import multiarray    # absolute
    import numpy._core.umath              # absolute
    from .._engine import compile         # ancestor's private submodule

    # Good
    from ._core import multiarray         # own private submodule

**SLD905**: Private attribute access on an imported name. The post-import
counterpart to SLD903 and SLD904.

.. code-block:: python

    import numpy as np

    # Bad
    np._core.something

    # Good
    np.array(...)

