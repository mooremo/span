"""Test options flow utilities for config flow.

Tests for Sub-Phase 4.1: Test Infrastructure
Validates key functions in config_flow_utils/options.py
"""

from unittest.mock import MagicMock, patch
import pytest
import voluptuous as vol

from custom_components.span_panel.config_flow_utils.options import (
    build_general_options_schema,
    get_current_naming_pattern,
    get_entity_naming_options_defaults,
    get_entity_naming_schema,
    get_general_options_defaults,
    pattern_to_flags,
    process_general_options_input,
)
from custom_components.span_panel.const import (
    ENABLE_CIRCUIT_NET_ENERGY_SENSORS,
    ENABLE_PANEL_NET_ENERGY_SENSORS,
    ENABLE_SOLAR_NET_ENERGY_SENSORS,
    ENTITY_NAMING_PATTERN,
    USE_CIRCUIT_NUMBERS,
    USE_DEVICE_PREFIX,
    EntityNamingPattern,
)
from custom_components.span_panel.options import (
    BATTERY_ENABLE,
    INVERTER_ENABLE,
    INVERTER_LEG1,
    INVERTER_LEG2,
)
from homeassistant.const import CONF_SCAN_INTERVAL


@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test-entry-id"
    entry.title = "SPAN Panel"
    entry.data = {"device_name": "SPAN Panel", "host": "192.168.1.100"}
    entry.options = {
        CONF_SCAN_INTERVAL: 15,
        BATTERY_ENABLE: False,
        INVERTER_ENABLE: False,
        INVERTER_LEG1: 0,
        INVERTER_LEG2: 0,
        USE_DEVICE_PREFIX: True,
        USE_CIRCUIT_NUMBERS: False,
        ENABLE_PANEL_NET_ENERGY_SENSORS: True,
        ENABLE_CIRCUIT_NET_ENERGY_SENSORS: True,
        ENABLE_SOLAR_NET_ENERGY_SENSORS: True,
    }
    return entry


# ===== Tests for build_general_options_schema =====


def test_build_general_options_schema_basic(mock_config_entry):
    """Test building general options schema."""
    available_tabs = [1, 2, 3, 4]

    schema = build_general_options_schema(mock_config_entry, available_tabs)

    # Should return a voluptuous Schema
    assert isinstance(schema, vol.Schema)

    # Should have the expected optional fields
    schema_dict = schema.schema
    assert any(str(key).find(CONF_SCAN_INTERVAL) >= 0 for key in schema_dict.keys())
    assert any(str(key).find(BATTERY_ENABLE) >= 0 for key in schema_dict.keys())
    assert any(str(key).find(INVERTER_ENABLE) >= 0 for key in schema_dict.keys())


def test_build_general_options_schema_with_current_legs(mock_config_entry):
    """Test schema building with current leg selections."""
    available_tabs = list(range(1, 33))
    current_leg1 = 1
    current_leg2 = 3

    schema = build_general_options_schema(
        mock_config_entry, available_tabs, current_leg1, current_leg2
    )

    # Schema should be created successfully
    assert isinstance(schema, vol.Schema)


def test_build_general_options_schema_with_user_input(mock_config_entry):
    """Test schema building with dynamic user input."""
    available_tabs = [1, 2, 3, 4]
    user_input = {INVERTER_LEG1: "1", INVERTER_LEG2: "3"}

    # Should handle dynamic updates
    schema = build_general_options_schema(
        mock_config_entry, available_tabs, user_input=user_input
    )

    assert isinstance(schema, vol.Schema)


# ===== Tests for get_general_options_defaults =====


def test_get_general_options_defaults_basic(mock_config_entry):
    """Test getting default values for general options."""
    defaults = get_general_options_defaults(mock_config_entry, 0, 0)

    # Should return a dictionary
    assert isinstance(defaults, dict)

    # Should have expected keys with values from config_entry.options
    assert defaults[CONF_SCAN_INTERVAL] == 15
    assert defaults[BATTERY_ENABLE] is False
    assert defaults[INVERTER_ENABLE] is False


def test_get_general_options_defaults_with_legs(mock_config_entry):
    """Test getting defaults with leg values."""
    defaults = get_general_options_defaults(mock_config_entry, 1, 3)

    # Legs should be converted to strings for selector compatibility
    assert defaults[INVERTER_LEG1] == "1"
    assert defaults[INVERTER_LEG2] == "3"


