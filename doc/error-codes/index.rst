Error Codes
===========

Every stolid diagnostic is an ``SLDxxx`` code. The leading digit groups
codes by the concern they enforce, so a whole family can be reasoned
about — or silenced — together:

- **SLD1xx** — testing and dynamic execution (mocking, ``exec``/``eval``).
- **SLD2xx** — abstract base classes and wide-module coupling.
- **SLD3xx** — object-oriented design and the enum-over-strings smells.
- **SLD4xx** — inheritance from concrete classes.
- **SLD5xx** — dataclass configuration (frozen, slotted, keyword-only).
- **SLD6xx** — code complexity (function weight, argument counts, cleanup).
- **SLD7xx** — naming (vague words, shadowing, confusable pairs).
- **SLD8xx** — cross-file contracts, documentation, and import-graph
  architecture (the checks that need a workspace-wide view).
- **SLD9xx** — privacy and the underscore-prefix convention.

Each page below lists the codes in its family with the rationale and a
bad/good example where one helps.

.. toctree::
   :maxdepth: 1

   sld1xx
   sld2xx
   sld3xx
   sld4xx
   sld5xx
   sld6xx
   sld7xx
   sld8xx
   sld9xx
