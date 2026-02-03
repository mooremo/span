"""Factory functions for creating Span Panel sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.span_panel.const import (
    ENABLE_CIRCUIT_NET_ENERGY_SENSORS,
    ENABLE_PANEL_NET_ENERGY_SENSORS,
    ENABLE_SOLAR_NET_ENERGY_SENSORS,
)
from custom_components.span_panel.coordinator import SpanPanelCoordinator
from custom_components.span_panel.options import (
    BATTERY_ENABLE,
    INVERTER_ENABLE,
    INVERTER_LEG1,
    INVERTER_LEG2,
)
from custom_components.span_panel.sensor_definitions import (
    BATTERY_SENSOR,
    CIRCUIT_SENSORS,
    PANEL_DATA_STATUS_SENSORS,
    PANEL_ENERGY_SENSORS,
    PANEL_POWER_SENSORS,
    SOLAR_SENSORS,
    STATUS_SENSORS,
    UNMAPPED_SENSORS,
)
from custom_components.span_panel.span_panel import SpanPanel

from .circuit import SpanCircuitEnergySensor, SpanCircuitPowerSensor, SpanUnmappedCircuitSensor
from .panel import (
    SpanPanelBattery,
    SpanPanelEnergySensor,
    SpanPanelPanelStatus,
    SpanPanelPowerSensor,
    SpanPanelStatus,
)
from .solar import SpanSolarEnergySensor, SpanSolarSensor

_LOGGER: logging.Logger = logging.getLogger(__name__)


def create_panel_sensors(
    coordinator: SpanPanelCoordinator, span_panel: SpanPanel, config_entry: ConfigEntry
) -> list[SpanPanelPanelStatus | SpanPanelStatus | SpanPanelPowerSensor | SpanPanelEnergySensor]:
    """Create panel-level sensors for the entire SPAN panel.

    Panel sensors provide system-wide measurements and status information:
    - Power sensors: Grid power, feedthrough power (Watts)
    - Energy sensors: Main meter consumed/produced, net energy (kWh)
    - Status sensors: DSM state, grid state, run configuration
    - Hardware sensors: Door state, network connectivity (WiFi/Cellular/Ethernet)

    All sensors are created from predefined entity descriptions in sensor_definitions.py.
    """
    entities: list[
        SpanPanelPanelStatus | SpanPanelStatus | SpanPanelPowerSensor | SpanPanelEnergySensor
    ] = []

    # Panel Data Status Sensors: DSM State, DSM Grid State, Run Configuration
    # These show operational state (on-grid, off-grid, backup mode)
    # Examples: sensor.span_panel_dsm_state, sensor.span_panel_run_config
    for description in PANEL_DATA_STATUS_SENSORS:
        entities.append(SpanPanelPanelStatus(coordinator, description, span_panel))

    # Panel Power Sensors: Instantaneous power measurements in Watts
    # Examples: sensor.span_panel_instant_grid_power, sensor.span_panel_feedthrough_power
    # These replace legacy synthetic sensors with native implementations
    for description in PANEL_POWER_SENSORS:
        entities.append(SpanPanelPowerSensor(coordinator, description, span_panel))

    # Panel Energy Sensors: Cumulative energy measurements in kWh
    # Includes net energy sensors (imported - exported) if enabled
    panel_net_energy_enabled = config_entry.options.get(ENABLE_PANEL_NET_ENERGY_SENSORS, True)

    for description in PANEL_ENERGY_SENSORS:
        # Net Energy Filtering: Skip net energy sensors if user disabled them
        # Net energy sensors calculate: energy_consumed - energy_produced
        # Useful for net metering, cost tracking, and Energy Dashboard
        is_net_energy_sensor = "net_energy" in description.key or "NetEnergy" in description.key

        if not panel_net_energy_enabled and is_net_energy_sensor:
            continue  # User disabled, skip this sensor
        entities.append(SpanPanelEnergySensor(coordinator, description, span_panel))

    # Hardware Status Sensors: Physical panel state and connectivity
    # Examples: sensor.span_panel_door_state, sensor.span_panel_wifi_link
    # Door sensor shows OPEN/CLOSED, network sensors show connected/disconnected
    for description_ss in STATUS_SENSORS:
        entities.append(SpanPanelStatus(coordinator, description_ss, span_panel))

    return entities


def create_circuit_sensors(
    coordinator: SpanPanelCoordinator, span_panel: SpanPanel, config_entry: ConfigEntry
) -> list[SpanCircuitPowerSensor | SpanCircuitEnergySensor]:
    """Create individual sensors for each named circuit in the panel.

    Circuit sensors provide per-breaker measurements for each named circuit:
    - Power sensor: Instantaneous power draw (Watts)
    - Energy consumed: Cumulative energy consumed (kWh, total_increasing)
    - Energy produced: Cumulative energy produced (kWh, total_increasing)
    - Net energy: Consumed - produced (kWh, if enabled)

    Unmapped circuits (synthetic placeholders) are excluded here and handled separately
    in create_unmapped_circuit_sensors() for solar/storage calculations.
    """
    entities: list[SpanCircuitPowerSensor | SpanCircuitEnergySensor] = []

    # Named Circuits Filter: Exclude "unmapped_tab_*" synthetic circuits
    # Named circuits have user-assigned names (e.g., "Kitchen Outlets", "HVAC")
    # Unmapped circuits are placeholders created by the panel for unused breaker positions
    # Example named circuits: "1", "2", "3" (circuit IDs from panel)
    # Example unmapped circuits: "unmapped_tab_5", "unmapped_tab_6" (used for solar)
    named_circuits = [cid for cid in span_panel.circuits if not cid.startswith("unmapped_tab_")]
    circuit_net_energy_enabled = config_entry.options.get(ENABLE_CIRCUIT_NET_ENERGY_SENSORS, True)

    # Create sensors for each named circuit
    for circuit_id in named_circuits:
        for circuit_description in CIRCUIT_SENSORS:
            # Net Energy Filtering: Skip if user disabled circuit-level net energy sensors
            # Net energy useful for circuits that both consume and produce (e.g., battery inverters)
            is_net_energy_sensor = (
                "net_energy" in circuit_description.key or "energy_net" in circuit_description.key
            )

            if not circuit_net_energy_enabled and is_net_energy_sensor:
                continue  # User disabled, skip this sensor type

            # Sensor Type Selection: Power vs Energy sensors use different classes
            if circuit_description.key == "circuit_power":
                # Power Sensor: Real-time measurement with attribute-based sub-sensors
                # Provides instant power, relay state, tabs, priority as attributes
                entities.append(
                    SpanCircuitPowerSensor(coordinator, circuit_description, span_panel, circuit_id)
                )
            else:
                # Energy Sensor: Cumulative measurements with grace period support
                # Grace period prevents spurious zero readings during panel startup
                # Integrates with HA Energy Dashboard (total_increasing state class)
                entities.append(
                    SpanCircuitEnergySensor(
                        coordinator, circuit_description, span_panel, circuit_id
                    )
                )

    return entities


def create_unmapped_circuit_sensors(
    coordinator: SpanPanelCoordinator, span_panel: SpanPanel
) -> list[SpanUnmappedCircuitSensor]:
    """Create sensors for unmapped circuits (tabs without assigned breakers).

    UNMAPPED CIRCUIT CONCEPT:
    -------------------------
    Unmapped circuits represent physical tabs in the panel that don't have named circuit
    breakers assigned. These typically occur when:
    1. Solar inverters connect directly to panel tabs (bypassing breakers)
    2. Battery storage systems connect to dedicated tabs
    3. Future expansion slots not yet populated

    WHY CREATE SENSORS FOR THEM:
    - Provide stable entity IDs for solar sensor calculations (solar spans 2 tabs)
    - Enable tracking of energy production/consumption on non-breaker connections
    - Support synthetic solar sensors that combine leg1 + leg2 power/energy
    - Maintain consistency in entity registry across panel reconfigurations

    SENSOR CHARACTERISTICS:
    - Entity IDs: sensor.span_panel_unmapped_tab_5_power (example)
    - Disabled by default in UI (not useful for typical users)
    - Used internally for solar sensor calculations (leg1 + leg2 = total solar)
    - Created automatically when panel reports unmapped tab data

    EXAMPLE USE CASE:
    Solar inverter on tabs 5 & 6 creates:
    - sensor.span_panel_unmapped_tab_5_power (leg 1)
    - sensor.span_panel_unmapped_tab_6_power (leg 2)
    - sensor.span_panel_solar_current_power (combines both legs)
    """
    entities: list[SpanUnmappedCircuitSensor] = []

    # Unmapped Circuits Filter: Select only circuits with "unmapped_tab_" prefix
    # Circuit IDs like "unmapped_tab_5" indicate tab 5 has no assigned breaker
    # These circuits are reported by the panel API but are not user-controllable
    unmapped_circuits = [cid for cid in span_panel.circuits if cid.startswith("unmapped_tab_")]

    for circuit_id in unmapped_circuits:
        for unmapped_description in UNMAPPED_SENSORS:
            # Create sensors using special unmapped sensor class
            # These sensors are identical to regular circuit sensors but:
            # 1. Disabled by default (hidden from UI unless explicitly enabled)
            # 2. Have "unmapped" in entity ID for clear identification
            # 3. Don't show in main circuit list (reduces entity clutter)
            entities.append(
                SpanUnmappedCircuitSensor(coordinator, unmapped_description, span_panel, circuit_id)
            )

    return entities


def create_battery_sensors(
    coordinator: SpanPanelCoordinator, span_panel: SpanPanel, config_entry: ConfigEntry
) -> list[SpanPanelBattery]:
    """Create battery sensors if enabled."""
    entities: list[SpanPanelBattery] = []

    # Add battery sensor if enabled
    battery_enabled = config_entry.options.get(BATTERY_ENABLE, False)
    if battery_enabled:
        entities.append(SpanPanelBattery(coordinator, BATTERY_SENSOR, span_panel))

    return entities


def create_solar_sensors(
    coordinator: SpanPanelCoordinator, span_panel: SpanPanel, config_entry: ConfigEntry
) -> list[SpanSolarSensor | SpanSolarEnergySensor]:
    """Create solar production sensors for 240V split-phase solar inverters.

    SOLAR SENSOR ARCHITECTURE:
    -------------------------
    Solar inverters in residential settings typically connect as 240V split-phase:
    - Leg 1: One phase (120V) connected to tab X (e.g., tab 5)
    - Leg 2: Other phase (120V) connected to tab Y (e.g., tab 6)
    - Combined: Total solar production = leg1_power + leg2_power

    Created solar sensors combine both legs to show total production:
    - sensor.span_panel_solar_current_power (W, real-time)
    - sensor.span_panel_solar_energy_produced_today (kWh, daily reset)
    - sensor.span_panel_solar_energy_produced_total (kWh, cumulative)
    - sensor.span_panel_solar_net_energy (kWh, if enabled)

    Configuration requirements:
    - User must enable solar sensors in options
    - User must specify tab numbers for both legs (1-32 typical, up to 40)
    - Tabs must have unmapped circuits (solar bypasses breakers)
    """
    entities: list[SpanSolarSensor | SpanSolarEnergySensor] = []

    # Solar Enabled Check: Exit early if user hasn't enabled solar sensors
    solar_enabled = config_entry.options.get(INVERTER_ENABLE, False)
    if not solar_enabled:
        return entities  # No solar configuration, skip sensor creation

    # Solar Tab Configuration: Extract user-configured tab numbers
    # User configures in UI: "Solar leg 1: 5", "Solar leg 2: 6"
    # These correspond to physical tab positions on the panel
    leg1_raw = config_entry.options.get(INVERTER_LEG1, 0)
    leg2_raw = config_entry.options.get(INVERTER_LEG2, 0)

    # Type Coercion: Ensure tab numbers are integers
    # UI stores as strings/ints, need consistent type for lookup
    try:
        leg1_tab = int(leg1_raw)
        leg2_tab = int(leg2_raw)
    except (TypeError, ValueError):
        # Invalid tab configuration (e.g., None, empty string)
        leg1_tab = 0
        leg2_tab = 0

    # Configuration Validation: Both legs required for 240V solar
    if leg1_tab <= 0 or leg2_tab <= 0:
        return entities  # Incomplete configuration, skip sensor creation

    # TAB-TO-CIRCUIT LOOKUP (Phase 2.1 Optimization):
    # ================================================
    # BEFORE (O(n²) - nested iteration):
    #   for circuit_id, circuit in span_panel.circuits.items():  # O(n)
    #       if leg1_tab in circuit.tabs:  # Inner check = O(n²) total
    #           leg1_circuit_id = circuit_id
    #
    # AFTER (O(1) - dictionary lookup):
    #   tab_mapping = span_panel.tab_to_circuit_id_map  # Built once, O(n)
    #   leg1_circuit_id = tab_mapping.get(leg1_tab)     # O(1) lookup
    #
    # Performance Impact: 64x faster for 32-circuit panels
    # Eliminates startup lag for solar installations
    tab_mapping = span_panel.tab_to_circuit_id_map
    leg1_circuit_id = tab_mapping.get(leg1_tab)  # e.g., "unmapped_tab_5"
    leg2_circuit_id = tab_mapping.get(leg2_tab)  # e.g., "unmapped_tab_6"

    # Circuit ID Validation: Both legs must have corresponding circuits
    # If tabs don't exist or aren't unmapped, circuit IDs will be None
    if leg1_circuit_id and leg2_circuit_id:
        solar_net_energy_enabled = config_entry.options.get(ENABLE_SOLAR_NET_ENERGY_SENSORS, True)

        for solar_description in SOLAR_SENSORS:
            # Net Energy Filtering: Skip if user disabled solar net energy
            # Solar net energy = produced - consumed (usually just produced for solar)
            if not solar_net_energy_enabled and "net_energy" in solar_description.key:
                continue  # User disabled, skip this sensor type

            # Sensor Type Selection: Power vs Energy sensors
            if solar_description.key == "solar_current_power":
                # Solar Power Sensor: Real-time production (Watts)
                # Combines leg1_power + leg2_power for total output
                # Updates every scan interval (default: 15 seconds)
                entities.append(
                    SpanSolarSensor(
                        coordinator,
                        solar_description,
                        span_panel,
                        leg1_circuit_id,
                        leg2_circuit_id,
                    )
                )
            else:
                # Solar Energy Sensor: Cumulative production (kWh)
                # Integrates with HA Energy Dashboard
                # Supports grace period to prevent startup zero readings
                # total_increasing state class for statistics
                entities.append(
                    SpanSolarEnergySensor(
                        coordinator,
                        solar_description,
                        span_panel,
                        leg1_circuit_id,
                        leg2_circuit_id,
                    )
                )

    return entities


def create_native_sensors(
    coordinator: SpanPanelCoordinator, span_panel: SpanPanel, config_entry: ConfigEntry
) -> list[
    SpanPanelPanelStatus
    | SpanPanelStatus
    | SpanPanelPowerSensor
    | SpanPanelEnergySensor
    | SpanCircuitPowerSensor
    | SpanCircuitEnergySensor
    | SpanUnmappedCircuitSensor
    | SpanPanelBattery
    | SpanSolarSensor
    | SpanSolarEnergySensor
]:
    """Create all native sensors for the SPAN Panel platform.

    SENSOR CREATION HIERARCHY:
    -------------------------
    This is the main entry point called by async_setup_entry() in sensor.py.
    It orchestrates creation of all sensor types in a specific order:

    1. Panel Sensors (5-10 entities):
       - System status (DSM state, grid state, run config)
       - Power measurements (grid power, feedthrough power)
       - Energy totals (main meter consumed/produced, net energy)
       - Hardware status (door, network connectivity)

    2. Circuit Sensors (3-4 per circuit, typically 96-128 entities for 32 circuits):
       - Power (instantaneous Watts)
       - Energy consumed (cumulative kWh)
       - Energy produced (cumulative kWh, if applicable)
       - Net energy (consumed - produced, if enabled)

    3. Unmapped Circuit Sensors (2 per unmapped tab, typically 0-8 entities):
       - Created for tabs without assigned breakers
       - Disabled by default (not useful for most users)
       - Used internally for solar sensor calculations

    4. Battery Sensors (0-1 entity):
       - Battery percentage (if battery storage present and enabled)

    5. Solar Sensors (0-4 entities):
       - Combined solar power (leg1 + leg2)
       - Solar energy produced today/total
       - Solar net energy (if enabled)

    Total entity count varies based on configuration:
    - Minimal: ~100-130 entities (32 circuits, no solar/battery)
    - Typical: ~110-140 entities (32 circuits, solar enabled)
    - Maximum: ~150+ entities (40 circuits, solar, battery, all net energy)

    All sensors respect user configuration options for:
    - Net energy sensor creation (can be disabled per category)
    - Solar sensor creation (requires leg configuration)
    - Battery sensor creation (requires hardware support)
    """
    entities: list[
        SpanPanelPanelStatus
        | SpanPanelStatus
        | SpanPanelPowerSensor
        | SpanPanelEnergySensor
        | SpanCircuitPowerSensor
        | SpanCircuitEnergySensor
        | SpanUnmappedCircuitSensor
        | SpanPanelBattery
        | SpanSolarSensor
        | SpanSolarEnergySensor
    ] = []

    # Sensor Creation Order (aggregates results from specialized factory functions):
    # Order doesn't affect functionality but logical grouping aids debugging logs
    entities.extend(create_panel_sensors(coordinator, span_panel, config_entry))
    entities.extend(create_circuit_sensors(coordinator, span_panel, config_entry))
    entities.extend(create_unmapped_circuit_sensors(coordinator, span_panel))
    entities.extend(create_battery_sensors(coordinator, span_panel, config_entry))
    entities.extend(create_solar_sensors(coordinator, span_panel, config_entry))

    return entities


def enable_unmapped_tab_entities(hass: HomeAssistant, entities: list[Any]) -> None:
    """Automatically enable unmapped tab entities that were previously disabled.

    BACKGROUND:
    ----------
    Unmapped tab sensors are created disabled by default because they're typically
    not useful for end users (they represent tabs without circuit breakers). However,
    when solar sensors are configured, these unmapped tab entities become necessary
    for internal calculations (solar = leg1 + leg2).

    PURPOSE:
    -------
    When a user enables solar sensors and configures leg tabs:
    1. Solar sensors (create_solar_sensors) are created enabled
    2. Unmapped tab sensors for those legs may exist but be disabled
    3. This function automatically enables them to support solar calculations
    4. Prevents "entity unavailable" errors in solar sensor calculations

    WHEN CALLED:
    -----------
    - After all sensors are created in async_setup_entry()
    - Only affects entities with "unmapped_tab_" in unique_id
    - Only enables entities that were previously disabled by user/system
    - Does not affect newly created entities (already enabled by default logic)

    EXAMPLE SCENARIO:
    ----------------
    1. User has unmapped tabs 5 & 6 (no breakers installed)
    2. Panel creates unmapped circuit sensors (disabled by default)
    3. User later configures solar: leg1=5, leg2=6
    4. Solar sensors need data from unmapped_tab_5 and unmapped_tab_6
    5. This function enables those specific unmapped sensors automatically
    6. Solar calculations work without manual entity enabling
    """
    entity_registry = er.async_get(hass)

    for entity in entities:
        # Unmapped Tab Detection: Check if this entity represents an unmapped tab
        # Unmapped tab entities have "unmapped_tab_" in their unique_id
        # Example: "DSM010000ABC-unmapped_tab_5-power"
        if (
            hasattr(entity, "unique_id")
            and entity.unique_id
            and "unmapped_tab_" in entity.unique_id
        ):
            entity_id = entity.entity_id  # e.g., "sensor.span_panel_unmapped_tab_5_power"
            registry_entry = entity_registry.async_get(entity_id)

            # Enable if Previously Disabled: Only modify entities explicitly disabled
            # Respects user preference if they manually disabled after auto-enable
            if registry_entry and registry_entry.disabled:
                _LOGGER.debug("Enabling previously disabled unmapped tab entity: %s", entity_id)
                # disabled_by=None means "not disabled" (enable the entity)
                entity_registry.async_update_entity(entity_id, disabled_by=None)
