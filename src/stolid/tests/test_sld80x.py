"""Tests for SLD802/SLD803/SLD804 — cross-file public-contract checks."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, empty, equal_to, has_item, is_not

from .code_parser import check_multifile, multifile_codes


def _just(codes: list[str], prefix: str) -> list[str]:
    return [code for code in codes if code.startswith(prefix)]


_CONCRETE_DEF = (
    "from dataclasses import dataclass\n"
    "@dataclass(frozen=True, slots=True, kw_only=True)\n"
    "class Backend:\n"
    "    name: str\n"
)

_PROTOCOL_DEF = (
    "from typing import Protocol\n"
    "class Backend(Protocol):\n"
    "    def fetch(self, key: str) -> bytes: ...\n"
)


_SLD802_PRESENT: list[tuple[str, dict[str, str]]] = [
    (
        "concrete_in_arg",
        {
            "a.py": _CONCRETE_DEF,
            "b.py": "from .a import Backend\ndef run(b: Backend) -> None: ...\n",
        },
    ),
    (
        "concrete_in_return",
        {
            "a.py": _CONCRETE_DEF,
            "b.py": "from .a import Backend\ndef make() -> Backend: ...\n",
        },
    ),
    (
        "concrete_inside_sequence",
        {
            "a.py": _CONCRETE_DEF,
            "b.py": (
                "from typing import Sequence\n"
                "from .a import Backend\n"
                "def fan(out: Sequence[Backend]) -> None: ...\n"
            ),
        },
    ),
    (
        "concrete_inside_union",
        {
            "a.py": _CONCRETE_DEF,
            "b.py": ("from .a import Backend\n" "def maybe() -> Backend | None: ...\n"),
        },
    ),
    (
        "concrete_in_dataclass_field",
        {
            "a.py": _CONCRETE_DEF,
            "b.py": (
                "from dataclasses import dataclass\n"
                "from .a import Backend\n"
                "@dataclass(frozen=True, slots=True, kw_only=True)\n"
                "class Driver:\n"
                "    backend: Backend\n"
            ),
        },
    ),
    (
        "concrete_in_module_level_assignment",
        {
            "a.py": _CONCRETE_DEF,
            "b.py": "from .a import Backend\nthing: Backend = ...  # type: ignore\n",
        },
    ),
]


_SLD802_ABSENT: list[tuple[str, dict[str, str]]] = [
    (
        "protocol_in_annotation",
        {
            "a.py": _PROTOCOL_DEF,
            "b.py": "from .a import Backend\ndef run(b: Backend) -> None: ...\n",
        },
    ),
    (
        "primitive_only",
        {
            "b.py": "def add(x: int, y: int) -> int: ...\n",
        },
    ),
    (
        "abstract_container_only",
        {
            "b.py": (
                "from typing import Mapping, Sequence\n"
                "def collect(items: Sequence[str], counts: Mapping[str, int]):\n"
                "    ...\n"
            ),
        },
    ),
    (
        "concrete_in_private_function",
        {
            "a.py": _CONCRETE_DEF,
            "b.py": "from .a import Backend\ndef _run(b: Backend) -> None: ...\n",
        },
    ),
    (
        "concrete_in_private_module",
        {
            "a.py": _CONCRETE_DEF,
            "_b.py": "from .a import Backend\ndef run(b: Backend) -> None: ...\n",
        },
    ),
    (
        "concrete_in_private_class",
        {
            "a.py": _CONCRETE_DEF,
            "b.py": (
                "from .a import Backend\n" "class _Driver:\n" "    backend: Backend\n"
            ),
        },
    ),
    (
        "concrete_in_private_attribute",
        {
            "a.py": _CONCRETE_DEF,
            "b.py": (
                "from .a import Backend\n" "class Driver:\n" "    _backend: Backend\n"
            ),
        },
    ),
    (
        "unknown_third_party_name",
        {
            "b.py": "def handle(req: Request) -> Response: ...\n",
        },
    ),
    (
        "name_with_protocol_definition_elsewhere",
        {
            "a.py": _CONCRETE_DEF,
            "p.py": _PROTOCOL_DEF,
            "b.py": "from .p import Backend\ndef run(b: Backend) -> None: ...\n",
        },
    ),
]


_SLD803_PRESENT: list[tuple[str, dict[str, str]]] = [
    (
        "list_param",
        {"b.py": "def join(items: list[str]) -> str: ...\n"},
    ),
    (
        "dict_return",
        {"b.py": "def counts() -> dict[str, int]: ...\n"},
    ),
    (
        "set_param",
        {"b.py": "def unique(items: set[int]) -> int: ...\n"},
    ),
    (
        "frozenset_param",
        {"b.py": "def keys(s: frozenset[str]) -> None: ...\n"},
    ),
    (
        "nested_list_in_sequence",
        {
            "b.py": (
                "from typing import Sequence\n"
                "def fan(rows: Sequence[list[str]]) -> None: ...\n"
            ),
        },
    ),
]


_SLD803_ABSENT: list[tuple[str, dict[str, str]]] = [
    (
        "sequence_instead_of_list",
        {
            "b.py": (
                "from typing import Sequence\n"
                "def join(items: Sequence[str]) -> str: ...\n"
            ),
        },
    ),
    (
        "mapping_instead_of_dict",
        {
            "b.py": (
                "from typing import Mapping\n"
                "def counts(c: Mapping[str, int]) -> None: ...\n"
            ),
        },
    ),
    (
        "list_in_private_function",
        {"b.py": "def _join(items: list[str]) -> str: ...\n"},
    ),
]


_SLD804_PRESENT: list[tuple[str, dict[str, str]]] = [
    (
        "variadic_tuple",
        {"b.py": "def pack(xs: tuple[int, ...]) -> None: ...\n"},
    ),
    (
        "variadic_in_return",
        {"b.py": "def grab() -> tuple[str, ...]: ...\n"},
    ),
]


_SLD804_ABSENT: list[tuple[str, dict[str, str]]] = [
    (
        "fixed_arity_tuple",
        {"b.py": "def pair() -> tuple[int, str]: ...\n"},
    ),
    (
        "fixed_arity_with_two_elements",
        {"b.py": "def pair(p: tuple[int, str]) -> None: ...\n"},
    ),
    (
        "variadic_in_private_module",
        {"_b.py": "def pack(xs: tuple[int, ...]) -> None: ...\n"},
    ),
]


def _assert_present(test: unittest.TestCase, cases, code: str) -> None:
    for name, files in cases:
        with test.subTest(name=name):
            codes = multifile_codes(files)
            assert_that(codes, has_item(code))


def _assert_absent(test: unittest.TestCase, cases, code: str) -> None:
    for name, files in cases:
        with test.subTest(name=name):
            codes = multifile_codes(files)
            assert_that(_just(codes, code), empty())


class TestSLD802ConcreteClass(unittest.TestCase):
    """Tests for SLD802: public annotation references concrete class."""

    def test_present(self) -> None:
        """Verify present cases emit SLD802."""
        _assert_present(self, _SLD802_PRESENT, "SLD802")

    def test_absent(self) -> None:
        """Verify absent cases emit no SLD802."""
        _assert_absent(self, _SLD802_ABSENT, "SLD802")


class TestSLD803ConcreteContainer(unittest.TestCase):
    """Tests for SLD803: public annotation uses concrete container."""

    def test_present(self) -> None:
        """Verify present cases emit SLD803."""
        _assert_present(self, _SLD803_PRESENT, "SLD803")

    def test_absent(self) -> None:
        """Verify absent cases emit no SLD803."""
        _assert_absent(self, _SLD803_ABSENT, "SLD803")


class TestSLD804VariadicTuple(unittest.TestCase):
    """Tests for SLD804: public annotation uses variadic tuple."""

    def test_present(self) -> None:
        """Verify present cases emit SLD804."""
        _assert_present(self, _SLD804_PRESENT, "SLD804")

    def test_absent(self) -> None:
        """Verify absent cases emit no SLD804."""
        _assert_absent(self, _SLD804_ABSENT, "SLD804")


class TestComposition(unittest.TestCase):
    """Tests for SLD80x interactions: nested forms, multiple violations."""

    def test_list_of_concrete_emits_both(self) -> None:
        """Verify ``list[Concrete]`` emits both SLD803 and SLD802."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": (
                    "from .a import Backend\n"
                    "def fan(out: list[Backend]) -> None: ...\n"
                ),
            }
        )
        assert_that(codes, has_item("SLD803"))
        assert_that(codes, has_item("SLD802"))

    def test_noqa_suppresses_sld802(self) -> None:
        """Verify ``# noqa: SLD802`` suppresses one violation."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": (
                    "from .a import Backend\n"
                    "def run(b: Backend) -> None: ...  # noqa: SLD802\n"
                ),
            }
        )
        assert_that(_just(codes, "SLD802"), empty())

    def test_bare_noqa_suppresses_sld802(self) -> None:
        """Verify a bare ``# noqa`` suppresses every code."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": (
                    "from .a import Backend\n"
                    "def run(b: Backend) -> None: ...  # noqa\n"
                ),
            }
        )
        assert_that(_just(codes, "SLD802"), empty())

    def test_noqa_other_code_does_not_suppress(self) -> None:
        """Verify ``# noqa: SLD801`` does not suppress SLD802."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": (
                    "from .a import Backend\n"
                    "def run(b: Backend) -> None: ...  # noqa: SLD801\n"
                ),
            }
        )
        assert_that(codes, has_item("SLD802"))

    def test_callable_annotation_recurses(self) -> None:
        """Verify ``Callable[[Concrete], Concrete]`` flags both positions."""
        files = {
            "a.py": _CONCRETE_DEF,
            "b.py": (
                "from typing import Callable\n"
                "from .a import Backend\n"
                "def install(fn: Callable[[Backend], Backend]) -> None: ...\n"
            ),
        }
        codes = multifile_codes(files)
        assert_that(_just(codes, "SLD802"), is_not(empty()))
        assert_that(len(_just(codes, "SLD802")), equal_to(2))

    def test_optional_concrete_flags(self) -> None:
        """Verify ``Optional[Concrete]`` flags the concrete."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": (
                    "from typing import Optional\n"
                    "from .a import Backend\n"
                    "def maybe() -> Optional[Backend]: ...\n"
                ),
            }
        )
        assert_that(codes, has_item("SLD802"))

    def test_annotated_recurses_into_first(self) -> None:
        """Verify ``Annotated[Concrete, ...]`` flags the concrete."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": (
                    "from typing import Annotated\n"
                    "from .a import Backend\n"
                    "def take(x: Annotated[Backend, 'tag']) -> None: ...\n"
                ),
            }
        )
        assert_that(codes, has_item("SLD802"))

    def test_type_subscript_recurses(self) -> None:
        """Verify ``type[Concrete]`` flags the concrete."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": "from .a import Backend\ndef cls() -> type[Backend]: ...\n",
            }
        )
        assert_that(codes, has_item("SLD802"))

    def test_literal_subscript_allowed(self) -> None:
        """Verify ``Literal[...]`` does not recurse into its arguments."""
        codes = multifile_codes(
            {
                "b.py": (
                    "from typing import Literal\n"
                    "def pick(x: Literal['a', 'b']) -> None: ...\n"
                ),
            }
        )
        assert_that(_just(codes, "SLD80"), empty())