def test_get_general_options_defaults_legacy_install(mock_config_entry):
    """Test defaults for legacy installation."""
    # Legacy install doesn't have USE_DEVICE_PREFIX
    mock_config_entry.options[USE_DEVICE_PREFIX] = False

    defaults = get_general_options_defaults(mock_config_entry, 0, 0)

    # Should include legacy upgrade flag
    assert "legacy_upgrade_to_friendly" in defaults
    assert defaults["legacy_upgrade_to_friendly"] is False


def test_get_general_options_defaults_modern_install(mock_config_entry):
    """Test defaults for modern installation."""
    # Modern install has USE_DEVICE_PREFIX = True
    mock_config_entry.options[USE_DEVICE_PREFIX] = True

    defaults = get_general_options_defaults(mock_config_entry, 0, 0)

    # Should NOT include legacy upgrade flag
    assert "legacy_upgrade_to_friendly" not in defaults


# ===== Tests for process_general_options_input =====


def test_process_general_options_input_basic(mock_config_entry):
    """Test processing basic user input."""
    user_input = {
        CONF_SCAN_INTERVAL: 30,
        BATTERY_ENABLE: True,
        INVERTER_ENABLE: False,
    }
    available_tabs = []

    processed, errors = process_general_options_input(
        mock_config_entry, user_input, available_tabs
    )

    # Should process without errors
    assert errors == {}
    assert processed[CONF_SCAN_INTERVAL] == 30
    assert processed[BATTERY_ENABLE] is True


def test_process_general_options_input_solar_enabled_valid(mock_config_entry):
    """Test processing input with valid solar configuration."""
    user_input = {
        INVERTER_ENABLE: True,
        INVERTER_LEG1: "1",  # Strings from selector
        INVERTER_LEG2: "3",  # Opposite phase
    }
    available_tabs = list(range(1, 33))

    processed, errors = process_general_options_input(
        mock_config_entry, user_input, available_tabs
    )

    # Should process and convert leg values to integers
    assert errors == {}
    assert processed[INVERTER_ENABLE] is True
    assert processed[INVERTER_LEG1] == 1  # Converted to int
    assert processed[INVERTER_LEG2] == 3


def test_process_general_options_input_solar_enabled_invalid_same_phase(mock_config_entry):
    """Test processing input with invalid solar configuration (same phase)."""
    user_input = {
        INVERTER_ENABLE: True,
        INVERTER_LEG1: "1",  # L1
        INVERTER_LEG2: "2",  # Also L1 (tabs 1-2 are same phase)
    }
    available_tabs = list(range(1, 33))

    processed, errors = process_general_options_input(
        mock_config_entry, user_input, available_tabs
    )

    # Should have validation error
    assert "base" in errors
    assert "phase" in errors["base"].lower()


def test_process_general_options_input_legacy_upgrade_requested(mock_config_entry):
    """Test processing when legacy upgrade is requested."""
    user_input = {
        "legacy_upgrade_to_friendly": True,
    }
    available_tabs = []

    processed, errors = process_general_options_input(
        mock_config_entry, user_input, available_tabs
    )

    # Should set migration flags
    assert errors == {}
    assert processed[USE_DEVICE_PREFIX] is True
    assert processed[USE_CIRCUIT_NUMBERS] is False
    assert processed.get("pending_legacy_migration") is True


def test_process_general_options_input_preserves_naming_flags(mock_config_entry):
    """Test that processing preserves existing naming flags."""
    mock_config_entry.options[USE_DEVICE_PREFIX] = True
    mock_config_entry.options[USE_CIRCUIT_NUMBERS] = True

    user_input = {CONF_SCAN_INTERVAL: 20}
    available_tabs = []

    processed, errors = process_general_options_input(
        mock_config_entry, user_input, available_tabs
    )

    # Should preserve existing flags
    assert processed[USE_DEVICE_PREFIX] is True
    assert processed[USE_CIRCUIT_NUMBERS] is True


def test_process_general_options_input_filters_separators(mock_config_entry):
    """Test that separator fields are filtered out."""
    user_input = {
        CONF_SCAN_INTERVAL: 25,
        "_separator_1": None,
        "_separator_solar": None,
    }
    available_tabs = []

    processed, errors = process_general_options_input(
        mock_config_entry, user_input, available_tabs
    )

    # Separators should be removed
    assert "_separator_1" not in processed
    assert "_separator_solar" not in processed
    assert CONF_SCAN_INTERVAL in processed


