"""Tests for SLD802/SLD803/SLD804 — base present/absent cases."""

from __future__ import annotations

import unittest

from ._sld80x_shared import CONCRETE_DEF, PROTOCOL_DEF, assert_absent, assert_present

_SLD802_PRESENT: list[tuple[str, dict[str, str]]] = [
    (
        "concrete_in_arg",
        {
            "a.py": CONCRETE_DEF,
            "b.py": "from .a import Backend\ndef run(b: Backend) -> None: ...\n",
        },
    ),
    (
        "concrete_in_return",
        {
            "a.py": CONCRETE_DEF,
            "b.py": "from .a import Backend\ndef make() -> Backend: ...\n",
        },
    ),
    (
        "concrete_inside_sequence",
        {
            "a.py": CONCRETE_DEF,
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
            "a.py": CONCRETE_DEF,
            "b.py": ("from .a import Backend\n" "def maybe() -> Backend | None: ...\n"),
        },
    ),
    (
        "concrete_in_dataclass_field",
        {
            "a.py": CONCRETE_DEF,
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
            "a.py": CONCRETE_DEF,
            "b.py": "from .a import Backend\nthing: Backend = ...  # type: ignore\n",
        },
    ),
    (
        "concrete_in_public_function_of_private_module",
        {
            "a.py": CONCRETE_DEF,
            "_b.py": "from .a import Backend\ndef run(b: Backend) -> None: ...\n",
        },
    ),
]


_SLD802_ABSENT: list[tuple[str, dict[str, str]]] = [
    (
        "protocol_in_annotation",
        {
            "a.py": PROTOCOL_DEF,
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
            "a.py": CONCRETE_DEF,
            "b.py": "from .a import Backend\ndef _run(b: Backend) -> None: ...\n",
        },
    ),
    (
        "concrete_in_private_function_of_private_module",
        {
            "a.py": CONCRETE_DEF,
            "_b.py": "from .a import Backend\ndef _run(b: Backend) -> None: ...\n",
        },
    ),
    (
        "concrete_in_private_class",
        {
            "a.py": CONCRETE_DEF,
            "b.py": (
                "from .a import Backend\n" "class _Driver:\n" "    backend: Backend\n"
            ),
        },
    ),
    (
        "concrete_in_private_attribute",
        {
            "a.py": CONCRETE_DEF,
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
            "a.py": CONCRETE_DEF,
            "p.py": PROTOCOL_DEF,
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
    (
        "list_in_public_function_of_private_module",
        {"_b.py": "def join(items: list[str]) -> str: ...\n"},
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
    (
        "variadic_in_public_function_of_private_module",
        {"_b.py": "def pack(xs: tuple[int, ...]) -> None: ...\n"},
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
        "variadic_in_private_function_of_private_module",
        {"_b.py": "def _pack(xs: tuple[int, ...]) -> None: ...\n"},
    ),
]


class TestSLD802ConcreteClass(unittest.TestCase):
    """Tests for SLD802: public annotation references concrete class."""

    def test_present(self) -> None:
        """Verify present cases emit SLD802."""
        assert_present(self, _SLD802_PRESENT, "SLD802")

    def test_absent(self) -> None:
        """Verify absent cases emit no SLD802."""
        assert_absent(self, _SLD802_ABSENT, "SLD802")


class TestSLD803ConcreteContainer(unittest.TestCase):
    """Tests for SLD803: public annotation uses concrete container."""

    def test_present(self) -> None:
        """Verify present cases emit SLD803."""
        assert_present(self, _SLD803_PRESENT, "SLD803")

    def test_absent(self) -> None:
        """Verify absent cases emit no SLD803."""
        assert_absent(self, _SLD803_ABSENT, "SLD803")


class TestSLD804VariadicTuple(unittest.TestCase):
    """Tests for SLD804: public annotation uses variadic tuple."""

    def test_present(self) -> None:
        """Verify present cases emit SLD804."""
        assert_present(self, _SLD804_PRESENT, "SLD804")

    def test_absent(self) -> None:
        """Verify absent cases emit no SLD804."""
        assert_absent(self, _SLD804_ABSENT, "SLD804")
