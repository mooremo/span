"""Utility functions package for Span Panel integration.

This package organizes helper functions by domain:
- validation: Input validation functions
- formatting: Friendly name formatting
- unique_ids: Unique ID construction
- entity_naming: Entity ID construction
- sensor_utils: Sensor-related helpers
- circuit_utils: Circuit-related helpers
- registry: Entity registry utilities

Extracted from helpers.py as part of Sub-Phase 5.3.
"""

from __future__ import annotations

# Circuit utilities
from .circuit_utils import (
    construct_tabs_attribute,
    construct_voltage_attribute,
    get_circuit_voltage_type,
    get_panel_voltage_attribute,
    parse_tabs_attribute,
)

# Entity naming utilities
from .entity_naming import (
    construct_120v_synthetic_entity_id,
    construct_240v_synthetic_entity_id,
    construct_entity_id,
    construct_multi_circuit_entity_id,
    construct_panel_entity_id,
    construct_panel_synthetic_entity_id,
    construct_single_circuit_entity_id,
    construct_unmapped_circuit_id,
    construct_unmapped_entity_id,
    get_circuit_number,
    get_unmapped_circuit_entity_id,
)

# Formatting utilities
from .formatting import (
    construct_friendly_name,
    construct_panel_friendly_name,
    construct_status_friendly_name,
    construct_unmapped_friendly_name,
)

# Registry utilities
from .registry import (
    async_create_span_notification,
    get_friendly_name_from_registry,
)

# Sensor utilities
from .sensor_utils import (
    extract_solar_info_from_sensor_key,
    get_api_description_key_from_suffix,
    get_suffix_from_sensor_key,
    is_panel_level_sensor_key,
    is_solar_sensor_key,
)

# Unique ID utilities
from .unique_ids import (
    build_binary_sensor_unique_id,
    build_binary_sensor_unique_id_for_entry,
    build_circuit_unique_id,
    build_panel_unique_id,
    build_select_unique_id,
    build_select_unique_id_for_entry,
    build_switch_unique_id,
    build_switch_unique_id_for_entry,
    construct_binary_sensor_unique_id,
    construct_circuit_unique_id,
    construct_circuit_unique_id_for_entry,
    construct_panel_unique_id,
    construct_panel_unique_id_for_entry,
    construct_select_unique_id,
    construct_sensor_set_id,
    construct_switch_unique_id,
    construct_synthetic_unique_id,
    construct_synthetic_unique_id_for_entry,
    construct_unmapped_unique_id,
    generate_unique_simulator_serial_number,
    get_device_identifier_for_entry,
    get_panel_entity_suffix,
    get_user_friendly_suffix,
)

# Validation utilities
from .validation import validate_scan_interval

__all__ = [
    # Validation
    "validate_scan_interval",
    # Formatting
    "construct_friendly_name",
    "construct_panel_friendly_name",
    "construct_status_friendly_name",
    "construct_unmapped_friendly_name",
    # Unique IDs - Pure build functions
    "build_circuit_unique_id",
    "build_panel_unique_id",
    "build_switch_unique_id",
    "build_binary_sensor_unique_id",
    "build_select_unique_id",
    "construct_synthetic_unique_id",
    "construct_sensor_set_id",
    "construct_unmapped_unique_id",
    # Unique IDs - Suffix helpers
    "get_user_friendly_suffix",
    "get_panel_entity_suffix",
    # Unique IDs - Simulator helpers
    "generate_unique_simulator_serial_number",
    "get_device_identifier_for_entry",
    # Unique IDs - Entry-based constructors
    "construct_panel_unique_id_for_entry",
    "construct_circuit_unique_id_for_entry",
    "build_switch_unique_id_for_entry",
    "build_select_unique_id_for_entry",
    "build_binary_sensor_unique_id_for_entry",
    "construct_synthetic_unique_id_for_entry",
    # Unique IDs - SpanPanel-based constructors
    "construct_circuit_unique_id",
    "construct_panel_unique_id",
    "construct_switch_unique_id",
    "construct_binary_sensor_unique_id",
    "construct_select_unique_id",
    # Entity naming
    "construct_entity_id",
    "construct_panel_entity_id",
    "construct_panel_synthetic_entity_id",
    "construct_single_circuit_entity_id",
    "construct_multi_circuit_entity_id",
    "construct_240v_synthetic_entity_id",
    "construct_120v_synthetic_entity_id",
    "construct_unmapped_entity_id",
    "get_unmapped_circuit_entity_id",
    "construct_unmapped_circuit_id",
    "get_circuit_number",
    # Sensor utilities
    "get_api_description_key_from_suffix",
    "get_suffix_from_sensor_key",
    "is_solar_sensor_key",
    "is_panel_level_sensor_key",
    "extract_solar_info_from_sensor_key",
    # Circuit utilities
    "construct_tabs_attribute",
    "parse_tabs_attribute",
    "get_circuit_voltage_type",
    "get_panel_voltage_attribute",
    "construct_voltage_attribute",
    # Registry utilities
    "get_friendly_name_from_registry",
    "async_create_span_notification",
]
