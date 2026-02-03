"""Test switch task tracking and error handling.

Tests for Phase 1.1: Fix Fire-and-Forget Async Tasks
Verifies that switch operations properly track async tasks and handle errors.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import pytest


@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


def create_mock_circuit(
    circuit_id: str = "1",
    name: str = "Test Circuit",
    relay_state: str = "CLOSED",
    is_user_controllable: bool = True,
):
    """Create a mock circuit for testing."""
    circuit = MagicMock()
    circuit.id = circuit_id
    circuit.name = name
    circuit.relay_state = relay_state
    circuit.is_user_controllable = is_user_controllable
    circuit.tabs = [int(circuit_id)]
    circuit.copy.return_value = circuit
    return circuit


def create_mock_span_panel(circuits: dict[str, Any]):
    """Create a mock SpanPanel with circuits."""
    panel = MagicMock()
    panel.circuits = circuits
    panel.status.serial_number = "TEST123"
    panel.api = AsyncMock()
    return panel


@pytest.mark.asyncio
async def test_switch_tracks_background_tasks(hass: Any, enable_custom_integrations: Any):
    """Test that switches have background task tracking capability."""
    from custom_components.span_panel.switch import async_setup_entry

    # Create test circuit
    circuit = create_mock_circuit(circuit_id="1", name="Test Circuit")
    circuits = {"1": circuit}
    mock_panel = create_mock_span_panel(circuits)

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

    # Verify switch was created
    assert len(entities) == 1
    switch = entities[0]

    # Verify switch has background task tracking
    assert hasattr(switch, "_background_tasks")
    assert isinstance(switch._background_tasks, set)
    assert len(switch._background_tasks) == 0


@pytest.mark.asyncio
async def test_switch_api_failure_logs_error(
    hass: Any, enable_custom_integrations: Any, caplog: Any
):
    """Test that API failures during switch operations are properly logged."""
    from custom_components.span_panel.switch import async_setup_entry

    # Create test circuit
    circuit = create_mock_circuit(circuit_id="1", name="Kitchen Lights")
    circuits = {"1": circuit}
    mock_panel = create_mock_span_panel(circuits)

    # Mock API to raise an exception
    mock_panel.api.set_relay = AsyncMock(side_effect=Exception("API connection failed"))

    # Create mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data = mock_panel
    mock_coordinator.config_entry = MagicMock()
    mock_coordinator.config_entry.title = "SPAN Panel"
    mock_coordinator.config_entry.data = {}
    mock_coordinator.config_entry.options = {}
    mock_coordinator.hass = hass
    mock_coordinator.async_request_refresh = AsyncMock()

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

    # Attempt to turn on - should fail but be logged
    with caplog.at_level("ERROR"):
        try:
            await switch.async_turn_on()
        except Exception:
            pass  # Expected to fail

    # Verify error was logged with context
    assert any(
        "Failed to turn on switch" in record.message
        and "circuit_id" in record.message.lower()
        for record in caplog.records
    ), "Expected error log with circuit_id context not found"


@pytest.mark.asyncio
async def test_switch_cleanup_on_removal(hass: Any, enable_custom_integrations: Any):
    """Test that background tasks are cleaned up when switch is removed."""
    from custom_components.span_panel.switch import async_setup_entry

    # Create test circuit
    circuit = create_mock_circuit(circuit_id="1", name="Test Circuit")
    circuits = {"1": circuit}
    mock_panel = create_mock_span_panel(circuits)

    # Mock API with a slow response to keep task alive
    async def slow_api_call(*args, **kwargs):
        await asyncio.sleep(0.5)

    mock_panel.api.set_relay = AsyncMock(side_effect=slow_api_call)

    # Create mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data = mock_panel
    mock_coordinator.config_entry = MagicMock()
    mock_coordinator.config_entry.title = "SPAN Panel"
    mock_coordinator.config_entry.data = {}
    mock_coordinator.config_entry.options = {}
    mock_coordinator.hass = hass
    mock_coordinator.async_request_refresh = AsyncMock()

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

    # Start an operation (don't wait)
    switch.turn_on()

    # Give task a moment to start
    await asyncio.sleep(0.05)

    # Verify task is tracked
    assert len(switch._background_tasks) > 0

    # Simulate entity removal
    await switch.async_will_remove_from_hass()

    # Verify tasks were cleaned up
    assert len(switch._background_tasks) == 0


@pytest.mark.asyncio
async def test_switch_task_cleanup_after_completion(
    hass: Any, enable_custom_integrations: Any
):
    """Test that tasks are automatically cleaned up after completion."""
    from custom_components.span_panel.switch import async_setup_entry

    # Create test circuit
    circuit = create_mock_circuit(circuit_id="1", name="HVAC")
    circuits = {"1": circuit}
    mock_panel = create_mock_span_panel(circuits)
    mock_panel.api.set_relay = AsyncMock()

    # Create mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data = mock_panel
    mock_coordinator.config_entry = MagicMock()
    mock_coordinator.config_entry.title = "SPAN Panel"
    mock_coordinator.config_entry.data = {}
    mock_coordinator.config_entry.options = {}
    mock_coordinator.hass = hass
    mock_coordinator.async_request_refresh = AsyncMock()

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

    # Call turn_on (which creates a fire-and-forget task)
    switch.turn_on()

    # Give task time to execute and clean itself up
    await asyncio.sleep(0.1)

    # Verify task was cleaned up after completion
    assert len(switch._background_tasks) == 0