class TestEnumAndTypedDict(unittest.TestCase):
    """Tests for enum/TypedDict/NamedTuple as allowed contract kinds."""

    def test_enum_in_annotation_is_allowed(self) -> None:
        """Verify Enum subclasses do not trip SLD802."""
        codes = multifile_codes(
            {
                "a.py": (
                    "from enum import Enum\n"
                    "class Status(Enum):\n"
                    "    OPEN = 1\n"
                    "    CLOSED = 2\n"
                ),
                "b.py": "from .a import Status\ndef pick(s: Status) -> None: ...\n",
            }
        )
        assert_that(_just(codes, "SLD802"), empty())

    def test_typed_dict_in_annotation_is_allowed(self) -> None:
        """Verify TypedDict subclasses do not trip SLD802."""
        codes = multifile_codes(
            {
                "a.py": (
                    "from typing import TypedDict\n"
                    "class Row(TypedDict):\n"
                    "    name: str\n"
                ),
                "b.py": "from .a import Row\ndef take(r: Row) -> None: ...\n",
            }
        )
        assert_that(_just(codes, "SLD802"), empty())

    def test_named_tuple_in_annotation_is_allowed(self) -> None:
        """Verify NamedTuple subclasses do not trip SLD802."""
        codes = multifile_codes(
            {
                "a.py": (
                    "from typing import NamedTuple\n"
                    "class Point(NamedTuple):\n"
                    "    x: int\n"
                    "    y: int\n"
                ),
                "b.py": "from .a import Point\ndef take(p: Point) -> None: ...\n",
            }
        )
        assert_that(_just(codes, "SLD802"), empty())

    def test_abc_in_annotation_is_allowed(self) -> None:
        """Verify ABC subclasses do not trip SLD802."""
        codes = multifile_codes(
            {
                "a.py": ("from abc import ABC\n" "class Reader(ABC):\n" "    pass\n"),
                "b.py": "from .a import Reader\ndef take(r: Reader) -> None: ...\n",
            }
        )
        assert_that(_just(codes, "SLD802"), empty())


