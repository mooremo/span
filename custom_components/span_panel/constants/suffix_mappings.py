"""Suffix mappings for consistent entity naming across the integration.

This module contains global suffix mappings for API description keys to user-friendly
and entity suffixes. These mappings drive consistent unique_id/entity_id suffixes
across all sensors, including Net Energy and import/export flows.

Extracted from helpers.py as part of Sub-Phase 4.4.2: Extract Suffix Mapping Constants
"""

from __future__ import annotations

# Circuit sensor API field mappings (used by get_user_friendly_suffix)
# Includes power, produced/consumed, net energy, and import/export energy
CIRCUIT_SUFFIX_MAPPING = {
    "instantPowerW": "power",
    "producedEnergyWh": "energy_produced",
    "consumedEnergyWh": "energy_consumed",
    "netEnergyWh": "energy_net",
    "importedEnergyWh": "energy_imported",
    "exportedEnergyWh": "energy_exported",
    "circuit_priority": "priority",
}

# Panel sensor API field mappings (used by get_user_friendly_suffix)
# Includes main meter/feedthrough produced, consumed, and net energy
PANEL_SUFFIX_MAPPING = {
    "instantGridPowerW": "grid_power",  # Descriptive to differentiate from other power types
    "feedthroughPowerW": "feed_through_power",
    "mainMeterEnergyProducedWh": "main_meter_energy_produced",  # Consistent naming
    "mainMeterEnergyConsumedWh": "main_meter_energy_consumed",  # Consistent naming
    "mainMeterNetEnergyWh": "main_meter_energy_net",  # Consistent naming
    "feedthroughEnergyProducedWh": "feed_through_energy_produced",  # Consistent naming
    "feedthroughEnergyConsumedWh": "feed_through_energy_consumed",  # Consistent naming
    "feedthroughNetEnergyWh": "feed_through_energy_net",  # Consistent naming
    "batteryPercentage": "battery_percentage",
    "dsmState": "dsm_state",
}

# Panel entity suffix mappings (used by get_panel_entity_suffix)
# These are the actual entity_id/unique_id suffixes used for panel sensors
# (e.g., "main_meter_net_energy" / "feed_through_net_energy").
PANEL_ENTITY_SUFFIX_MAPPING = {
    "instantGridPowerW": "current_power",
    "feedthroughPowerW": "feed_through_power",
    "mainMeterEnergyProducedWh": "main_meter_produced_energy",
    "mainMeterEnergyConsumedWh": "main_meter_consumed_energy",
    "mainMeterNetEnergyWh": "main_meter_net_energy",
    "feedthroughEnergyProducedWh": "feed_through_produced_energy",
    "feedthroughEnergyConsumedWh": "feed_through_consumed_energy",
    "feedthroughNetEnergyWh": "feed_through_net_energy",
    "batteryPercentage": "battery_level",
    "dsmState": "dsm_state",
}

# Combined mapping for general suffix lookup
ALL_SUFFIX_MAPPINGS = {**CIRCUIT_SUFFIX_MAPPING, **PANEL_SUFFIX_MAPPING}


# Pre-computed reverse mapping for O(1) lookup performance
# Built once at module load time instead of rebuilding on every function call
# This optimization was implemented in Phase 2.3
_REVERSE_SUFFIX_MAPPING: dict[str, str] = {}

# Add circuit suffix mappings
for _api_key, _user_suffix in CIRCUIT_SUFFIX_MAPPING.items():
    _REVERSE_SUFFIX_MAPPING[_user_suffix] = _api_key

# Add panel suffix mappings
for _api_key, _user_suffix in PANEL_SUFFIX_MAPPING.items():
    _REVERSE_SUFFIX_MAPPING[_user_suffix] = _api_key

# Add panel entity suffix mappings (these take precedence for panel sensors)
for _api_key, _entity_suffix in PANEL_ENTITY_SUFFIX_MAPPING.items():
    _REVERSE_SUFFIX_MAPPING[_entity_suffix] = _api_key
