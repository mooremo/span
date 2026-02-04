"""Sensor-related utilities for Span Panel integration.

Provides functions for sensor classification, solar sensor handling,
and suffix mapping utilities.

Extracted from helpers.py as part of Sub-Phase 5.3.
"""

from __future__ import annotations

import re
from typing import Any

from ..constants.suffix_mappings import _REVERSE_SUFFIX_MAPPING


def get_api_description_key_from_suffix(suffix: str) -> str | None:
    """Reverse map from user-friendly suffix back to API description key.

    This is used for migration when we need to extract the original API description key
    from an entity_id suffix to call the helper functions correctly.

    Uses pre-computed reverse mapping for O(1) lookup performance.

    Args:
        suffix: User-friendly suffix extracted from entity_id (e.g., "power", "energy_produced")

    Returns:
        API description key (e.g., "instantPowerW", "producedEnergyWh") or None if not found

    Examples:
        get_api_description_key_from_suffix("power") -> "instantPowerW"
        get_api_description_key_from_suffix("energy_produced") -> "producedEnergyWh"
        get_api_description_key_from_suffix("current_power") -> "instantGridPowerW"

    """
    # Use pre-computed reverse mapping (built at module load time)
    return _REVERSE_SUFFIX_MAPPING.get(suffix)


def get_suffix_from_sensor_key(sensor_key: str) -> str:
    """Extract the suffix from a sensor key for use with entity ID helpers.

    Args:
        sensor_key: Sensor key like "span_abc123_solar_inverter_power" or "span_abc123_house_total_consumption"

    Returns:
        User-friendly suffix like "power" or "consumption"

    Examples:
        get_suffix_from_sensor_key("span_abc123_solar_inverter_power") -> "power"
        get_suffix_from_sensor_key("span_abc123_solar_inverter_energy_produced") -> "energy_produced"
        get_suffix_from_sensor_key("span_abc123_house_total_consumption") -> "consumption"

    """
    # Remove device prefix (span_{serial}_) from sensor key
    # Sensor keys follow pattern: span_{serial}_{actual_sensor_name}
    parts = sensor_key.split("_")
    if len(parts) >= 3 and parts[0] == "span":
        # Reconstruct the sensor name without the device prefix
        sensor_name = "_".join(parts[2:])
    else:
        # Fallback if pattern doesn't match expected format
        sensor_name = sensor_key

    # For solar sensors, the suffix is the last part after "solar_inverter_"
    if sensor_name.startswith("solar_inverter_"):
        return sensor_name.replace("solar_inverter_", "")

    # For other sensors, the suffix is typically the last part or last few parts
    # Look for well-established suffix patterns
    established_suffixes = [
        "energy_produced",
        "energy_consumed",
        "energy_net",
        "current_power",
        "grid_power",
        "total_power",
        "instant_power",
        "consumption",
        "production",
        "power",
        "energy",
    ]

    # Check if the sensor name ends with any established suffix
    for suffix in established_suffixes:
        if sensor_name.endswith(suffix):
            return suffix

    # If no established pattern matches, return the last part after the last underscore
    name_parts = sensor_name.split("_")
    return name_parts[-1] if name_parts else sensor_name


def is_solar_sensor_key(sensor_key: str) -> bool:
    """Check if a sensor key represents a solar sensor.

    Args:
        sensor_key: Sensor key to check (e.g., "span_abc123_solar_inverter_power")

    Returns:
        True if this is a solar sensor key

    Examples:
        is_solar_sensor_key("span_abc123_solar_inverter_power") -> True
        is_solar_sensor_key("span_abc123_house_total_consumption") -> False

    """
    # Remove device prefix to get the actual sensor name
    parts = sensor_key.split("_")
    if len(parts) >= 3 and parts[0] == "span":
        sensor_name = "_".join(parts[2:])
    else:
        sensor_name = sensor_key

    return sensor_name.startswith("solar_inverter_") or "solar" in sensor_name.lower()


def is_panel_level_sensor_key(sensor_key: str) -> bool:
    """Check if a sensor key represents a panel-level sensor.

    Panel-level sensors have the form: span_{device_identifier}_{sensor_type}
    Circuit sensors have the form: span_{device_identifier}_{circuit_id}_{sensor_type}

    Args:
        sensor_key: Sensor key to check (e.g., "span_sp3-simulation-001_current_power" or
                   "span_sp3-simulation-001_12ce227695cd44338864b0ef2ec4168b_power")

    Returns:
        True if this is a panel-level sensor (no circuit ID)

    Examples:
        is_panel_level_sensor_key("span_sp3-simulation-001_current_power") -> True
        is_panel_level_sensor_key("span_sp3-simulation-001_12ce227695cd44338864b0ef2ec4168b_power") -> False

    """
    # Must start with "span_"
    if not sensor_key.startswith("span_"):
        return False

    # Look for UUID pattern (32 hex characters) anywhere in the string after "span_"
    # Circuit IDs in SPAN are typically formatted as 32 lowercase hex characters without dashes
    uuid_pattern = re.compile(r"_[a-f0-9]{32}_")

    # If we find a UUID pattern, this is a circuit sensor
    if uuid_pattern.search(sensor_key):
        return False
    else:
        # No UUID pattern found, this is a panel-level sensor
        return True


def extract_solar_info_from_sensor_key(
    sensor_key: str, sensor_config: dict[str, Any]
) -> dict[str, Any] | None:
    """Extract solar sensor information from sensor key and config.

    Args:
        sensor_key: Solar sensor key like "span_abc123_solar_inverter_instant_power"
        sensor_config: Sensor configuration dictionary

    Returns:
        Dictionary with solar info: {"friendly_name": str, "leg1": int, "leg2": int}

    Examples:
        extract_solar_info_from_sensor_key("span_abc123_solar_inverter_instant_power", config)
        -> {"friendly_name": "Solar Inverter", "leg1": 30, "leg2": 32}

    """
    if not is_solar_sensor_key(sensor_key):
        return None

    # Extract friendly name from sensor name, removing the suffix
    name = sensor_config.get("name", "")
    if name:
        # Remove common suffixes from the name to get the base friendly name
        for suffix in [" Instant Power", " Energy Produced", " Energy Consumed", " Power"]:
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        friendly_name = name
    else:
        friendly_name = "Solar Inverter"

    # Extract circuit numbers from variables that reference backing entities
    leg1 = 0
    leg2 = 0
    variables = sensor_config.get("variables", {})

    # Look for patterns like "sensor.span_panel_solar_east_power" or "sensor.span_panel_circuit_30_power"
    for _var_name, entity_id in variables.items():
        if isinstance(entity_id, str) and "circuit_" in entity_id:
            # Extract circuit number from entity_id like "sensor.span_panel_circuit_30_power"
            parts = entity_id.split("_")
            for i, part in enumerate(parts):
                if part == "circuit" and i + 1 < len(parts):
                    try:
                        circuit_num = int(parts[i + 1])
                        if leg1 == 0:
                            leg1 = circuit_num
                        elif leg2 == 0:
                            leg2 = circuit_num
                        break
                    except ValueError:
                        continue

    return {
        "friendly_name": friendly_name,
        "leg1": leg1,
        "leg2": leg2,
    }


__all__ = [
    "get_api_description_key_from_suffix",
    "get_suffix_from_sensor_key",
    "is_solar_sensor_key",
    "is_panel_level_sensor_key",
    "extract_solar_info_from_sensor_key",
]
