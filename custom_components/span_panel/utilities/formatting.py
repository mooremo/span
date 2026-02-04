"""Formatting utilities for Span Panel integration.

Provides functions for constructing user-friendly names and formatting
display values.

Extracted from helpers.py as part of Sub-Phase 5.3.
"""

from __future__ import annotations

from typing import Any
import warnings


def construct_friendly_name(description_name: Any) -> str:
    """Construct friendly name for sensors (consolidated function).

    Works for panel-level, status, and other sensors.
    Converts description to string, returns empty string for None/empty values.

    Args:
        description_name: The sensor description name (can be str, int, None, or UndefinedType)

    Returns:
        String representation or empty string

    Examples:
        >>> construct_friendly_name("Main Panel")
        'Main Panel'
        >>> construct_friendly_name(None)
        ''
        >>> construct_friendly_name(42)
        '42'

    """
    return str(description_name) if description_name else ""


def construct_panel_friendly_name(description_name: Any) -> str:
    """Construct friendly name for panel-level sensors.

    .. deprecated::
        Use :func:`construct_friendly_name` instead.
        This function will be removed in version 2.0.

    Args:
        description_name: The sensor description name (can be str, None, or UndefinedType)

    Returns:
        Friendly name string

    """
    warnings.warn(
        "construct_panel_friendly_name is deprecated, use construct_friendly_name instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return construct_friendly_name(description_name)


def construct_status_friendly_name(description_name: Any) -> str:
    """Construct friendly name for status sensors.

    .. deprecated::
        Use :func:`construct_friendly_name` instead.
        This function will be removed in version 2.0.

    Args:
        description_name: The sensor description name (can be str, None, or UndefinedType)

    Returns:
        Friendly name string

    """
    warnings.warn(
        "construct_status_friendly_name is deprecated, use construct_friendly_name instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return construct_friendly_name(description_name)


def construct_unmapped_friendly_name(
    circuit_number: int | str, sensor_description_name: str
) -> str:
    """Construct friendly name for unmapped circuit sensors.

    Args:
        circuit_number: The tab number (e.g., 30, 32)
        sensor_description_name: The sensor description (e.g., "Consumed Energy")

    Returns:
        Friendly name like "Unmapped Tab 32 Consumed Energy"

    """
    return f"Unmapped Tab {circuit_number} {sensor_description_name}"


__all__ = [
    "construct_friendly_name",
    "construct_panel_friendly_name",
    "construct_status_friendly_name",
    "construct_unmapped_friendly_name",
]
