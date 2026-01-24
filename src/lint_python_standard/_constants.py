"""Constants and error messages for lint-python-standard."""

from __future__ import annotations

# Error codes and messages
LPS102 = "LPS102 Use of patch/patch.object is prohibited (use dependency injection)"
LPS201 = "LPS201 Import of ABC is prohibited (use Protocol instead)"
LPS202 = "LPS202 Use of @abstractmethod is prohibited (use Protocol instead)"
LPS301 = (
    "LPS301 __init__ method is prohibited (use @dataclass with default_factory "
    "for attribute initialization; use @classmethod for ergonomic parameter "
    "computation)"
)
LPS302 = "LPS302 Private method '{}' defined (extract to separate class)"
LPS303 = (
    "LPS303 Method '{}' only accesses public members of self "
    "(convert to module-level function; use functools.singledispatch "
    "if polymorphism is needed)"
)
LPS401 = "LPS401 Class '{}' inherits from concrete class '{}' (use composition)"
LPS501 = "LPS501 Dataclass '{}' missing frozen=True"
LPS502 = "LPS502 Dataclass '{}' missing slots=True"
LPS503 = "LPS503 Dataclass '{}' missing kw_only=True"
LPS601 = "LPS601 Function '{}' has {} lines (limit: {})"
LPS602 = "LPS602 Function '{}' has {} arguments (limit: {})"
LPS603 = "LPS603 Class '{}' has {} methods (limit: {})"
LPS604 = "LPS604 Module has {} lines (limit: {})"

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
