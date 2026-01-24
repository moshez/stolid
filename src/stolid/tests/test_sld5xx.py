"""Tests for SLD5xx error codes (dataclass related)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, empty, equal_to, has_item

from .code_parser import get_error_codes


class TestSLD501FrozenDataclass(unittest.TestCase):
    """Tests for SLD501: Dataclass missing frozen=True."""

    def test_dataclass_no_frozen(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD501"))

    def test_dataclass_frozen_false(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=False, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD501"))

    def test_dataclass_frozen_true(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that("SLD501" in codes, equal_to(False))


class TestSLD502SlotsDataclass(unittest.TestCase):
    """Tests for SLD502: Dataclass missing slots=True."""

    def test_dataclass_no_slots(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD502"))

    def test_dataclass_slots_false(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=False, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD502"))

    def test_dataclass_slots_true(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that("SLD502" in codes, equal_to(False))


class TestSLD503KwOnlyDataclass(unittest.TestCase):
    """Tests for SLD503: Dataclass missing kw_only=True."""

    def test_dataclass_no_kw_only(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD503"))

    def test_dataclass_kw_only_false(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=False)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD503"))

    def test_dataclass_kw_only_true(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that("SLD503" in codes, equal_to(False))


class TestDataclassVariants(unittest.TestCase):
    """Tests for dataclass decorator variants."""

    def test_dataclasses_module_prefix(self) -> None:
        code = """
        import dataclasses

        @dataclasses.dataclass
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        # Should detect missing frozen, slots, kw_only
        assert_that(codes, has_item("SLD501"))
        assert_that(codes, has_item("SLD502"))
        assert_that(codes, has_item("SLD503"))

    def test_dataclass_with_all_flags(self) -> None:
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        lps50x = [c for c in codes if c.startswith("SLD50")]
        assert_that(lps50x, empty())

    def test_dataclass_with_non_constant_kwarg(self) -> None:
        """Dataclass with non-constant keyword argument value."""
        code = """
        from dataclasses import dataclass

        FROZEN = True

        @dataclass(frozen=FROZEN, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD501"))

    def test_dataclass_with_extra_kwargs(self) -> None:
        """Dataclass with extra keyword arguments."""
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True, order=True, eq=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        lps50x = [c for c in codes if c.startswith("SLD50")]
        assert_that(lps50x, empty())

    def test_non_dataclass_decorator_call(self) -> None:
        """Class with non-dataclass decorator that is a Call."""
        code = """
        def my_decorator(cls):
            return cls

        @my_decorator
        class MyClass:
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD501" in codes, equal_to(False))

    def test_class_with_multiple_decorators(self) -> None:
        """Class with multiple decorators including dataclass."""
        code = """
        from dataclasses import dataclass

        def log_class(cls):
            return cls

        @log_class
        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        lps50x = [c for c in codes if c.startswith("SLD50")]
        assert_that(lps50x, empty())

    def test_decorator_that_is_not_dataclass_but_is_call(self) -> None:
        """Test that random Call decorators don't trigger dataclass checks."""
        code = """
        @some_random_decorator()
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that("SLD501" in codes, equal_to(False))
        assert_that("SLD502" in codes, equal_to(False))
        assert_that("SLD503" in codes, equal_to(False))

    def test_class_decorator_is_subscript(self) -> None:
        """Class decorator that is a Subscript (not Name/Attribute/Call)."""
        code = """
        decorators = [lambda x: x]

        @decorators[0]
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that("SLD501" in codes, equal_to(False))
        assert_that("SLD502" in codes, equal_to(False))
        assert_that("SLD503" in codes, equal_to(False))
