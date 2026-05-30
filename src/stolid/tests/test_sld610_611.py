"""Tests for SLD610/SLD611: manual index-walking loops."""

from __future__ import annotations

import unittest

from .code_parser import (
    assert_absent,
    assert_count,
    assert_message_contains,
    assert_present,
)

_SLD610_PRESENT: list[tuple[str, str]] = [
    ("range_len_direct", "for i in range(len(seq)):\n    use(seq[i])\n"),
    ("range_len_with_start", "for i in range(0, len(seq)):\n    use(seq[i])\n"),
    ("range_len_minus_one", "for i in range(len(seq) - 1):\n    use(seq[i])\n"),
    (
        "range_len_attribute",
        "for i in range(len(self.items)):\n    use(self.items[i])\n",
    ),
    (
        "range_two_lens",
        "for i in range(len(a), len(b)):\n    use(i)\n",
    ),
]

_SLD610_ABSENT: list[tuple[str, str]] = [
    ("range_plain_count", "for i in range(10):\n    use(i)\n"),
    ("range_numeric_interval", "for i in range(start, stop):\n    use(i)\n"),
    ("direct_iteration", "for item in seq:\n    use(item)\n"),
    ("enumerate", "for i, item in enumerate(seq):\n    use(i, item)\n"),
    ("non_range_call_with_len", "for x in sorted(items, key=len):\n    use(x)\n"),
    ("len_call_not_in_range", "for x in chunked(items, len(items)):\n    use(x)\n"),
]

_SLD611_PRESENT: list[tuple[str, str]] = [
    ("less_than", "while i < len(seq):\n    use(seq[i])\n    i += 1\n"),
    ("less_equal", "while i <= len(seq):\n    use(seq[i])\n    i += 1\n"),
    ("reversed_greater", "while len(seq) > i:\n    use(seq[i])\n    i += 1\n"),
    (
        "reversed_greater_equal",
        "while len(seq) >= i:\n    use(seq[i])\n    i += 1\n",
    ),
    ("len_with_arithmetic", "while i < len(seq) - 1:\n    use(seq[i])\n    i += 1\n"),
]

_SLD611_ABSENT: list[tuple[str, str]] = [
    ("worklist_drained_to_empty", "while len(stack) > 0:\n    stack.pop()\n"),
    ("truthiness", "while running:\n    step()\n"),
    ("no_len_comparison", "while i < n:\n    i += 1\n"),
    ("equality_not_ordering", "while i == len(seq):\n    step()\n"),
    ("chained_comparison", "while 0 < i < len(seq):\n    i += 1\n"),
    (
        "both_sides_len",
        "while len(left) < len(right):\n    grow(left)\n",
    ),
]

_SLD610_COUNT: list[tuple[str, str, int]] = [
    (
        "two_independent_loops",
        "for i in range(len(a)):\n    use(a[i])\n"
        "for j in range(len(b)):\n    use(b[j])\n",
        2,
    ),
]


class TestSLD610RangeLen(unittest.TestCase):
    """Tests for SLD610: ``for`` over ``range(len(...))``."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD610_PRESENT, "SLD610")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD610_ABSENT, "SLD610")

    def test_count(self) -> None:
        """Verify count."""
        assert_count(self, _SLD610_COUNT, "SLD610")

    def test_message_mentions_enumerate(self) -> None:
        """Verify the SLD610 message points at enumerate."""
        assert_message_contains(
            "for i in range(len(seq)):\n    use(seq[i])\n", "SLD610", "enumerate"
        )


class TestSLD611WhileIndex(unittest.TestCase):
    """Tests for SLD611: ``while`` indexing against ``len(...)``."""

    def test_present(self) -> None:
        """Verify present."""
        assert_present(self, _SLD611_PRESENT, "SLD611")

    def test_absent(self) -> None:
        """Verify absent."""
        assert_absent(self, _SLD611_ABSENT, "SLD611")

    def test_message_mentions_enumerate(self) -> None:
        """Verify the SLD611 message points at enumerate."""
        assert_message_contains(
            "while i < len(seq):\n    use(seq[i])\n    i += 1\n",
            "SLD611",
            "enumerate",
        )
