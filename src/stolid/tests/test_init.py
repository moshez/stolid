"""Smoke tests that import the top-level ``stolid`` package."""

import unittest
from hamcrest import assert_that, contains_string

from .. import __version__


class TestInit(unittest.TestCase):
    """Tests that the package metadata is loadable."""

    def test_version(self):
        """Verify ``__version__`` exposes a dotted version string."""
        assert_that(__version__, contains_string("."))