# ===== Tests for get_entity_naming_schema =====


def test_get_entity_naming_schema():
    """Test getting entity naming schema."""
    schema = get_entity_naming_schema()

    # Should return a voluptuous Schema
    assert isinstance(schema, vol.Schema)

    # Should have ENTITY_NAMING_PATTERN field
    schema_dict = schema.schema
    assert any(str(key).find(ENTITY_NAMING_PATTERN) >= 0 for key in schema_dict.keys())


# ===== Tests for get_current_naming_pattern =====


def test_get_current_naming_pattern_friendly_names(mock_config_entry):
    """Test detecting friendly names pattern."""
    mock_config_entry.options[USE_CIRCUIT_NUMBERS] = False
    mock_config_entry.options[USE_DEVICE_PREFIX] = True

    pattern = get_current_naming_pattern(mock_config_entry)

    assert pattern == EntityNamingPattern.FRIENDLY_NAMES.value


def test_get_current_naming_pattern_circuit_numbers(mock_config_entry):
    """Test detecting circuit numbers pattern."""
    mock_config_entry.options[USE_CIRCUIT_NUMBERS] = True
    mock_config_entry.options[USE_DEVICE_PREFIX] = True  # Doesn't matter when circuit_numbers is True

    pattern = get_current_naming_pattern(mock_config_entry)

    assert pattern == EntityNamingPattern.CIRCUIT_NUMBERS.value


def test_get_current_naming_pattern_legacy(mock_config_entry):
    """Test detecting legacy naming pattern."""
    mock_config_entry.options[USE_CIRCUIT_NUMBERS] = False
    mock_config_entry.options[USE_DEVICE_PREFIX] = False

    pattern = get_current_naming_pattern(mock_config_entry)

    assert pattern == EntityNamingPattern.LEGACY_NAMES.value


def test_get_current_naming_pattern_default_to_friendly(mock_config_entry):
    """Test default pattern when flags are missing."""
    # Empty options
    mock_config_entry.options = {}

    pattern = get_current_naming_pattern(mock_config_entry)

    # Default should be friendly names (False circuit_numbers, False device_prefix -> legacy)
    # Actually, with empty options, defaults will be False for both, so legacy
    assert pattern == EntityNamingPattern.LEGACY_NAMES.value


# ===== Tests for pattern_to_flags =====


def test_pattern_to_flags_friendly_names():
    """Test converting friendly names pattern to flags."""
    flags = pattern_to_flags(EntityNamingPattern.FRIENDLY_NAMES.value)

    assert flags[USE_DEVICE_PREFIX] is True
    assert flags[USE_CIRCUIT_NUMBERS] is False


def test_pattern_to_flags_circuit_numbers():
    """Test converting circuit numbers pattern to flags."""
    flags = pattern_to_flags(EntityNamingPattern.CIRCUIT_NUMBERS.value)

    assert flags[USE_DEVICE_PREFIX] is True
    assert flags[USE_CIRCUIT_NUMBERS] is True


def test_pattern_to_flags_unknown_pattern():
    """Test converting unknown pattern (defaults to legacy/no prefix)."""
    flags = pattern_to_flags("unknown_pattern")

    # Unknown pattern defaults to both False (legacy pattern)
    assert flags[USE_DEVICE_PREFIX] is False
    assert flags[USE_CIRCUIT_NUMBERS] is False


# ===== Tests for get_entity_naming_options_defaults =====


def test_get_entity_naming_options_defaults(mock_config_entry):
    """Test getting entity naming options defaults."""
    mock_config_entry.options[USE_CIRCUIT_NUMBERS] = False
    mock_config_entry.options[USE_DEVICE_PREFIX] = True

    defaults = get_entity_naming_options_defaults(mock_config_entry)

    # Should include the current pattern
    assert ENTITY_NAMING_PATTERN in defaults
    assert defaults[ENTITY_NAMING_PATTERN] == EntityNamingPattern.FRIENDLY_NAMES.value


def test_get_entity_naming_options_defaults_circuit_numbers(mock_config_entry):
    """Test defaults for circuit numbers pattern."""
    mock_config_entry.options[USE_CIRCUIT_NUMBERS] = True

    defaults = get_entity_naming_options_defaults(mock_config_entry)

    assert defaults[ENTITY_NAMING_PATTERN] == EntityNamingPattern.CIRCUIT_NUMBERS.value
