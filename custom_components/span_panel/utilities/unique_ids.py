"""Unique ID construction utilities for Span Panel integration.

Provides functions for building unique IDs for various entity types.
All functions are pure and take explicit parameters.

Extracted from helpers.py as part of Sub-Phase 5.3.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from ..const import DOMAIN
from ..constants.suffix_mappings import (
    ALL_SUFFIX_MAPPINGS,
    PANEL_ENTITY_SUFFIX_MAPPING,
)

if TYPE_CHECKING:
    from ..coordinator import SpanPanelCoordinator
    from ..span_panel import SpanPanel


def get_user_friendly_suffix(description_key: str) -> str:
    """Convert API description keys to user-friendly suffixes for consistent naming.

    Args:
        description_key: API description key (e.g., "instantPowerW")

    Returns:
        User-friendly suffix (e.g., "power")

    """
    # If we have a direct mapping, use it
    if description_key in ALL_SUFFIX_MAPPINGS:
        return ALL_SUFFIX_MAPPINGS[description_key]

    # Otherwise, sanitize by converting dots to underscores and making lowercase
    return description_key.replace(".", "_").lower()


def get_panel_entity_suffix(description_key: str) -> str:
    """Convert panel API description keys to entity ID suffixes for unique ID consistency.

    This ensures panel unique IDs use the same suffix as entity IDs for consistency.

    Args:
        description_key: API description key (e.g., "instantGridPowerW")

    Returns:
        Entity-specific suffix (e.g., "current_power")

    """
    # If we have a direct mapping, use it
    if description_key in PANEL_ENTITY_SUFFIX_MAPPING:
        return PANEL_ENTITY_SUFFIX_MAPPING[description_key]

    # Otherwise, fall back to the general suffix mapping
    return get_user_friendly_suffix(description_key)


def build_circuit_unique_id(serial: str, circuit_id: str, description_key: str) -> str:
    """Build unique ID for circuit sensors using consistent pattern (pure function).

    Args:
        serial: Panel serial number
        circuit_id: Circuit ID from panel API (UUID or tab number)
        description_key: Sensor description key (e.g., "instantPowerW")

    Returns:
        Unique ID like "span_{serial}_{circuit_id}_{consistent_suffix}"

    """
    consistent_suffix = get_user_friendly_suffix(description_key)
    return f"span_{serial.lower()}_{circuit_id}_{consistent_suffix}"


def build_panel_unique_id(serial: str, description_key: str) -> str:
    """Build unique ID for panel-level sensors using entity ID suffix pattern (pure function).

    Args:
        serial: Panel serial number
        description_key: Sensor description key (e.g., "instantGridPowerW")

    Returns:
        Unique ID like "span_{serial}_{entity_suffix}" (matches entity ID suffix)

    """
    entity_suffix = get_panel_entity_suffix(description_key)
    return f"span_{serial.lower()}_{entity_suffix}"


def build_switch_unique_id(serial: str, circuit_id: str) -> str:
    """Build unique ID for switch entities using consistent pattern (pure function).

    Args:
        serial: Panel serial number
        circuit_id: Circuit ID from panel API

    Returns:
        Unique ID like "span_{serial}_relay_{circuit_id}"

    """
    return f"span_{serial}_relay_{circuit_id}"


def build_binary_sensor_unique_id(serial: str, description_key: str) -> str:
    """Build unique ID for binary sensor entities using consistent pattern (pure function).

    Args:
        serial: Panel serial number
        description_key: Sensor description key (e.g., "doorState")

    Returns:
        Unique ID like "span_{serial}_{description_key}"

    """
    return f"span_{serial}_{description_key}"


def build_select_unique_id(serial: str, select_id: str) -> str:
    """Build unique ID for select entities using consistent pattern (pure function).

    Args:
        serial: Panel serial number
        select_id: Select entity identifier

    Returns:
        Unique ID like "span_{serial}_select_{select_id}"

    """
    return f"span_{serial}_select_{select_id}"


def construct_synthetic_unique_id(serial: str, sensor_name: str) -> str:
    """Build unique ID for synthetic sensors using consistent pattern (pure function).

    Args:
        serial: Panel serial number
        sensor_name: Complete sensor name with suffix (e.g., "solar_inverter_power")

    Returns:
        Unique ID like "span_{serial}_{sensor_name}"

    """
    return f"span_{serial.lower()}_{sensor_name}"


def construct_sensor_set_id(device_identifier: str) -> str:
    """Build sensor set ID for synthetic sensors using consistent pattern (pure function).

    Args:
        device_identifier: Device identifier (serial number for real panels, slugified name for simulators)

    Returns:
        Sensor set ID like "{device_identifier}_sensors"

    """
    return f"{device_identifier}_sensors"


def construct_unmapped_unique_id(serial: str, circuit_number: int | str, suffix: str) -> str:
    """Construct unique ID for unmapped circuit sensors.

    Args:
        serial: Panel serial number
        circuit_number: The tab number (e.g., 30, 32)
        suffix: Sensor suffix (e.g., "power", "energy_produced")

    Returns:
        Unique ID like "span_{serial}_unmapped_tab_{circuit_number}_{suffix}"

    """
    return f"span_{serial}_unmapped_tab_{circuit_number}_{suffix}"


def generate_unique_simulator_serial_number(hass: HomeAssistant) -> str:
    """Generate a unique simulator serial number in the format sim-nnn.

    Args:
        hass: Home Assistant instance

    Returns:
        Unique serial number in format sim-nnn (e.g., sim-001, sim-002, etc.)

    """
    # Get all existing span panel config entries
    existing_entries = hass.config_entries.async_entries(DOMAIN)

    # Find existing simulator serial numbers
    existing_serials: set[str] = set()
    for entry in existing_entries:
        if entry.data.get("simulation_mode", False):
            # Check both simulator_serial_number and CONF_HOST fields
            serial = entry.data.get("simulator_serial_number")
            if serial and serial.startswith("sim-"):
                existing_serials.add(serial)

            # CONF_HOST may contain the serial for existing simulator configurations
            host_serial = entry.data.get(CONF_HOST)
            if host_serial and host_serial.startswith("sim-"):
                existing_serials.add(host_serial)

    # Find the next available number
    counter = 1
    while f"sim-{counter:03d}" in existing_serials:
        counter += 1

    return f"sim-{counter:03d}"


def _get_device_identifier_for_unique_ids(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    device_name: str | None = None,
) -> str:
    """Compute per-entry device identifier for unique_ids.

    - Live panels: use true serial number
    - Simulator entries: use serial number from span panel status (which should be sim-nnn format)

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        device_name: Optional device name (unused, kept for API compatibility)

    Returns:
        Device identifier string (serial number)

    """
    # Note: is_simulator check is kept for documentation purposes but both paths return same value
    is_simulator = bool(coordinator.config_entry.data.get("simulation_mode", False))
    if is_simulator:
        # For simulators, use the serial number from the span panel status
        # This should be in the format sim-nnn (e.g., sim-001, sim-002, etc.)
        return span_panel.status.serial_number
    return span_panel.status.serial_number


def get_device_identifier_for_entry(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    device_name: str | None = None,
) -> str:
    """Public helper to get the per-entry device identifier used in unique_ids and storage.

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        device_name: Optional device name (unused, kept for API compatibility)

    Returns:
        Device identifier string (serial number)

    """
    return _get_device_identifier_for_unique_ids(coordinator, span_panel, device_name)


# Entry-based unique ID constructors (handle simulators)


def construct_panel_unique_id_for_entry(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    description_key: str,
    device_name: str | None = None,
) -> str:
    """Build panel unique_id using per-entry identifier (handles simulators).

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        description_key: Sensor description key (e.g., "instantGridPowerW")
        device_name: Optional device name (unused)

    Returns:
        Unique ID for panel sensor

    """
    identifier = _get_device_identifier_for_unique_ids(coordinator, span_panel, device_name)
    return build_panel_unique_id(identifier, description_key)


def construct_circuit_unique_id_for_entry(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    circuit_id: str,
    description_key: str,
    device_name: str | None = None,
) -> str:
    """Build circuit unique_id using per-entry identifier (handles simulators).

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        circuit_id: Circuit ID from panel API
        description_key: Sensor description key (e.g., "instantPowerW")
        device_name: Optional device name (unused)

    Returns:
        Unique ID for circuit sensor

    """
    identifier = _get_device_identifier_for_unique_ids(coordinator, span_panel, device_name)
    return build_circuit_unique_id(identifier, circuit_id, description_key)


def build_switch_unique_id_for_entry(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    circuit_id: str,
    device_name: str | None = None,
) -> str:
    """Build switch unique_id using per-entry identifier (handles simulators).

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        circuit_id: Circuit ID from panel API
        device_name: Optional device name (unused)

    Returns:
        Unique ID for switch entity

    """
    identifier = _get_device_identifier_for_unique_ids(coordinator, span_panel, device_name)
    return build_switch_unique_id(identifier, circuit_id)


def build_select_unique_id_for_entry(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    select_id: str,
    device_name: str | None = None,
) -> str:
    """Build select unique_id using per-entry identifier (handles simulators).

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        select_id: Select entity identifier
        device_name: Optional device name (unused)

    Returns:
        Unique ID for select entity

    """
    identifier = _get_device_identifier_for_unique_ids(coordinator, span_panel, device_name)
    return build_select_unique_id(identifier, select_id)


def build_binary_sensor_unique_id_for_entry(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    description_key: str,
    device_name: str | None = None,
) -> str:
    """Build binary_sensor unique_id using per-entry identifier (handles simulators).

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        description_key: Sensor description key (e.g., "doorState")
        device_name: Optional device name (unused)

    Returns:
        Unique ID for binary sensor entity

    """
    identifier = _get_device_identifier_for_unique_ids(coordinator, span_panel, device_name)
    return build_binary_sensor_unique_id(identifier, description_key)


def construct_synthetic_unique_id_for_entry(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    sensor_name: str,
    device_name: str | None = None,
) -> str:
    """Build synthetic sensor unique_id using per-entry identifier (handles simulators).

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        sensor_name: Complete sensor name with suffix
        device_name: Optional device name (unused)

    Returns:
        Unique ID for synthetic sensor

    """
    identifier = _get_device_identifier_for_unique_ids(coordinator, span_panel, device_name)
    return construct_synthetic_unique_id(identifier, sensor_name)


# SpanPanel-based unique ID constructors (for non-coordinator contexts)


def construct_circuit_unique_id(
    span_panel: SpanPanel, circuit_id: str, description_key: str
) -> str:
    """Construct unique ID for circuit sensors using consistent pattern.

    Args:
        span_panel: The span panel data
        circuit_id: Circuit ID from panel API (UUID or tab number)
        description_key: Sensor description key (e.g., "instantPowerW")

    Returns:
        Unique ID like "span_{serial}_{circuit_id}_{consistent_suffix}"

    Examples:
        span_abc123_0dad2f16cd514812ae1807b0457d473e_power
        span_abc123_circuit_15_energy_produced

    """
    return build_circuit_unique_id(span_panel.status.serial_number, circuit_id, description_key)


def construct_panel_unique_id(span_panel: SpanPanel, description_key: str) -> str:
    """Construct unique ID for panel-level sensors using consistent pattern.

    Args:
        span_panel: The span panel data
        description_key: Sensor description key (e.g., "instantGridPowerW")

    Returns:
        Unique ID like "span_{serial}_{consistent_suffix}" (uses descriptive consistent names)

    Examples:
        span_abc123_grid_power
        span_abc123_feed_through_power
        span_abc123_dsm_state

    """
    return build_panel_unique_id(span_panel.status.serial_number, description_key)


def construct_switch_unique_id(span_panel: SpanPanel, circuit_id: str) -> str:
    """Construct unique ID for switch entities using consistent pattern.

    Args:
        span_panel: The span panel data
        circuit_id: Circuit ID from panel API

    Returns:
        Unique ID like "span_{serial}_relay_{circuit_id}"

    Examples:
        span_abc123_relay_0dad2f16cd514812ae1807b0457d473e

    """
    return build_switch_unique_id(span_panel.status.serial_number, circuit_id)


def construct_binary_sensor_unique_id(span_panel: SpanPanel, description_key: str) -> str:
    """Construct unique ID for binary sensor entities using consistent pattern.

    Args:
        span_panel: The span panel data
        description_key: Sensor description key (e.g., "doorState")

    Returns:
        Unique ID like "span_{serial}_{description_key}"

    Examples:
        span_abc123_doorState
        span_abc123_eth0Link

    """
    return build_binary_sensor_unique_id(span_panel.status.serial_number, description_key)


def construct_select_unique_id(span_panel: SpanPanel, select_id: str) -> str:
    """Construct unique ID for select entities using consistent pattern.

    Args:
        span_panel: The span panel data
        select_id: Select entity identifier

    Returns:
        Unique ID like "span_{serial}_select_{select_id}"

    Examples:
        span_abc123_select_priority_mode

    """
    return build_select_unique_id(span_panel.status.serial_number, select_id)


__all__ = [
    # Pure build functions
    "build_circuit_unique_id",
    "build_panel_unique_id",
    "build_switch_unique_id",
    "build_binary_sensor_unique_id",
    "build_select_unique_id",
    "construct_synthetic_unique_id",
    "construct_sensor_set_id",
    "construct_unmapped_unique_id",
    # Suffix helpers
    "get_user_friendly_suffix",
    "get_panel_entity_suffix",
    # Simulator helpers
    "generate_unique_simulator_serial_number",
    "get_device_identifier_for_entry",
    # Entry-based constructors
    "construct_panel_unique_id_for_entry",
    "construct_circuit_unique_id_for_entry",
    "build_switch_unique_id_for_entry",
    "build_select_unique_id_for_entry",
    "build_binary_sensor_unique_id_for_entry",
    "construct_synthetic_unique_id_for_entry",
    # SpanPanel-based constructors
    "construct_circuit_unique_id",
    "construct_panel_unique_id",
    "construct_switch_unique_id",
    "construct_binary_sensor_unique_id",
    "construct_select_unique_id",
]
