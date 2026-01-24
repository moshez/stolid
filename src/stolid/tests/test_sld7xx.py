"""Tests for SLD7xx error codes (naming conventions)."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, contains_string, equal_to, has_item

from .code_parser import check_code, get_error_codes


class TestSLD701BadClassNames(unittest.TestCase):
    """Tests for SLD701: Forbidden words in class names."""

    def test_class_with_helper_suffix(self) -> None:  # noqa: SLD701
        code = """
        class DiskHelper:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_class_with_util_suffix(self) -> None:  # noqa: SLD701
        code = """
        class DiskUtil:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_class_with_utils_suffix(self) -> None:  # noqa: SLD701
        code = """
        class StringUtils:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_class_with_manager_suffix(self) -> None:  # noqa: SLD701
        code = """
        class ConnectionManager:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_class_with_manage_suffix(self) -> None:  # noqa: SLD701
        code = """
        class DataManage:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_class_with_help_prefix(self) -> None:  # noqa: SLD701
        code = """
        class HelpProvider:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_class_standalone_helper(self) -> None:  # noqa: SLD701
        code = """
        class Helper:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_class_with_helpers_suffix(self) -> None:  # noqa: SLD701
        code = """
        class TestHelpers:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_class_with_managers_suffix(self) -> None:  # noqa: SLD701
        code = """
        class TaskManagers:
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_class_futile_no_error(self) -> None:
        """'Futile' should not match 'util' - not at word boundary."""
        code = """
        class Futile:
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD701" in codes, equal_to(False))

    def test_class_helpful_no_error(self) -> None:  # noqa: SLD701
        """'Helpful' should not match 'help' - word continues after."""
        code = """
        class Helpful:
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD701" in codes, equal_to(False))

    def test_class_utility_no_error(self) -> None:  # noqa: SLD701
        """'Utility' should not match 'util' - word continues after."""
        code = """
        class Utility:
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD701" in codes, equal_to(False))

    def test_class_management_no_error(self) -> None:  # noqa: SLD701
        """'Management' should not match 'manage' - word continues after."""
        code = """
        class Management:
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD701" in codes, equal_to(False))

    def test_class_clean_name_no_error(self) -> None:
        code = """
        class DiskReader:
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD701" in codes, equal_to(False))


class TestSLD701BadFunctionNames(unittest.TestCase):
    """Tests for SLD701: Forbidden words in function/method names."""

    def test_function_with_helper_suffix(self) -> None:  # noqa: SLD701
        code = """
        def get_helper():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_function_with_util_suffix(self) -> None:  # noqa: SLD701
        code = """
        def string_util():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_function_with_utils_suffix(self) -> None:  # noqa: SLD701
        code = """
        def get_utils():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_function_with_manager_suffix(self) -> None:  # noqa: SLD701
        code = """
        def get_manager():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_function_snake_case_helper_middle(self) -> None:  # noqa: SLD701
        code = """
        def create_helper_function():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_function_camel_case_helper_middle(self) -> None:  # noqa: SLD701
        code = """
        def createHelperFunction():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_function_helpful_no_error(self) -> None:  # noqa: SLD701
        code = """
        def is_helpful():
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD701" in codes, equal_to(False))

    def test_function_futile_no_error(self) -> None:
        code = """
        def is_futile():
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD701" in codes, equal_to(False))

    def test_async_function_with_helper(self) -> None:  # noqa: SLD701
        code = """
        async def async_helper():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_method_with_helper(self) -> None:  # noqa: SLD701
        code = """
        class MyClass:
            def my_helper(self):
                pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_clean_function_name_no_error(self) -> None:
        code = """
        def read_file():
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD701" in codes, equal_to(False))


class TestSLD701BadModuleNames(unittest.TestCase):
    """Tests for SLD701: Forbidden words in module names."""

    def test_module_name_with_helper(self) -> None:  # noqa: SLD701
        code = "x = 1"
        errors = check_code(code, filename="helper.py")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that(codes, has_item("SLD701"))

    def test_module_name_with_util(self) -> None:  # noqa: SLD701
        code = "x = 1"
        errors = check_code(code, filename="string_util.py")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that(codes, has_item("SLD701"))

    def test_module_name_with_utils(self) -> None:  # noqa: SLD701
        code = "x = 1"
        errors = check_code(code, filename="utils.py")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that(codes, has_item("SLD701"))

    def test_module_name_with_manager(self) -> None:  # noqa: SLD701
        code = "x = 1"
        errors = check_code(code, filename="connection_manager.py")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that(codes, has_item("SLD701"))

    def test_module_name_with_helpers(self) -> None:  # noqa: SLD701
        code = "x = 1"
        errors = check_code(code, filename="test_helpers.py")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that(codes, has_item("SLD701"))

    def test_module_name_with_managers(self) -> None:  # noqa: SLD701
        code = "x = 1"
        errors = check_code(code, filename="task_managers.py")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that(codes, has_item("SLD701"))

    def test_module_name_futile_no_error(self) -> None:
        code = "x = 1"
        errors = check_code(code, filename="futile.py")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that("SLD701" in codes, equal_to(False))

    def test_module_name_clean_no_error(self) -> None:
        code = "x = 1"
        errors = check_code(code, filename="reader.py")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that("SLD701" in codes, equal_to(False))

    def test_init_module_skipped(self) -> None:
        """__init__.py should not be checked."""
        code = "x = 1"
        errors = check_code(code, filename="__init__.py")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that("SLD701" in codes, equal_to(False))

    def test_no_filename_no_module_error(self) -> None:
        """When no filename is provided, no module name check."""
        code = "x = 1"
        errors = check_code(code, filename="")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that("SLD701" in codes, equal_to(False))

    def test_non_py_filename_no_module_error(self) -> None:
        """Non-.py files should not have module name checks."""
        code = "x = 1"
        errors = check_code(code, filename="helper.pyi")
        codes = [msg.split()[0] for _, _, msg in errors]
        assert_that("SLD701" in codes, equal_to(False))


class TestSLD701EdgeCases(unittest.TestCase):
    """Edge case tests for SLD701."""

    def test_error_message_includes_name_and_word(self) -> None:
        code = """
        class ConnectionManager:
            pass
        """
        errors = check_code(code)
        messages = [msg for _, _, msg in errors if "SLD701" in msg]
        assert_that(messages[0], contains_string("ConnectionManager"))
        assert_that(messages[0], contains_string("manager"))

    def test_all_caps_helper(self) -> None:  # noqa: SLD701
        """ALL_CAPS_HELPER should be flagged."""
        code = """
        def ALL_HELPER():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_mixed_case_util(self) -> None:  # noqa: SLD701
        """UTIL as a separate word in mixed case."""
        code = """
        class MyUTIL:
            pass
        """
        codes = get_error_codes(code)
        # UTIL follows lowercase 'y', so it should be treated as a word boundary
        assert_that(codes, has_item("SLD701"))

    def test_help_as_standalone_word(self) -> None:  # noqa: SLD701
        code = """
        def help():
            pass
        """
        codes = get_error_codes(code)
        assert_that(codes, has_item("SLD701"))

    def test_unhelpful_no_error(self) -> None:  # noqa: SLD701
        """'unhelpful' - 'help' is not at a word boundary."""
        code = """
        def unhelpful():
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD701" in codes, equal_to(False))

    def test_utilize_no_error(self) -> None:  # noqa: SLD701
        """'utilize' - 'util' is not at a word boundary."""
        code = """
        def utilize():
            pass
        """
        codes = get_error_codes(code)
        assert_that("SLD701" in codes, equal_to(False))
