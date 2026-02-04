"""Circuit-related utilities for Span Panel integration.

Provides functions for circuit voltage handling, tab parsing, and
circuit attribute construction.

Extracted from helpers.py as part of Sub-Phase 5.3.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..span_panel_circuit import SpanPanelCircuit

_LOGGER = logging.getLogger(__name__)


def construct_tabs_attribute(circuit: SpanPanelCircuit) -> str | None:
    """Construct tabs attribute string from circuit data.

    For US electrical systems, circuits can only have 1 tab (120V) or 2 tabs (240V).

    Args:
        circuit: SpanPanelCircuit object with tabs information

    Returns:
        Tabs attribute string like "tabs [30:32]" for 240V or "tabs [28]" for 120V,
        or None if no tabs information is available

    Examples:
        Single tab (120V): "tabs [28]"
        Two tabs (240V): "tabs [30:32]"
        No tabs: None

    """
    if not circuit.tabs:
        return None

    # Sort tabs for consistent ordering
    sorted_tabs = sorted(circuit.tabs)

    if len(sorted_tabs) == 1:
        # Single tab (120V)
        return f"tabs [{sorted_tabs[0]}]"
    elif len(sorted_tabs) == 2:
        # Two tabs (240V) - format as range
        return f"tabs [{sorted_tabs[0]}:{sorted_tabs[1]}]"
    else:
        # More than 2 tabs is not valid for US electrical system
        _LOGGER.warning(
            "Circuit %s has %d tabs, which is not valid for US electrical system (expected 1 or 2)",
            circuit.circuit_id,
            len(sorted_tabs),
        )
        return None


def parse_tabs_attribute(tabs_attr: str) -> list[int] | None:
    """Parse tabs attribute string back to list of tab numbers.

    For US electrical systems, only 1 tab (120V) or 2 tabs (240V) are valid.

    Args:
        tabs_attr: Tabs attribute string like "tabs [30:32]" or "tabs [28]"

    Returns:
        List of tab numbers, or None if parsing fails or invalid for US electrical system

    Examples:
        "tabs [28]" -> [28] (120V)
        "tabs [30:32]" -> [30, 32] (240V)

    """
    if not tabs_attr or not tabs_attr.startswith("tabs ["):
        return None

    try:
        # Extract content between brackets
        content = tabs_attr[6:-1]  # Remove "tabs [" and "]"

        if ":" in content:
            # Range format: "30:32" (240V)
            start, end = map(int, content.split(":"))
            return [start, end]
        else:
            # Single tab: "28" (120V)
            return [int(content)]

    except (ValueError, IndexError) as e:
        _LOGGER.warning("Failed to parse tabs attribute '%s': %s", tabs_attr, e)
        return None


def get_circuit_voltage_type(circuit: SpanPanelCircuit) -> str:
    """Determine the voltage type of a circuit based on its tabs.

    For US electrical systems, circuits can only be 120V (1 tab) or 240V (2 tabs).

    Args:
        circuit: SpanPanelCircuit object

    Returns:
        Voltage type: "120V" for single tab, "240V" for two tabs, "unknown" otherwise

    """
    if not circuit.tabs:
        return "unknown"

    if len(circuit.tabs) == 1:
        return "120V"
    elif len(circuit.tabs) == 2:
        return "240V"
    else:
        # More than 2 tabs is not valid for US electrical system
        _LOGGER.warning(
            "Circuit %s has %d tabs, which is not valid for US electrical system (expected 1 or 2)",
            circuit.circuit_id,
            len(circuit.tabs),
        )
        return "unknown"


def get_panel_voltage_attribute() -> int:
    """Get voltage attribute for panel-level sensors.

    US residential electrical panels are standardized as 240V split-phase systems.
    Panel-level sensors (like main meter energy) represent aggregate measurements
    at the full panel voltage.

    Returns:
        Panel voltage in volts (always 240 for US residential panels)

    """
    return 240


def construct_voltage_attribute(circuit: SpanPanelCircuit) -> int | None:
    """Construct voltage attribute for a circuit based on tab count.

    For US electrical systems, circuits can only have 1 tab (120V) or 2 tabs (240V).

    Args:
        circuit: SpanPanelCircuit object with tabs information

    Returns:
        Voltage in volts (120 for single tab, 240 for double tab), or None if no tabs information

    Examples:
        Single tab (120V): 120
        Two tabs (240V): 240
        No tabs: None

    """
    if not circuit.tabs:
        return None

    if len(circuit.tabs) == 1:
        return 120
    elif len(circuit.tabs) == 2:
        return 240
    else:
        # More than 2 tabs is not valid for US electrical system
        _LOGGER.warning(
            "Circuit %s has %d tabs, which is not valid for US electrical system (expected 1 or 2)",
            circuit.circuit_id,
            len(circuit.tabs),
        )
        return None


__all__ = [
    "construct_tabs_attribute",
    "parse_tabs_attribute",
    "get_circuit_voltage_type",
    "get_panel_voltage_attribute",
    "construct_voltage_attribute",
]
