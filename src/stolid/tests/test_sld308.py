"""Tests for SLD308 (peer module-level identifier-valued string constants)."""

from __future__ import annotations

import unittest

from .code_parser import assert_absent, assert_count, assert_present

_SLD308_PRESENT: list[tuple[str, str]] = [
    (
        "two_upper_case_identifier_constants",
        "OPEN = 'open'\nCLOSED = 'closed'\n",
    ),
    (
        "lowercase_name_still_flagged",
        "open_status = 'open'\nclosed_status = 'closed'\n",
    ),
    (
        "annotated_assignments",
        "FIRST: str = 'first'\nSECOND: str = 'second'\n",
    ),
    (
        "mixed_annotated_and_plain",
        "FIRST: str = 'first'\nSECOND = 'second'\nTHIRD = 'third'\n",
    ),
    (
        "underscored_identifier_value",
        "READ = 'private_read'\nWRITE = 'private_write'\n",
    ),
]


_SLD308_ABSENT: list[tuple[str, str]] = [
    (
        "single_identifier_constant",
        "DEFAULT = 'anonymous'\n",
    ),
    (
        "values_with_spaces_not_identifiers",
        "GREETING = 'hello world'\nFAREWELL = 'good bye'\n",
    ),
    (
        "values_with_dots_not_identifiers",
        "HOST = 'example.com'\nPATH = 'a.b.c'\n",
    ),
    (
        "non_string_constants",
        "X = 1\nY = 2\nZ = 3\n",
    ),
    (
        "string_inside_class_body",
        "class K:\n    A = 'one'\n    B = 'two'\n",
    ),
    (
        "string_inside_function_body",
        "def f():\n    A = 'one'\n    B = 'two'\n",
    ),
    (
        "tuple_unpacking_assignment",
        "A, B = 'one', 'two'\n",
    ),
    (
        "value_is_attribute_not_constant",
        "import os\nA = os.linesep\nB = os.linesep\n",
    ),
    (
        "annotation_only_no_value",
        "A: str\nB: str\n",
    ),
    (
        "annassign_with_attribute_target",
        "import types\nobj = types.SimpleNamespace()\nobj.x: str = 'foo'\n",
    ),
    (
        "empty_string_not_identifier",
        "A = ''\nB = ''\n",
    ),
    (
        "starts_with_digit_not_identifier",
        "A = '1abc'\nB = '2xyz'\n",
    ),
]


class TestSLD308ModuleStringConstants(unittest.TestCase):
    """SLD308: Module-level peer string constants with identifier values."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD308_PRESENT, "SLD308")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD308_ABSENT, "SLD308")

    def test_one_report_per_constant(self) -> None:
        """Verify one report per identifier-valued constant."""
        cases = [
            (
                "three_peers_three_reports",
                "A = 'one'\nB = 'two'\nC = 'three'\n",
                3,
            ),
            (
                "non_identifier_skipped_in_count",
                "A = 'one'\nB = 'hello world'\nC = 'three'\n",
                2,
            ),
        ]
        assert_count(self, cases, "SLD308")
