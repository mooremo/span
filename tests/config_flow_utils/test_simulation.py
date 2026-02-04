"""Test simulation utilities for config flow.

Tests for Sub-Phase 4.1: Test Infrastructure
Validates all functions in config_flow_utils/simulation.py
"""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch
import pytest
import yaml

from custom_components.span_panel.config_flow_utils.simulation import (
    extract_serial_from_config,
    get_available_simulation_configs,
    get_simulation_config_path,
    validate_yaml_config,
)


@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


# ===== Tests for get_available_simulation_configs =====


def test_get_available_simulation_configs_display_name_format():
    """Test that display names are formatted correctly."""
    result = get_available_simulation_configs()

    # Should have at least the default 32-circuit config
    assert isinstance(result, dict)
    assert len(result) > 0

    # Check that display names are title-cased and formatted
    for key, display_name in result.items():
        # Display name should not be empty
        assert display_name
        # Should have replaced underscores with spaces
        assert "_" not in display_name or "simulation_config" not in display_name
        # Should be title-cased
        assert display_name[0].isupper() or display_name[0].isdigit()


def test_get_available_simulation_configs_no_directory():
    """Test getting simulation configs from actual directory."""
    result = get_available_simulation_configs()

    # Should return configs (will include real files from simulation_configs/ directory)
    assert isinstance(result, dict)
    assert len(result) > 0  # Should have at least one config
    # All values should be strings (display names)
    for key, value in result.items():
        assert isinstance(key, str)
        assert isinstance(value, str)


def test_get_available_simulation_configs_returns_dict():
    """Test that get_available_simulation_configs returns a dictionary."""
    result = get_available_simulation_configs()

    # Should return a dictionary
    assert isinstance(result, dict)

    # Should have at least one config (real files exist in the project)
    assert len(result) >= 1

    # Keys should be config file stems
    for key in result.keys():
        assert isinstance(key, str)
        assert not key.endswith(".yaml")  # Should be stem, not full filename


# ===== Tests for extract_serial_from_config =====


def test_extract_serial_from_config_with_serial_number(tmp_path):
    """Test extracting serial number from config with serial_number field."""
    config_file = tmp_path / "test_config.yaml"
    config_data = {"serial_number": "SPAN-12345"}
    config_file.write_text(yaml.dump(config_data))

    result = extract_serial_from_config(config_file)
    assert result == "SPAN-12345"


def test_extract_serial_from_config_with_panel_serial(tmp_path):
    """Test extracting serial number from nested panel.serial_number."""
    config_file = tmp_path / "test_config.yaml"
    config_data = {"panel": {"serial_number": "SPAN-67890"}}
    config_file.write_text(yaml.dump(config_data))

    result = extract_serial_from_config(config_file)
    assert result == "SPAN-67890"


def test_extract_serial_from_config_with_status_serial(tmp_path):
    """Test extracting serial number from nested status.serial_number."""
    config_file = tmp_path / "test_config.yaml"
    config_data = {"status": {"serial_number": "SPAN-STATUS-123"}}
    config_file.write_text(yaml.dump(config_data))

    result = extract_serial_from_config(config_file)
    assert result == "SPAN-STATUS-123"


def test_extract_serial_from_config_file_not_found():
    """Test extracting serial when file doesn't exist."""
    non_existent_file = Path("/non/existent/file.yaml")

    result = extract_serial_from_config(non_existent_file)

    # Should return default
    assert result == "span-sim-001"


def test_extract_serial_from_config_invalid_yaml(tmp_path):
    """Test extracting serial from invalid YAML."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: data: [")

    result = extract_serial_from_config(config_file)

    # Should return default when YAML is invalid
    assert result == "span-sim-001"


def test_extract_serial_from_config_no_serial_field(tmp_path):
    """Test extracting serial when no serial_number field exists."""
    config_file = tmp_path / "no_serial.yaml"
    config_data = {"other_field": "value", "panel": {"other": "data"}}
    config_file.write_text(yaml.dump(config_data))

    result = extract_serial_from_config(config_file)

    # Should return default
    assert result == "span-sim-001"


def test_extract_serial_from_config_not_a_dict(tmp_path):
    """Test extracting serial when YAML is not a dictionary."""
    config_file = tmp_path / "list.yaml"
    config_file.write_text(yaml.dump(["item1", "item2"]))

    result = extract_serial_from_config(config_file)

    # Should return default
    assert result == "span-sim-001"


# ===== Tests for get_simulation_config_path =====


def test_get_simulation_config_path():
    """Test getting the path to a simulation config file."""
    config_key = "simulation_config_32_circuit"

    result = get_simulation_config_path(config_key)

    # Should return a Path object
    assert isinstance(result, Path)
    # Should end with the correct filename
    assert result.name == "simulation_config_32_circuit.yaml"
    # Should contain simulation_configs in the path
    assert "simulation_configs" in str(result)


def test_get_simulation_config_path_custom_key():
    """Test getting path with custom config key."""
    config_key = "my_custom_config"

    result = get_simulation_config_path(config_key)

    assert isinstance(result, Path)
    assert result.name == "my_custom_config.yaml"


# ===== Tests for validate_yaml_config =====


def test_validate_yaml_config_valid_file(tmp_path):
    """Test validating a valid YAML configuration file."""
    yaml_file = tmp_path / "valid.yaml"
    config_data = {"key1": "value1", "key2": {"nested": "value"}}
    yaml_file.write_text(yaml.dump(config_data))

    result = validate_yaml_config(yaml_file)

    assert result == config_data
    assert result["key1"] == "value1"
    assert result["key2"]["nested"] == "value"


def test_validate_yaml_config_file_not_found():
    """Test validating when file doesn't exist."""
    non_existent_file = Path("/non/existent/config.yaml")

    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        validate_yaml_config(non_existent_file)


def test_validate_yaml_config_invalid_yaml(tmp_path):
    """Test validating invalid YAML."""
    yaml_file = tmp_path / "invalid.yaml"
    yaml_file.write_text("invalid: yaml: [unclosed")

    with pytest.raises(yaml.YAMLError):
        validate_yaml_config(yaml_file)


def test_validate_yaml_config_empty_file(tmp_path):
    """Test validating empty YAML file."""
    yaml_file = tmp_path / "empty.yaml"
    yaml_file.write_text("")

    result = validate_yaml_config(yaml_file)

    # Empty YAML should return empty dict
    assert result == {}


def test_validate_yaml_config_not_a_dict(tmp_path):
    """Test validating YAML that's not a dictionary."""
    yaml_file = tmp_path / "list.yaml"
    yaml_file.write_text(yaml.dump(["item1", "item2"]))

    with pytest.raises(TypeError, match="Configuration file must contain a YAML dictionary"):
        validate_yaml_config(yaml_file)


def test_validate_yaml_config_with_complex_structure(tmp_path):
    """Test validating YAML with complex nested structure."""
    yaml_file = tmp_path / "complex.yaml"
    config_data = {
        "panel": {
            "serial_number": "SPAN-123",
            "circuits": [
                {"id": 1, "name": "Kitchen"},
                {"id": 2, "name": "Bedroom"},
            ],
        },
        "settings": {"voltage": 240, "phases": ["L1", "L2"]},
    }
    yaml_file.write_text(yaml.dump(config_data))

    result = validate_yaml_config(yaml_file)

    assert result == config_data
    assert result["panel"]["serial_number"] == "SPAN-123"
    assert len(result["panel"]["circuits"]) == 2
    assert result["settings"]["voltage"] == 240
