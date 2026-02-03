"""Test switch KeyError handler for missing circuits.

Tests for Phase 1.2: Fix Race Condition in Switch Operations
Verifies that switches handle missing circuits gracefully without raising exceptions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any


@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


def create_mock_circuit(
    circuit_id: str = "1",
    name: str = "Test Circuit",
    relay_state: str = "CLOSED",
):
    """Create a mock circuit for testing."""
    circuit = MagicMock()
    circuit.id = circuit_id
    circuit.name = name
    circuit.relay_state = relay_state
    circuit.is_user_controllable = True
    circuit.tabs = [int(circuit_id)]
    circuit.copy.return_value = circuit
    return circuit


@pytest.mark.asyncio
async def test_switch_turn_on_circuit_missing(
    hass: Any, enable_custom_integrations: Any, caplog: Any
):
    """Test turn_on when circuit disappears (KeyError handling)."""
    from custom_components.span_panel.switch import async_setup_entry

    # Create test circuit
    circuit = create_mock_circuit(circuit_id="1", name="Kitchen Lights")
    circuits = {"1": circuit}
    mock_panel = MagicMock()
    mock_panel.circuits = circuits
    mock_panel.status.serial_number = "TEST123"
    mock_panel.api = AsyncMock()

    # Create mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data = mock_panel
    mock_coordinator.config_entry = MagicMock()
    mock_coordinator.config_entry.title = "SPAN Panel"
    mock_coordinator.config_entry.data = {}
    mock_coordinator.config_entry.options = {}
    mock_coordinator.hass = hass

    entities = []

    def mock_add_entities(new_entities, update_before_add: bool = False):
        entities.extend(new_entities)

    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.title = "SPAN Panel"
    mock_config_entry.data = {}

    hass.data = {
        "span_panel": {
            "test_entry": {
                "coordinator": mock_coordinator,
            }
        }
    }

    # Setup entities
    await async_setup_entry(hass, mock_config_entry, mock_add_entities)
    switch = entities[0]

    # Remove circuit from panel (simulating race condition)
    mock_panel.circuits = {}

    # Attempt to turn on - should handle KeyError gracefully
    with caplog.at_level("WARNING"):
        await switch.async_turn_on()

    # Verify warning was logged with circuit_id
    assert any(
        "Circuit 1" in record.message and "not found" in record.message
        for record in caplog.records
    ), "Expected warning log about missing circuit not found"


@pytest.mark.asyncio
async def test_switch_turn_off_circuit_missing(
    hass: Any, enable_custom_integrations: Any, caplog: Any
):
    """Test turn_off when circuit disappears (KeyError handling)."""
    from custom_components.span_panel.switch import async_setup_entry

    circuit = create_mock_circuit(circuit_id="2", name="Living Room")
    circuits = {"2": circuit}
    mock_panel = MagicMock()
    mock_panel.circuits = circuits
    mock_panel.status.serial_number = "TEST123"
    mock_panel.api = AsyncMock()

    mock_coordinator = MagicMock()
    mock_coordinator.data = mock_panel
    mock_coordinator.config_entry = MagicMock()
    mock_coordinator.config_entry.title = "SPAN Panel"
    mock_coordinator.config_entry.data = {}
    mock_coordinator.config_entry.options = {}
    mock_coordinator.hass = hass

    entities = []

    def mock_add_entities(new_entities, update_before_add: bool = False):
        entities.extend(new_entities)

    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.title = "SPAN Panel"
    mock_config_entry.data = {}

    hass.data = {
        "span_panel": {
            "test_entry": {
                "coordinator": mock_coordinator,
            }
        }
    }

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)
    switch = entities[0]

    # Remove circuit
    mock_panel.circuits = {}

    # Attempt to turn off
    with caplog.at_level("WARNING"):
        await switch.async_turn_off()

    # Verify warning logged
    assert any(
        "Circuit 2" in record.message and "not found" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_switch_missing_circuit_with_none_name(
    hass: Any, enable_custom_integrations: Any, caplog: Any
):
    """Test KeyError handler when circuit name is None."""
    from custom_components.span_panel.switch import async_setup_entry

    # Create circuit with None name
    circuit = create_mock_circuit(circuit_id="3", name=None)
    circuits = {"3": circuit}
    mock_panel = MagicMock()
    mock_panel.circuits = circuits
    mock_panel.status.serial_number = "TEST123"
    mock_panel.api = AsyncMock()

    mock_coordinator = MagicMock()
    mock_coordinator.data = mock_panel
    mock_coordinator.config_entry = MagicMock()
    mock_coordinator.config_entry.title = "SPAN Panel"
    mock_coordinator.config_entry.data = {}
    mock_coordinator.config_entry.options = {}
    mock_coordinator.hass = hass

    entities = []

    def mock_add_entities(new_entities, update_before_add: bool = False):
        entities.extend(new_entities)

    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.title = "SPAN Panel"
    mock_config_entry.data = {}

    hass.data = {
        "span_panel": {
            "test_entry": {
                "coordinator": mock_coordinator,
            }
        }
    }

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)
    switch = entities[0]

    # Remove circuit
    mock_panel.circuits = {}

    # Turn on with None name - should log "unnamed"
    with caplog.at_level("WARNING"):
        await switch.async_turn_on()

    # Verify "unnamed" is in log message
    assert any(
        "unnamed" in record.message and "Circuit 3" in record.message
        for record in caplog.records
    )
