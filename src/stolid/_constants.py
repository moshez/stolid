"""Constants and error messages for stolid."""

from __future__ import annotations

# Error codes and messages
SLD102 = "SLD102 Use of patch/patch.object is prohibited (use dependency injection)"
SLD201 = "SLD201 Import of ABC is prohibited (use Protocol instead)"
SLD202 = "SLD202 Use of @abstractmethod is prohibited (use Protocol instead)"
SLD301 = (
    "SLD301 __init__ method is prohibited (use @dataclass with default_factory "
    "for attribute initialization; use @classmethod for ergonomic parameter "
    "computation)"
)
SLD302 = "SLD302 Private method '{}' defined (extract to separate class)"
SLD303 = (
    "SLD303 Method '{}' only accesses public members of self "
    "(convert to module-level function; use functools.singledispatch "
    "if polymorphism is needed)"
)
SLD401 = "SLD401 Class '{}' inherits from concrete class '{}' (use composition)"
SLD501 = "SLD501 Dataclass '{}' missing frozen=True"
SLD502 = "SLD502 Dataclass '{}' missing slots=True"
SLD503 = "SLD503 Dataclass '{}' missing kw_only=True"
SLD601 = "SLD601 Function '{}' has {} lines (limit: {})"
SLD602 = "SLD602 Function '{}' has {} arguments (limit: {})"
SLD603 = "SLD603 Class '{}' has {} methods (limit: {})"
SLD604 = "SLD604 Module has {} lines (limit: {})"
SLD701 = "SLD701 Name '{}' contains forbidden word '{}' (use a more specific name)"

# Bad name patterns (vague, non-descriptive names)
BAD_NAME_WORDS: frozenset[str] = frozenset(
    {"help", "helper", "helpers", "util", "utils", "manage", "manager", "managers"}
)

# Code limits
MAX_FUNCTION_LINES = 30
MAX_FUNCTION_ARGS = 4
MAX_CLASS_METHODS = 15
MAX_MODULE_LINES = 400

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
