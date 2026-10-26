"""Tests for SLD204: imports must be at the top of the module."""

from __future__ import annotations

import unittest

from hamcrest import assert_that, empty

from .code_parser import assert_absent, assert_count, assert_present, get_error_codes

_LATE_IMPORT_PRESENT: list[tuple[str, str]] = [
    ("import_after_assignment", "x = 1\nimport os\n"),
    ("from_import_after_assignment", "x = 1\nfrom os import path\n"),
    (
        "import_after_function_def",
        "def f():\n    pass\nimport os\n",
    ),
    ("import_inside_function", "def f():\n    import os\n"),
    (
        "from_import_inside_function",
        "def f():\n    from os import path\n",
    ),
    ("import_inside_class", "class C:\n    import os\n"),
    (
        "import_inside_method",
        "class C:\n    def m(self):\n        import os\n",
    ),
    ("import_inside_if_block", "if True:\n    import os\n"),
    (
        "import_inside_try",
        "try:\n    import os\nexcept ImportError:\n    pass\n",
    ),
    (
        "import_after_docstring_and_code",
        '"""Docstring."""\nx = 1\nimport os\n',
    ),
    (
        "import_after_non_docstring_expr",
        "1 + 1\nimport os\n",
    ),
    (
        "import_after_non_string_constant",
        "42\nimport os\n",
    ),
    (
        "passthrough_block_after_code",
        "from temporalio import workflow\n\nx = 1\n"
        "with workflow.unsafe.imports_passed_through():\n    import pandas\n",
    ),
    (
        "import_in_function_inside_passthrough_block",
        "from temporalio import workflow\n\n"
        "with workflow.unsafe.imports_passed_through():\n"
        "    def f():\n        import os\n",
    ),
    (
        "import_inside_ordinary_with_block",
        "with open('f') as handle:\n    import os\n",
    ),
    (
        "import_inside_with_non_call_manager",
        "with manager:\n    import os\n",
    ),
    (
        "import_inside_with_other_passthrough_owner",
        "with activity.unsafe.imports_passed_through():\n    import os\n",
    ),
    (
        "import_inside_with_passthrough_on_call_result",
        "with get_workflow().unsafe.imports_passed_through():\n    import os\n",
    ),
]


_LATE_IMPORT_ABSENT: list[tuple[str, str]] = [
    ("single_import", "import os\n"),
    ("single_from_import", "from os import path\n"),
    (
        "multiple_imports_then_code",
        "import os\nimport sys\nfrom typing import Any\nx = 1\n",
    ),
    (
        "docstring_then_imports",
        '"""Module docstring."""\nimport os\nfrom sys import argv\n',
    ),
    (
        "future_then_imports",
        "from __future__ import annotations\nimport os\n",
    ),
    ("imports_then_code", "import os\nx = os.getcwd()\n"),
    ("empty_module", ""),
    ("only_docstring", '"""Module docstring."""\n'),
    (
        "string_expression_after_imports",
        'import os\n"not a docstring"\n',
    ),
    (
        "passthrough_block_imports",
        "from temporalio import workflow\n\n"
        "with workflow.unsafe.imports_passed_through():\n"
        "    import pandas\n    from requests import Session\n",
    ),
    (
        "passthrough_block_then_code",
        "from temporalio import workflow\n\n"
        "with workflow.unsafe.imports_passed_through():\n"
        "    import pandas\n\nx = pandas\n",
    ),
    (
        "imports_after_passthrough_block",
        "from temporalio import workflow\n\n"
        "with workflow.unsafe.imports_passed_through():\n"
        "    import pandas\n\nimport os\n",
    ),
    (
        "passthrough_block_fully_qualified",
        "import temporalio\n\n"
        "with temporalio.workflow.unsafe.imports_passed_through():\n"
        "    import pandas\n",
    ),
    (
        "passthrough_block_among_several_managers",
        "from temporalio import workflow\n\n"
        "with trace(), workflow.unsafe.imports_passed_through():\n"
        "    import pandas\n",
    ),
]


_LATE_IMPORT_COUNT: list[tuple[str, str, int]] = [
    (
        "multiple_imports_after_code",
        "x = 1\nimport os\nimport sys\n",
        2,
    ),
    (
        "import_in_function_and_after_code",
        "x = 1\ndef f():\n    import os\nimport sys\n",
        2,
    ),
    (
        "nested_import_in_method_in_class",
        "class C:\n    def m(self):\n        from os import path\n",
        1,
    ),
    (
        "late_passthrough_block_reported_once",
        "from temporalio import workflow\n\nx = 1\n"
        "with workflow.unsafe.imports_passed_through():\n"
        "    import pandas\n    import numpy\n",
        1,
    ),
    (
        "nested_imports_inside_passthrough_block",
        "from temporalio import workflow\n\n"
        "with workflow.unsafe.imports_passed_through():\n"
        "    def f():\n        import os\n        import sys\n",
        2,
    ),
]


class TestSLD204ImportPlacement(unittest.TestCase):
    """Tests for SLD204: imports must be at the top of the module."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _LATE_IMPORT_PRESENT, "SLD204")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _LATE_IMPORT_ABSENT, "SLD204")

    def test_count(self) -> None:
        """Verify count."""
        assert_count(self, _LATE_IMPORT_COUNT, "SLD204")

    def test_no_errors_on_well_formed_module(self) -> None:
        """Verify no errors on well formed module."""
        source = (
            '"""Module docstring."""\n'
            "from __future__ import annotations\n"
            "import os\n"
            "import sys\n"
            "from typing import Any\n"
            "\n"
            "x: Any = os.getcwd()\n"
            "y = sys.path\n"
        )
        codes = [c for c in get_error_codes(source) if c == "SLD204"]
        assert_that(codes, empty())
