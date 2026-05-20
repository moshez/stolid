# Shared constants for stolid. Single-consumer SLD codes live in the
# module that emits them; this file holds only multi-consumer codes and
# non-code constants (limits, allow-lists, word sets).

from __future__ import annotations

# Duplicate detector thresholds
MIN_CLONE_NODES = 12
MIN_CLONE_SCORE = 2.5

# Dangerous builtins for dynamic code execution. Any use is a strong signal
# of metaprogramming shenanigans and should be carefully audited.
DANGEROUS_BUILTINS: frozenset[str] = frozenset({"exec", "eval", "__import__"})

# Code limits
MAX_FUNCTION_LINES = 30
MAX_FUNCTION_ARGS = 4
MAX_CLASS_METHODS = 15
MAX_DATACLASS_FIELDS = 10
MAX_MODULE_LINES = 400
MAX_MODULE_REFERENCES = 7

# Allowed base classes for inheritance
ALLOWED_BASES: frozenset[str] = frozenset(
    {
        # typing
        "Protocol",
        "Generic",
        # exceptions
        "Exception",
        "BaseException",
        # testing
        "TestCase",
        # enums
        "Enum",
        "IntEnum",
        "StrEnum",
        "Flag",
        "IntFlag",
        # other acceptable patterns
        "TypedDict",
        "NamedTuple",
    }
)
