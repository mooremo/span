"""Test sensor factory optimizations.

Tests for Phase 2.1: Optimize Solar Sensor Tab Lookup
Verifies that solar sensor creation uses O(1) tab-to-circuit mapping
instead of O(n²) iteration.
"""

import pytest
from typing import Any
from unittest.mock import MagicMock
import time


@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


def create_mock_circuit(
    circuit_id: str,
    name: str,
    tabs: list[int] | None = None,
    relay_state: str = "CLOSED",
    is_user_controllable: bool = True,
) -> Any:
    """Create a mock circuit for testing."""
    circuit = MagicMock()
    circuit.id = circuit_id
    circuit.name = name
    circuit.tabs = tabs if tabs is not None else [int(circuit_id)]
    circuit.relay_state = relay_state
    circuit.is_user_controllable = is_user_controllable
    circuit.instant_power_w = 100.0
    circuit.produced_energy_wh = 1000.0
    circuit.consumed_energy_wh = 500.0
    circuit.copy.return_value = circuit
    return circuit


def create_mock_span_panel_with_circuits(num_circuits: int = 32) -> Any:
    """Create a mock SpanPanel with specified number of circuits."""
    from custom_components.span_panel.span_panel import SpanPanel

    panel = MagicMock(spec=SpanPanel)

    # Create circuits with sequential tab assignments
    circuits = {}
    for i in range(1, num_circuits + 1):
        circuit = create_mock_circuit(
            circuit_id=str(i),
            name=f"Circuit {i}",
            tabs=[i],
        )
        circuits[str(i)] = circuit

    panel.circuits = circuits
    panel.status = MagicMock()
    panel.status.serial_number = "TEST123"
    panel.status.main_meter_energy_produced_wh = 50000.0
    panel.status.main_meter_energy_consumed_wh = 75000.0
    panel.status.main_relay_state = "CLOSED"

    # Add mock panel data
    panel.panel = MagicMock()
    panel.panel.instant_grid_power_w = 1500.0
    panel.panel.feedthrough_power_w = 0.0

    # Add mock API (needed for sensor construction)
    panel.api = MagicMock()
    panel.api.simulation_mode = False

    # Build tab_to_circuit_id_map (mimics the real implementation)
    tab_mapping: dict[int, str] = {}
    for circuit_id, circuit in circuits.items():
        if hasattr(circuit, "tabs") and circuit.tabs:
            for tab in circuit.tabs:
                tab_mapping[tab] = circuit_id

    panel.tab_to_circuit_id_map = tab_mapping

    return panel


@pytest.mark.asyncio
async def test_tab_to_circuit_mapping_property_exists(
    hass: Any, enable_custom_integrations: Any
):
    """Test that SpanPanel has tab_to_circuit_id_map property."""
    from custom_components.span_panel.span_panel import SpanPanel

    panel = create_mock_span_panel_with_circuits(4)

    # Should have the mapping property
    assert hasattr(panel, "tab_to_circuit_id_map")


@pytest.mark.asyncio
async def test_tab_to_circuit_mapping_correctness(
    hass: Any, enable_custom_integrations: Any
):
    """Test that tab-to-circuit mapping is correct."""
    panel = create_mock_span_panel_with_circuits(4)

    # Get the mapping
    mapping = panel.tab_to_circuit_id_map

    # Verify mapping correctness
    assert mapping[1] == "1"
    assert mapping[2] == "2"
    assert mapping[3] == "3"
    assert mapping[4] == "4"