class TestAnnotationForms(unittest.TestCase):
    """Tests for less-common annotation expression forms."""

    def test_dotted_subscript_recurses_into_value(self) -> None:
        """Verify ``typing.Mapping[Concrete, int]`` flags the concrete arg."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": (
                    "import typing\n"
                    "from .a import Backend\n"
                    "def take(m: typing.Mapping[Backend, int]) -> None: ...\n"
                ),
            }
        )
        assert_that(codes, has_item("SLD802"))

    def test_callable_with_ellipsis_args(self) -> None:
        """Verify ``Callable[..., Concrete]`` flags the concrete return."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": (
                    "from typing import Callable\n"
                    "from .a import Backend\n"
                    "def install(fn: Callable[..., Backend]) -> None: ...\n"
                ),
            }
        )
        assert_that(codes, has_item("SLD802"))

    def test_dotted_attribute_annotation(self) -> None:
        """Verify a bare ``pkg.Foo`` Attribute annotation is classified by ``Foo``."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": ("from . import a\n" "def take(b: a.Backend) -> None: ...\n"),
            }
        )
        assert_that(codes, has_item("SLD802"))

    def test_init_module_is_public(self) -> None:
        """Verify ``__init__.py`` is a public module despite the underscores."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "pkg/__init__.py": (
                    "from ..a import Backend\n" "def reset(b: Backend) -> None: ...\n"
                ),
            }
        )
        assert_that(codes, has_item("SLD802"))


