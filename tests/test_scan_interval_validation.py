"""Test scan interval validation consolidation.

Tests for Phase 2.2: Consolidate Scan Interval Validation
Verifies that scan interval validation is consistent across all entry points.
"""

import pytest
from typing import Any


@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


def test_validate_scan_interval_with_valid_int():
    """Test validation with valid integer input."""
    from custom_components.span_panel.const import validate_scan_interval

    result = validate_scan_interval(15)
    assert result == 15


def test_validate_scan_interval_with_valid_float():
    """Test validation with float input (should convert to int)."""
    from custom_components.span_panel.const import validate_scan_interval

    result = validate_scan_interval(15.7)
    assert result == 15  # Should truncate to int


def test_validate_scan_interval_with_string():
    """Test validation with string input."""
    from custom_components.span_panel.const import validate_scan_interval

    result = validate_scan_interval("20")
    assert result == 20


def test_validate_scan_interval_with_float_string():
    """Test validation with float string input."""
    from custom_components.span_panel.const import validate_scan_interval

    result = validate_scan_interval("15.5")
    assert result == 15  # Should convert via int(float())


def test_validate_scan_interval_clamps_to_minimum():
    """Test that values below 5 are clamped to 5."""
    from custom_components.span_panel.const import validate_scan_interval

    # Test various values below minimum
    assert validate_scan_interval(0) == 5
    assert validate_scan_interval(1) == 5
    assert validate_scan_interval(4) == 5
    assert validate_scan_interval(-10) == 5


def test_validate_scan_interval_accepts_minimum():
    """Test that exactly 5 is accepted."""
    from custom_components.span_panel.const import validate_scan_interval

    result = validate_scan_interval(5)
    assert result == 5


def test_validate_scan_interval_with_none():
    """Test validation with None (should return default)."""
    from custom_components.span_panel.const import (
        validate_scan_interval,
        DEFAULT_SCAN_INTERVAL,
    )

    result = validate_scan_interval(None)
    assert result == int(DEFAULT_SCAN_INTERVAL.total_seconds())


def test_validate_scan_interval_with_invalid_string():
    """Test validation with invalid string (should return default)."""
    from custom_components.span_panel.const import (
        validate_scan_interval,
        DEFAULT_SCAN_INTERVAL,
    )

    result = validate_scan_interval("invalid")
    assert result == int(DEFAULT_SCAN_INTERVAL.total_seconds())


def test_validate_scan_interval_with_very_large_value():
    """Test validation with very large value."""
    from custom_components.span_panel.const import validate_scan_interval

    result = validate_scan_interval(999999)
    assert result == 999999  # Should accept large values


def test_validate_scan_interval_with_empty_string():
    """Test validation with empty string (should return default)."""
    from custom_components.span_panel.const import (
        validate_scan_interval,
        DEFAULT_SCAN_INTERVAL,
    )

    result = validate_scan_interval("")
    assert result == int(DEFAULT_SCAN_INTERVAL.total_seconds())


def test_minimum_scan_interval_constant():
    """Test that MINIMUM_SCAN_INTERVAL constant exists and is correct."""
    from custom_components.span_panel.const import MINIMUM_SCAN_INTERVAL

    assert MINIMUM_SCAN_INTERVAL == 5


def test_validate_scan_interval_edge_case_negative_float():
    """Test validation with negative float."""
    from custom_components.span_panel.const import validate_scan_interval

    result = validate_scan_interval(-5.5)
    assert result == 5  # Should clamp to minimum


def test_validate_scan_interval_edge_case_zero_string():
    """Test validation with string "0"."""
    from custom_components.span_panel.const import validate_scan_interval

    result = validate_scan_interval("0")
    assert result == 5  # Should clamp to minimum