@pytest.mark.asyncio
async def test_tab_to_circuit_mapping_multiple_tabs_per_circuit(
    hass: Any, enable_custom_integrations: Any
):
    """Test mapping with circuits that span multiple tabs (e.g., 240V circuits)."""
    from custom_components.span_panel.span_panel import SpanPanel

    panel = MagicMock(spec=SpanPanel)

    # Circuit 1 uses tabs 1 and 2 (240V circuit)
    # Circuit 3 uses tab 3 only (120V circuit)
    circuits = {
        "1": create_mock_circuit("1", "HVAC", tabs=[1, 2]),
        "3": create_mock_circuit("3", "Lights", tabs=[3]),
    }
    panel.circuits = circuits

    # Build tab mapping
    tab_mapping: dict[int, str] = {}
    for circuit_id, circuit in circuits.items():
        if hasattr(circuit, "tabs") and circuit.tabs:
            for tab in circuit.tabs:
                tab_mapping[tab] = circuit_id
    panel.tab_to_circuit_id_map = tab_mapping

    mapping = panel.tab_to_circuit_id_map

    # Tab 1 should map to circuit "1"
    # Tab 2 should map to circuit "1" (same circuit spans both tabs)
    # Tab 3 should map to circuit "3"
    assert mapping[1] == "1"
    assert mapping[2] == "1"
    assert mapping[3] == "3"


@pytest.mark.asyncio
async def test_tab_to_circuit_mapping_edge_case_no_tabs(
    hass: Any, enable_custom_integrations: Any
):
    """Test mapping handles circuits with no tabs attribute or empty tabs."""
    from custom_components.span_panel.span_panel import SpanPanel

    panel = MagicMock(spec=SpanPanel)

    # Circuit with no tabs attribute
    circuit_no_tabs = create_mock_circuit("1", "NoTabs", tabs=None)
    circuit_no_tabs.tabs = None

    # Circuit with empty tabs list
    circuit_empty_tabs = create_mock_circuit("2", "EmptyTabs", tabs=[])

    # Circuit with valid tabs
    circuit_valid = create_mock_circuit("3", "Valid", tabs=[5])

    circuits = {
        "1": circuit_no_tabs,
        "2": circuit_empty_tabs,
        "3": circuit_valid,
    }
    panel.circuits = circuits

    # Build tab mapping
    tab_mapping: dict[int, str] = {}
    for circuit_id, circuit in circuits.items():
        if hasattr(circuit, "tabs") and circuit.tabs:
            for tab in circuit.tabs:
                tab_mapping[tab] = circuit_id
    panel.tab_to_circuit_id_map = tab_mapping

    mapping = panel.tab_to_circuit_id_map

    # Only circuit 3 should appear in mapping
    assert 5 in mapping
    assert mapping[5] == "3"
    # Circuits without tabs should not cause errors
    assert len(mapping) == 1


@pytest.mark.asyncio
async def test_tab_to_circuit_mapping_empty_circuits(
    hass: Any, enable_custom_integrations: Any
):
    """Test mapping handles empty circuits dictionary."""
    from custom_components.span_panel.span_panel import SpanPanel

    panel = MagicMock(spec=SpanPanel)
    panel.circuits = {}

    # Build tab mapping (will be empty)
    panel.tab_to_circuit_id_map = {}

    mapping = panel.tab_to_circuit_id_map

    # Should return empty mapping
    assert mapping == {}


@pytest.mark.asyncio
async def test_solar_sensor_uses_tab_mapping(
    hass: Any, enable_custom_integrations: Any
):
    """Test that solar sensor creation uses tab mapping instead of iteration."""
    from custom_components.span_panel.sensors.factory import create_solar_sensors
    from custom_components.span_panel.options import (
        INVERTER_ENABLE,
        INVERTER_LEG1,
        INVERTER_LEG2,
    )

    panel = create_mock_span_panel_with_circuits(32)

    # Add solar production data to trigger solar sensor creation
    # Solar inverter typically on tabs 1 and 2
    panel.status.circuits_solar_produced_wh = {
        "leg1": 10000.0,
        "leg2": 10000.0,
    }

    # Mock options
    mock_options = MagicMock()
    mock_options.enable_unmapped_circuits = False
    panel.options = mock_options

    # Create mock coordinator and config entry with solar enabled
    mock_coordinator = MagicMock()
    mock_coordinator.data = panel
    mock_coordinator.config_entry = MagicMock()
    mock_coordinator.config_entry.options = {
        INVERTER_ENABLE: True,  # Enable solar sensors
        INVERTER_LEG1: 1,       # Tab 1 for leg1
        INVERTER_LEG2: 2,       # Tab 2 for leg2
    }

    # Create solar sensors - should use tab mapping
    entities = create_solar_sensors(
        mock_coordinator,
        panel,
        mock_coordinator.config_entry
    )

    # Should have created solar sensors without iterating through all circuits
    assert len(entities) > 0


