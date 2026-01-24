"""Tests for SLD1xx error codes (patch/mock related)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, empty, equal_to, has_item

from .code_parser import get_error_codes


class TestSLD102Import(unittest.TestCase):
    """Tests for SLD102: patch import detection."""

    def test_import_patch_from_unittest_mock(self) -> None:
        code = """
        from unittest.mock import patch
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD102"))

    def test_import_patch_from_mock(self) -> None:
        code = """
        from mock import patch
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD102"))

    def test_mock_import_allowed(self) -> None:
        """Importing Mock itself is allowed, only patch is prohibited."""
        code = """
        from unittest.mock import Mock, MagicMock
        """
        codes = get_error_codes(code)
        assert_that(codes, empty())

    def test_patch_aliased_import(self) -> None:
        code = """
        from unittest.mock import patch as p

        p("module.thing")
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(True))

    def test_import_patch_among_multiple(self) -> None:
        """Import patch among other imports from unittest.mock."""
        code = """
        from unittest.mock import Mock, patch, MagicMock
        """
        codes = get_error_codes(code)
        stolid102_count = codes.count("SLD102")
        assert_that(stolid102_count, equal_to(1))


class TestSLD102Usage(unittest.TestCase):
    """Tests for SLD102: patch usage detection."""

    def test_patch_decorator(self) -> None:
        code = """
        from unittest.mock import patch

        @patch("module.thing")
        def test_something():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD102"))

    def test_patch_context_manager(self) -> None:  # noqa: SLD701
        code = """
        from unittest.mock import patch

        def test_something():
            with patch("module.thing"):
                pass
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(True))

    def test_patch_object_call(self) -> None:
        code = """
        from unittest.mock import patch

        def test_something():
            patch.object(obj, "attr")
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(True))

    def test_unittest_mock_patch_attribute_access(self) -> None:
        code = """
        import unittest.mock

        unittest.mock.patch("thing")
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD102"))

    def test_mock_module_patch_attribute(self) -> None:
        code = """
        import mock

        mock.patch("thing")
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD102"))

    def test_patch_object_via_mock_module_attribute(self) -> None:
        """Test mock.patch.object() detection via attribute chain."""
        code = """
        import unittest.mock

        unittest.mock.patch.object(obj, "attr")
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD102"))

    def test_attribute_patch_on_nested_attribute(self) -> None:
        """Test deeply nested attribute access for patch."""
        code = """
        import unittest

        unittest.mock.patch("thing")
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD102"))

    def test_patch_object_via_deeply_nested_attribute(self) -> None:
        """Test a.b.patch.object() detection."""
        code = """
        import unittest

        unittest.mock.patch.object(obj, "attr")
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD102"))


class TestSLD102EdgeCases(unittest.TestCase):
    """Tests for SLD102: edge cases and non-matches."""

    def test_with_statement_non_call(self) -> None:
        """With statement with non-Call context expression."""
        code = """
        class MyClass:
            pass

        with some_context:
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(False))

    def test_with_statement_call_non_name(self) -> None:
        """With statement with Call but func is not Name."""
        code = """
        with obj.method():
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(False))

    def test_patch_attribute_not_mock(self) -> None:
        """Attribute named 'patch' but not on mock module."""
        code = """
        class MyPatcher:
            patch = None

        obj = MyPatcher()
        obj.patch
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(False))

    def test_attribute_patch_on_non_mock_name(self) -> None:
        """xxx.patch where xxx is not 'mock'."""
        code = """
        something.patch("value")
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(False))

    def test_call_with_attribute_func_not_object(self) -> None:
        """Call with attribute func but not 'object' attr."""
        code = """
        from unittest.mock import patch

        patch.dict({})
        """
        codes = get_error_codes(code)
        stolid102_count = codes.count("SLD102")
        assert_that(stolid102_count, equal_to(1))

    def test_patch_object_with_non_patch_name(self) -> None:
        """xxx.object() where xxx is not a patch name."""
        code = """
        something.object(1, 2)
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(False))

    def test_with_non_patch_function_call(self) -> None:
        """Test with statement calling function that's not patch."""
        code = """
        from unittest.mock import patch

        with open("file.txt"):
            pass
        """
        codes = get_error_codes(code)
        stolid102_count = codes.count("SLD102")
        assert_that(stolid102_count, equal_to(1))

    def test_attribute_patch_nested_not_mock(self) -> None:
        """Test foo.bar.patch where bar is not 'mock'."""
        code = """
        foo.bar.patch
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(False))

    def test_call_func_attribute_not_object(self) -> None:
        """Test func.something() where attr is not 'object'."""
        code = """
        from unittest.mock import patch

        result = patch.dict({})
        """
        codes = get_error_codes(code)
        stolid102_count = codes.count("SLD102")
        assert_that(stolid102_count, equal_to(1))

    def test_call_object_func_value_attribute_not_patch(self) -> None:
        """Test xxx.yyy.object() where yyy is not 'patch'."""
        code = """
        foo.bar.object(thing)
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(False))

    def test_call_object_func_value_name_not_patch(self) -> None:
        """Test notpatch.object() - func.value is Name but not in patch_names."""
        code = """
        factory.object(MyClass)
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(False))

    def test_call_func_is_attribute_not_object(self) -> None:
        """Call where func is Attribute but attr is not 'object'."""
        code = """
        from unittest.mock import patch

        x = patch.something("module")
        """
        codes = get_error_codes(code)
        stolid102_count = codes.count("SLD102")
        assert_that(stolid102_count, equal_to(1))

    def test_call_object_on_non_patch_attribute(self) -> None:
        """Test xxx.object() where xxx is not patch."""
        code = """
        factory.object(MyClass)
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(False))

    def test_patch_object_via_attribute_value_name_not_patch(self) -> None:
        """Test xxx.object() where xxx is Name but not in patch_names."""
        code = """
        something.object(obj, "attr")
        """
        codes = get_error_codes(code)
        assert_that("SLD102" in codes, equal_to(False))
