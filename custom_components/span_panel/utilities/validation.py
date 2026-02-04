"""Input validation utilities for Span Panel integration.

Provides validation functions for user inputs, ensuring data integrity
and applying business rules.

Extracted from helpers.py as part of Sub-Phase 5.3.
"""

from __future__ import annotations

from typing import Any

from ..const import DEFAULT_SCAN_INTERVAL, MINIMUM_SCAN_INTERVAL


def validate_scan_interval(raw_value: Any) -> int:
    """Validate and normalize scan interval value.

    Consolidates scan interval validation logic used across multiple entry points.
    Accepts strings, floats, and ints, converts to int, and clamps to minimum value.

    Args:
        raw_value: Raw scan interval value (int, float, str, or None)

    Returns:
        Validated scan interval in seconds (int), clamped to MINIMUM_SCAN_INTERVAL

    Examples:
        >>> validate_scan_interval(15)
        15
        >>> validate_scan_interval("20")
        20
        >>> validate_scan_interval(3)  # Below minimum
        5
        >>> validate_scan_interval(None)  # Invalid, returns default
        15

    """
    try:
        # Accept strings, floats, and ints; e.g., "15", 15.0, 15
        scan_interval_seconds = int(float(raw_value))
    except (TypeError, ValueError):
        # Invalid input - return default
        return int(DEFAULT_SCAN_INTERVAL.total_seconds())

    # Clamp to minimum value
    if scan_interval_seconds < MINIMUM_SCAN_INTERVAL:
        return MINIMUM_SCAN_INTERVAL

    return scan_interval_seconds


__all__ = ["validate_scan_interval"]