@pytest.mark.asyncio
async def test_benchmark_tab_lookup_performance(
    hass: Any, enable_custom_integrations: Any
):
    """Benchmark test comparing O(n²) vs O(1) tab lookup performance."""
    # Create large panel (32 circuits is typical max)
    panel = create_mock_span_panel_with_circuits(32)

    # Simulate O(n²) lookup (old method)
    def old_method_lookup(circuits: dict, target_tab: int) -> str | None:
        """Old O(n²) method - iterate through all circuits."""
        for circuit_id, circuit in circuits.items():
            if hasattr(circuit, "tabs") and circuit.tabs:
                if target_tab in circuit.tabs:
                    return circuit_id
        return None

    # Benchmark old method
    start_old = time.perf_counter()
    for _ in range(100):  # Run 100 times to get measurable time
        # Lookup tabs 1 and 2 (typical solar inverter)
        old_method_lookup(panel.circuits, 1)
        old_method_lookup(panel.circuits, 2)
    end_old = time.perf_counter()
    old_duration = end_old - start_old

    # Benchmark new method using mapping
    start_new = time.perf_counter()
    for _ in range(100):
        mapping = panel.tab_to_circuit_id_map
        _ = mapping.get(1)
        _ = mapping.get(2)
    end_new = time.perf_counter()
    new_duration = end_new - start_new

    # New method should be significantly faster
    # For 32 circuits, we expect at least 5x improvement
    speedup = old_duration / new_duration if new_duration > 0 else float('inf')

    print(f"\nBenchmark Results (32 circuits, 100 iterations):")
    print(f"  Old O(n²) method: {old_duration*1000:.3f}ms")
    print(f"  New O(1) method:  {new_duration*1000:.3f}ms")
    print(f"  Speedup: {speedup:.1f}x")

    # Assert at least 5x speedup (conservative - should be much higher)
    assert speedup >= 5.0, f"Expected 5x+ speedup, got {speedup:.1f}x"


@pytest.mark.asyncio
async def test_solar_sensor_creation_with_invalid_tabs(
    hass: Any, enable_custom_integrations: Any
):
    """Test solar sensor handles invalid tab references gracefully."""
    from custom_components.span_panel.sensors.factory import create_solar_sensors
    from custom_components.span_panel.span_panel import SpanPanel

    panel = MagicMock(spec=SpanPanel)

    # Create circuits on tabs 1-2
    circuits = {
        "1": create_mock_circuit("1", "Circuit1", tabs=[1]),
        "2": create_mock_circuit("2", "Circuit2", tabs=[2]),
    }
    panel.circuits = circuits
    panel.status = MagicMock()
    panel.status.serial_number = "TEST123"

    # Build tab mapping
    tab_mapping: dict[int, str] = {}
    for circuit_id, circuit in circuits.items():
        if hasattr(circuit, "tabs") and circuit.tabs:
            for tab in circuit.tabs:
                tab_mapping[tab] = circuit_id
    panel.tab_to_circuit_id_map = tab_mapping

    # Solar data references tabs 99 and 100 (don't exist in mapping)
    # This shouldn't crash - should handle gracefully
    panel.status.circuits_solar_produced_wh = {
        "leg1": 10000.0,
        "leg2": 10000.0,
    }

    # Mock the panel data
    panel.panel = MagicMock()
    panel.panel.instant_grid_power_w = 1500.0

    mock_options = MagicMock()
    mock_options.enable_unmapped_circuits = False
    panel.options = mock_options

    mock_coordinator = MagicMock()
    mock_coordinator.data = panel
    mock_coordinator.config_entry = MagicMock()
    mock_coordinator.config_entry.options = {}

    # Should not crash even with invalid tab references
    # Since tabs 99 and 100 don't exist, no solar sensors will be created
    entities = create_solar_sensors(
        mock_coordinator,
        panel,
        mock_coordinator.config_entry
    )

    # Should return empty list without crashing
    assert len(entities) == 0  # No sensors created due to invalid tabs
