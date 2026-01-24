"""Constants and error messages for stolid."""

from __future__ import annotations

# Error codes and messages
STOLID102 = "STOLID102 Use of patch/patch.object is prohibited (use dependency injection)"
STOLID201 = "STOLID201 Import of ABC is prohibited (use Protocol instead)"
STOLID202 = "STOLID202 Use of @abstractmethod is prohibited (use Protocol instead)"
STOLID301 = (
    "STOLID301 __init__ method is prohibited (use @dataclass with default_factory "
    "for attribute initialization; use @classmethod for ergonomic parameter "
    "computation)"
)
STOLID302 = "STOLID302 Private method '{}' defined (extract to separate class)"
STOLID303 = (
    "STOLID303 Method '{}' only accesses public members of self "
    "(convert to module-level function; use functools.singledispatch "
    "if polymorphism is needed)"
)
STOLID401 = "STOLID401 Class '{}' inherits from concrete class '{}' (use composition)"
STOLID501 = "STOLID501 Dataclass '{}' missing frozen=True"
STOLID502 = "STOLID502 Dataclass '{}' missing slots=True"
STOLID503 = "STOLID503 Dataclass '{}' missing kw_only=True"
STOLID601 = "STOLID601 Function '{}' has {} lines (limit: {})"
STOLID602 = "STOLID602 Function '{}' has {} arguments (limit: {})"
STOLID603 = "STOLID603 Class '{}' has {} methods (limit: {})"
STOLID604 = "STOLID604 Module has {} lines (limit: {})"

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
