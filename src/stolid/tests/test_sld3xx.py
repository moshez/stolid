"""Tests for SLD3xx error codes (init, private methods, public access)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, equal_to

from .code_parser import assert_absent, assert_present, get_error_codes

_SLD301_PRESENT: list[tuple[str, str]] = [
    (
        "init_in_regular_class",
        "class MyClass:\n    def __init__(self):\n        pass\n",
    ),
    (
        "init_explicitly_in_dataclass_flagged",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n\n"
        "    def __init__(self):\n        pass\n",
    ),
    (
        "init_in_testcase_flagged",
        "import unittest\n\nclass MyTest(unittest.TestCase):\n"
        "    def __init__(self, *args, **kwargs):\n"
        "        super().__init__(*args, **kwargs)\n",
    ),
    (
        "post_init_in_dataclass_flagged",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n\n"
        "    def __post_init__(self):\n        pass\n",
    ),
    (
        "post_init_in_regular_class_flagged",
        "class MyClass:\n" "    def __post_init__(self):\n        pass\n",
    ),
]


_SLD301_ABSENT: list[tuple[str, str]] = [
    (
        "dataclass_no_explicit_init",
        "from dataclasses import dataclass\n\n"
        "@dataclass(frozen=True, slots=True, kw_only=True)\n"
        "class MyClass:\n    x: int\n",
    ),
    (
        "other_dunders_allowed",
        "class MyClass:\n"
        "    def __str__(self):\n        return 'MyClass'\n\n"
        "    def __repr__(self):\n        return 'MyClass()'\n\n"
        "    def __eq__(self, other):\n        return True\n\n"
        "    def __hash__(self):\n        return 0\n\n"
        "    def __call__(self):\n        return None\n",
    ),
]


_SLD302_PRESENT: list[tuple[str, str]] = [
    (
        "private_method",
        "class MyClass:\n" "    def _private_method(self):\n        pass\n",
    ),
    (
        "double_underscore_private",
        "class MyClass:\n" "    def __very_private(self):\n        pass\n",
    ),
]


_SLD302_ABSENT: list[tuple[str, str]] = [
    (
        "dunder_methods_allowed",
        "class MyClass:\n"
        "    def __str__(self):\n        return 'MyClass'\n\n"
        "    def __repr__(self):\n        return 'MyClass()'\n\n"
        "    def __eq__(self, other):\n        return True\n",
    ),
    (
        "public_method_allowed",
        "class MyClass:\n    def public_method(self):\n        pass\n",
    ),
]


_SLD303_PRESENT: list[tuple[str, str]] = [
    (
        "method_accesses_only_public",
        "class MyClass:\n"
        "    def format(self):\n"
        "        return f'{self.name}: {self.value}'\n",
    ),
    (
        "method_no_self_access",
        "class MyClass:\n    def compute(self):\n        return 42\n",
    ),
    (
        "decorator_not_name_or_attribute_or_call",
        "class MyClass:\n    @(some_list[0])\n"
        "    def method(self):\n        return self.value\n",
    ),
    (
        "method_decorator_attribute_not_abstractmethod",
        "class MyClass:\n    @some_module.some_decorator\n"
        "    def method(self):\n        return self.value\n",
    ),
]


_SLD303_ABSENT: list[tuple[str, str]] = [
    (
        "method_accesses_private_allowed",
        "class MyClass:\n    def process(self):\n        return self._data + 1\n",
    ),
    (
        "method_accesses_mixed",
        "class MyClass:\n    def process(self):\n"
        "        return f'{self.name}: {self._internal}'\n",
    ),
    (
        "async_method_with_private_access",
        "class MyClass:\n    async def fetch(self):\n        return self._data\n",
    ),
    (
        "dunder_method_exempt",
        "class MyClass:\n    def __str__(self):\n        return self.name\n",
    ),
    (
        "property_exempt",
        "class MyClass:\n    @property\n    def name(self):\n"
        "        return self.first_name + ' ' + self.last_name\n",
    ),
    (
        "setter_exempt",
        "class MyClass:\n    @name.setter\n"
        "    def name(self, value):\n        self.first_name = value\n",
    ),
    (
        "classmethod_exempt",
        "class MyClass:\n    @classmethod\n"
        "    def create(cls):\n        return cls()\n",
    ),
    (
        "staticmethod_exempt",
        "class MyClass:\n    @staticmethod\n" "    def helper():\n        return 42\n",
    ),
    (
        "classmethod_via_attribute",
        "import builtins\n\nclass MyClass:\n"
        "    @builtins.classmethod\n"
        "    def create(cls):\n        return cls()\n",
    ),
    (
        "staticmethod_via_attribute",
        "import builtins\n\nclass MyClass:\n"
        "    @builtins.staticmethod\n"
        "    def helper():\n        return 42\n",
    ),
    (
        "staticmethod_via_attribute_with_self",
        "class MyClass:\n    @types.staticmethod\n"
        "    def helper(self):\n        return self.value\n",
    ),
    (
        "classmethod_via_attribute_with_self",
        "class MyClass:\n    @functools.classmethod\n"
        "    def create(self):\n        return self\n",
    ),
    (
        "staticmethod_name_with_self_param",
        "class MyClass:\n    @staticmethod\n"
        "    def method(self):\n        return self\n",
    ),
    (
        "classmethod_name_with_self_param",
        "class MyClass:\n    @classmethod\n"
        "    def method(self):\n        return self\n",
    ),
]


class TestSLD301InitProhibited(unittest.TestCase):
    """Tests for SLD301: __init__ method is prohibited."""

    def test_present(self) -> None:
        assert_present(self, _SLD301_PRESENT, "SLD301")

    def test_absent(self) -> None:
        assert_absent(self, _SLD301_ABSENT, "SLD301")


class TestSLD302PrivateMethodsProhibited(unittest.TestCase):
    """Tests for SLD302: Private methods are prohibited."""

    def test_present(self) -> None:
        assert_present(self, _SLD302_PRESENT, "SLD302")

    def test_absent(self) -> None:
        assert_absent(self, _SLD302_ABSENT, "SLD302")


class TestSLD303PublicAccess(unittest.TestCase):
    """Tests for SLD303: methods that don't access private state."""

    def test_present(self) -> None:
        assert_present(self, _SLD303_PRESENT, "SLD303")

    def test_absent(self) -> None:
        assert_absent(self, _SLD303_ABSENT, "SLD303")

    def test_function_without_self_no_lint(self) -> None:
        codes = get_error_codes(
            "class MyClass:\n    def not_a_method():\n        pass\n"
        )
        for sld in ("SLD301", "SLD302", "SLD303"):
            with self.subTest(code=sld):
                assert_that(sld in codes, equal_to(False))
