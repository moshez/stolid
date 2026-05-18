# Shared constants for stolid. Single-consumer SLD codes live in the
# module that emits them; this file holds only multi-consumer codes and
# non-code constants (limits, allow-lists, word sets).

from __future__ import annotations

# Duplicate detector thresholds
MIN_CLONE_NODES = 12
MIN_CLONE_SCORE = 2.5

# Bad name patterns (vague, non-descriptive names)
BAD_NAME_WORDS: frozenset[str] = frozenset(
    {"help", "helper", "helpers", "util", "utils", "manage", "manager", "managers"}
)

# Dangerous builtins for dynamic code execution. Any use is a strong signal
# of metaprogramming shenanigans and should be carefully audited.
DANGEROUS_BUILTINS: frozenset[str] = frozenset({"exec", "eval", "__import__"})

# Code limits
# SLD601 counts a *weighted* line budget, not raw lines. Each line's weight is
# COMPLEXITY_FACTOR ** (indent_depth + max(0, bracket_depth - 1)), where
# indent_depth is the line's indent past the function body's baseline (one
# step = INDENT_WIDTH spaces), and bracket_depth is the deepest stack of
# brackets opened on the line itself. Blank lines weigh 0; comment-only
# lines weigh 1 unweighted. A flat function still costs ~1 per line, so
# the budget reads roughly like a line count for unnested code.
#
# Factor 1.3 was chosen for symmetry with the spirit of cyclomatic
# complexity while staying tolerable: depth-4 code costs ~2.86x per line,
# so a budget of 30 fits ~10 lines of consistently 4-deep code -- enough
# room for typical guard/branch nesting, harsh enough to push staircase
# code toward extraction or early returns. INDENT_WIDTH is hardcoded to 4
# in line with PEP 8 and stolid's opinionated stance on style.
COMPLEXITY_FACTOR = 1.3
INDENT_WIDTH = 4
MAX_FUNCTION_LINES = 30
MAX_FUNCTION_ARGS = 4
MAX_CLASS_METHODS = 15
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
