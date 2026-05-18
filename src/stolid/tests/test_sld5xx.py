"""Tests for SLD5xx error codes (dataclass related)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, empty, has_item

from .code_parser import assert_absent, assert_present, get_error_codes

_SLD501_PRESENT: list[tuple[str, str]] = [
    (
        "no_frozen",
        "from dataclasses import dataclass\n\n@dataclass\n"
        "class MyClass:\n    x: int\n",
    ),
    (
        "frozen_false",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=False, slots=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n",
    ),
    (
        "non_constant_kwarg",
        "from dataclasses import dataclass\n\nFROZEN = True\n\n"
        "@dataclass(frozen=FROZEN, slots=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n",
    ),
]


_SLD501_ABSENT: list[tuple[str, str]] = [
    (
        "frozen_true",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n",
    ),
]


_SLD502_PRESENT: list[tuple[str, str]] = [
    (
        "no_slots",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n",
    ),
    (
        "slots_false",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=False, kw_only=True)\n"
        "class MyClass:\n    x: int\n",
    ),
]


_SLD502_ABSENT: list[tuple[str, str]] = [
    (
        "slots_true",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n",
    ),
]


_SLD503_PRESENT: list[tuple[str, str]] = [
    (
        "no_kw_only",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True)\n"
        "class MyClass:\n    x: int\n",
    ),
    (
        "kw_only_false",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=False)\n"
        "class MyClass:\n    x: int\n",
    ),
]


_SLD503_ABSENT: list[tuple[str, str]] = [
    (
        "kw_only_true",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n",
    ),
]


_NO_SLD50X: list[tuple[str, str]] = [
    (
        "all_flags",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n",
    ),
    (
        "extra_kwargs",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True, order=True, eq=True)\n"
        "class MyClass:\n    x: int\n",
    ),
    (
        "multiple_decorators",
        "from dataclasses import dataclass\n\n"
        "def log_class(cls):\n    return cls\n\n"
        "@log_class\n@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n",
    ),
    (
        "random_decorator_call",
        "@some_random_decorator()\nclass MyClass:\n    x: int\n",
    ),
    (
        "subscript_decorator",
        "decorators = [lambda x: x]\n\n" "@decorators[0]\nclass MyClass:\n    x: int\n",
    ),
    (
        "non_dataclass_decorator",
        "def my_decorator(cls):\n    return cls\n\n"
        "@my_decorator\nclass MyClass:\n    pass\n",
    ),
]


class TestSLD501FrozenDataclass(unittest.TestCase):
    """Tests for SLD501: Dataclass missing frozen=True."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD501_PRESENT, "SLD501")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD501_ABSENT, "SLD501")


class TestSLD502SlotsDataclass(unittest.TestCase):
    """Tests for SLD502: Dataclass missing slots=True."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD502_PRESENT, "SLD502")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD502_ABSENT, "SLD502")


class TestSLD503KwOnlyDataclass(unittest.TestCase):
    """Tests for SLD503: Dataclass missing kw_only=True."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD503_PRESENT, "SLD503")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD503_ABSENT, "SLD503")


class TestDataclassVariants(unittest.TestCase):
    """Tests for dataclass decorator variants."""

    def test_dataclasses_module_prefix_flags_all(self) -> None:
        """Verify dataclasses module prefix flags all."""
        source = (
            "import dataclasses\n\n"
            "@dataclasses.dataclass\nclass MyClass:\n    x: int\n"
        )
        codes = get_error_codes(source)
        for sld in ("SLD501", "SLD502", "SLD503"):
            with self.subTest(code=sld):
                assert_that(codes, has_item(sld))

    def test_no_sld50x_reported(self) -> None:
        """Verify no sld50x reported."""
        for name, source in _NO_SLD50X:
            with self.subTest(name=name):
                codes = get_error_codes(source)
                assert_that([c for c in codes if c.startswith("SLD50")], empty())
