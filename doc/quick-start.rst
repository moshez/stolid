Getting Started with stolid
===========================

Install
-------

.. code-block:: bash

    pip install stolid

Run
---

Stolid ships a unified entry point that runs every check:

.. code-block:: bash

    python -m stolid your_package/

This runs the flake8 plugin (emitting every per-file ``SLDxxx`` code)
and then the cross-file scanners that produce the ``SLD80x``
public-contract diagnostics. The exit code is the worst of the two
stages. With no arguments, ``python -m stolid`` scans the current
directory.

Running ``flake8`` directly still works for editor integration, but it
only loads the in-file plugin — the ``SLD80x`` cross-file checks
require the workspace-wide view that ``python -m stolid`` provides:

.. code-block:: bash

    flake8 your_code.py  # in-file SLDxxx only, no SLD80x

Configure
---------

Stolid follows standard flake8 configuration. Add to your ``setup.cfg``
or ``.flake8``:

.. code-block:: ini

    [flake8]
    extend-ignore = SLD301,SLD302

Or use per-file ignores:

.. code-block:: ini

    [flake8]
    per-file-ignores =
        tests/*:SLD301,SLD302

See the README for the full catalog of error codes.