class TestSyntaxErrorAndReporting(unittest.TestCase):
    """Tests for scanner robustness and diagnostic format."""

    def test_syntax_error_skipped(self) -> None:
        """Verify a file with a syntax error does not crash the scanner."""
        codes = multifile_codes(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": "def f(\n",
                "c.py": "from .a import Backend\ndef run(b: Backend) -> None: ...\n",
            }
        )
        assert_that(codes, has_item("SLD802"))

    def test_message_includes_class_name(self) -> None:
        """Verify the SLD802 diagnostic message mentions the offending class."""
        result = check_multifile(
            {
                "a.py": _CONCRETE_DEF,
                "b.py": "from .a import Backend\ndef run(b: Backend) -> None: ...\n",
            }
        )
        sld802 = [item for item in result if "SLD802" in item[3]]
        assert_that(sld802, is_not(empty()))
        for _, _, _, message in sld802:
            assert_that("Backend" in message, equal_to(True))

    def test_message_includes_container_name(self) -> None:
        """Verify the SLD803 diagnostic message mentions the offending container."""
        result = check_multifile({"b.py": "def f(xs: list[int]) -> None: ...\n"})
        sld803 = [item for item in result if "SLD803" in item[3]]
        assert_that(sld803, is_not(empty()))
        for _, _, _, message in sld803:
            assert_that("list" in message, equal_to(True))
