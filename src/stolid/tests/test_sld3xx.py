"""Tests for SLD3xx error codes (init, private methods, public access)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to, has_item

from .code_parser import get_error_codes


class TestSLD301InitProhibited(unittest.TestCase):
    """Tests for SLD301: __init__ method is prohibited."""

    def test_init_in_regular_class(self) -> None:
        code = """
        class MyClass:
            def __init__(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD301"))

    def test_dataclass_no_explicit_init(self) -> None:
        """Dataclass without explicit __init__ should not trigger SLD301."""
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int
        """
        codes = get_error_codes(code)
        assert_that("SLD301" in codes, equal_to(False))

    def test_init_explicitly_in_dataclass_flagged(self) -> None:
        """Explicit __init__ in dataclass should be flagged."""
        code = """
        from dataclasses import dataclass

        @dataclass(frozen=True, slots=True, kw_only=True)
        class MyClass:
            x: int

            def __init__(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD301"))

    def test_init_in_testcase_flagged(self) -> None:
        """TestCase __init__ is still flagged (no special handling)."""
        code = """
        import unittest

        class MyTest(unittest.TestCase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
        """
        codes = get_error_codes(code)
        assert_that("SLD301" in codes, equal_to(True))


class TestSLD302PrivateMethodsProhibited(unittest.TestCase):
    """Tests for SLD302: Private methods are prohibited."""

    def test_private_method(self) -> None:
        code = """
        class MyClass:
            def _private_method(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD302"))

    def test_double_underscore_private(self) -> None:
        code = """
        class MyClass:
            def __very_private(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD302"))

    def test_dunder_methods_allowed(self) -> None:
        code = """
        class MyClass:
            def __str__(self):
                return "MyClass"

            def __repr__(self):
                return "MyClass()"

            def __eq__(self, other):
                return True
        """
        codes = get_error_codes(code)
        assert_that("SLD302" in codes, equal_to(False))

    def test_public_method_allowed(self) -> None:
        code = """
        class MyClass:
            def public_method(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that("SLD302" in codes, equal_to(False))


class TestSLD303Detection(unittest.TestCase):
    """Tests for SLD303: Detection of methods that only access public members."""

    def test_method_accesses_only_public(self) -> None:
        code = """
        class MyClass:
            def format(self):
                return f"{self.name}: {self.value}"
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD303"))

    def test_method_accesses_private_allowed(self) -> None:
        code = """
        class MyClass:
            def process(self):
                return self._data + 1
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_method_accesses_mixed(self) -> None:
        """If method accesses both public and private, it's allowed."""
        code = """
        class MyClass:
            def process(self):
                return f"{self.name}: {self._internal}"
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_method_no_self_access_allowed(self) -> None:
        """Method that doesn't access self at all doesn't trigger SLD303."""
        code = """
        class MyClass:
            def compute(self):
                return 42
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_async_method_with_private_access(self) -> None:
        """Async method accessing private state."""
        code = """
        class MyClass:
            async def fetch(self):
                return self._data
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_decorator_not_name_or_attribute_or_call(self) -> None:
        """Decorator that is not Name, Attribute, or Call."""
        code = """
        class MyClass:
            @(some_list[0])
            def method(self):
                return self.value
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(True))

    def test_method_decorator_attribute_not_abstractmethod(self) -> None:
        """Decorator that is Attribute but not abstractmethod."""
        code = """
        class MyClass:
            @some_module.some_decorator
            def method(self):
                return self.value
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD303"))


class TestSLD303Exemptions(unittest.TestCase):
    """Tests for SLD303: Exemptions from public access check."""

    def test_dunder_method_exempt(self) -> None:
        """Dunder methods are exempt from SLD303."""
        code = """
        class MyClass:
            def __str__(self):
                return self.name
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_property_exempt(self) -> None:
        """Property methods are exempt from SLD303."""
        code = """
        class MyClass:
            @property
            def name(self):
                return self.first_name + " " + self.last_name
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_setter_exempt(self) -> None:
        """Property setters are exempt."""
        code = """
        class MyClass:
            @name.setter
            def name(self, value):
                self.first_name = value
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_classmethod_exempt(self) -> None:
        """Classmethods don't have self, so they're exempt."""
        code = """
        class MyClass:
            @classmethod
            def create(cls):
                return cls()
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_staticmethod_exempt(self) -> None:
        """Staticmethods don't have self."""
        code = """
        class MyClass:
            @staticmethod
            def helper():
                return 42
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_classmethod_via_attribute(self) -> None:
        """Test @builtins.classmethod detection."""
        code = """
        import builtins

        class MyClass:
            @builtins.classmethod
            def create(cls):
                return cls()
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_staticmethod_via_attribute(self) -> None:
        """Test @module.staticmethod detection."""
        code = """
        import builtins

        class MyClass:
            @builtins.staticmethod
            def helper():
                return 42
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_method_in_class_not_method(self) -> None:
        """Function in class without self parameter."""
        code = """
        class MyClass:
            def not_a_method():
                pass
        """
        codes = get_error_codes(code)
        assert_that("SLD301" in codes, equal_to(False))
        assert_that("SLD302" in codes, equal_to(False))
        assert_that("SLD303" in codes, equal_to(False))

    def test_staticmethod_via_attribute_with_self(self) -> None:
        """Test @module.staticmethod on a method with self param."""
        code = """
        class MyClass:
            @types.staticmethod
            def helper(self):
                return self.value
        """
        codes = get_error_codes(code)
        assert_that("SLD302" in codes, equal_to(False))
        assert_that("SLD303" in codes, equal_to(False))

    def test_classmethod_via_attribute_with_self(self) -> None:
        """Test @module.classmethod on a method with self param."""
        code = """
        class MyClass:
            @functools.classmethod
            def create(self):
                return self
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_staticmethod_name_with_self_param(self) -> None:
        """Test @staticmethod (Name) on method with self parameter."""
        code = """
        class MyClass:
            @staticmethod
            def method(self):
                return self
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))

    def test_classmethod_name_with_self_param(self) -> None:
        """Test @classmethod (Name) on method with self parameter."""
        code = """
        class MyClass:
            @classmethod
            def method(self):
                return self
        """
        codes = get_error_codes(code)
        assert_that("SLD303" in codes, equal_to(False))
