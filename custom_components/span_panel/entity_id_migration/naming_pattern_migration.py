"""Naming pattern migration for Span Panel integration.

Handles migration between different entity naming patterns:
- Friendly names ↔ circuit numbers
- With/without device prefix

Extracted from entity_id_naming_patterns.py as part of Sub-Phase 5.1.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from ..const import DOMAIN
from .registry_helpers import (
    get_circuit_friendly_name,
    get_circuit_tabs_from_coordinator,
    get_device_name_from_registry,
)

_LOGGER = logging.getLogger(__name__)


# Panel-level suffixes - entities with these suffixes should not be migrated
PANEL_LEVEL_SUFFIXES = {
    # Panel data status sensors (from PANEL_DATA_STATUS_SENSORS)
    "dsm_state",
    "dsm_grid_state",
    "current_run_config",
    "main_relay_state",
    # Hardware status sensors (from STATUS_SENSORS)
    "software_version",
    # Binary sensor suffixes (from BINARY_SENSORS)
    "doorState",
    "eth0Link",
    "wlanLink",
    "wwanLink",
    "panel_status",
    # Panel power sensors (from PANEL_POWER_SENSORS)
    "current_power",  # instantGridPowerW
    "feed_through_power",  # feedthroughPowerW
    # Panel energy sensors (from PANEL_ENERGY_SENSORS)
    "main_meter_produced_energy",  # mainMeterEnergyProducedWh
    "main_meter_consumed_energy",  # mainMeterEnergyConsumedWh
    "main_meter_net_energy",  # mainMeterNetEnergyWh
    "feed_through_produced_energy",  # feedthroughEnergyProducedWh
    "feed_through_consumed_energy",  # feedthroughEnergyConsumedWh
    "feed_through_net_energy",  # feedthroughNetEnergyWh
    # Battery sensors
    "battery_level",
    "battery_percentage",
    "storage_battery_percentage",
    # Solar sensors (from SOLAR_SENSORS)
    "solar_current_power",
    "solar_produced_energy",
    "solar_consumed_energy",
    "solar_net_energy",
}


def is_panel_level_entity(unique_id: str) -> bool:
    """Check if the entity is a panel-level entity based on its unique_id pattern.

    Panel-level entities have unique IDs like:
    - span_{serial}_{panel_suffix} (no circuit_id)

    Args:
        unique_id: The unique ID to check

    Returns:
        True if this is a panel-level entity, False otherwise

    """
    return any(unique_id.endswith(f"_{suffix}") for suffix in PANEL_LEVEL_SUFFIXES)


def should_migrate_entity(entity: er.RegistryEntry, sanitized_device_name: str) -> bool:
    """Determine if an entity should be migrated based on its unique ID pattern.

    Uses process of elimination to identify circuit entities that can be renamed:
    - Excludes panel-level entities (DSM state, door state, software version, power/energy, solar, etc.)
    - Excludes unmapped circuits (backing data for synthetics)
    - Allows circuit entities, switches, and selects to be migrated

    Args:
        entity: The entity registry entry
        sanitized_device_name: The sanitized device name for prefix checking

    Returns:
        True if the entity should be migrated, False otherwise

    """
    unique_id = entity.unique_id
    if not unique_id:
        return False

    # Parse unique ID to determine entity type
    # Pattern: span_{serial}_{circuit_id}_{suffix} or span_{serial}_{suffix}
    parts = unique_id.split("_", 2)  # Split into max 3 parts
    if len(parts) < 3 or parts[0] != "span":
        return False

    # Exclude unmapped circuits (they should not be migrated)
    if "unmapped_tab" in unique_id:
        return False

    # Exclude panel-level entities (they should not be migrated)
    if is_panel_level_entity(unique_id):
        return False

    # At this point, we have entities that are not panel-level or unmapped
    # These are circuit entities, switches, and selects that can be migrated
    return True


def construct_circuit_entity_id(
    hass: HomeAssistant,
    config_entry_id: str,
    platform: str,
    circuit_id: str,
    suffix: str,
    use_circuit_numbers: bool,
    use_device_prefix: bool,
    sanitized_device_name: str,
    entity: er.RegistryEntry,
) -> str:
    """Construct entity ID for circuit entities.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID
        platform: The platform name (sensor, switch, select)
        circuit_id: The circuit ID
        suffix: The entity suffix
        use_circuit_numbers: Whether to use circuit numbers
        use_device_prefix: Whether to include device prefix
        sanitized_device_name: The sanitized device name
        entity: The entity registry entry to get tabs attribute

    Returns:
        Constructed entity ID

    """
    parts = []

    if use_device_prefix:
        parts.append(sanitized_device_name)

    if use_circuit_numbers:
        # Get actual circuit numbers from coordinator data
        tabs = get_circuit_tabs_from_coordinator(hass, config_entry_id, circuit_id)
        if tabs:
            if len(tabs) == 2:
                # 240V circuit - use both tab numbers
                sorted_tabs = sorted(tabs)
                parts.append(f"circuit_{sorted_tabs[0]}_{sorted_tabs[1]}")
            elif len(tabs) == 1:
                # 120V circuit - use single tab number
                parts.append(f"circuit_{tabs[0]}")
            else:
                # Fallback to circuit_id
                parts.append(f"circuit_{circuit_id}")
        else:
            # Fallback to circuit_id
            parts.append(f"circuit_{circuit_id}")
    else:
        # Use circuit friendly name - get from entity state or coordinator
        circuit_name = get_circuit_friendly_name(hass, config_entry_id, entity, circuit_id)
        if circuit_name:
            parts.append(slugify(circuit_name))
        else:
            # Fallback to circuit_id if we can't get the friendly name
            parts.append(circuit_id)

    if suffix and not parts[-1].endswith(f"_{suffix}"):
        parts.append(suffix)

    return f"{platform}.{'_'.join(parts)}"


def construct_circuit_select_entity_id(
    hass: HomeAssistant,
    config_entry_id: str,
    platform: str,
    circuit_id: str,
    suffix: str,
    use_circuit_numbers: bool,
    use_device_prefix: bool,
    sanitized_device_name: str,
    entity: er.RegistryEntry,
) -> str:
    """Construct entity ID for circuit-related select entities.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID
        platform: The platform name
        circuit_id: The circuit ID
        suffix: The entity suffix (e.g., "circuit_priority")
        use_circuit_numbers: Whether to use circuit numbers
        use_device_prefix: Whether to include device prefix
        sanitized_device_name: The sanitized device name
        entity: The entity registry entry to get tabs attribute

    Returns:
        Constructed entity ID

    """
    parts = []

    if use_device_prefix:
        parts.append(sanitized_device_name)

    if use_circuit_numbers:
        # Get actual circuit numbers from coordinator data
        tabs = get_circuit_tabs_from_coordinator(hass, config_entry_id, circuit_id)
        if tabs:
            if len(tabs) == 2:
                # 240V circuit - use both tab numbers
                sorted_tabs = sorted(tabs)
                parts.append(f"circuit_{sorted_tabs[0]}_{sorted_tabs[1]}")
            elif len(tabs) == 1:
                # 120V circuit - use single tab number
                parts.append(f"circuit_{tabs[0]}")
            else:
                # Fallback to circuit_id
                parts.append(f"circuit_{circuit_id}")
        else:
            # Fallback to circuit_id
            parts.append(f"circuit_{circuit_id}")
    else:
        # Use circuit friendly name
        circuit_name = get_circuit_friendly_name(hass, config_entry_id, entity, circuit_id)
        if circuit_name:
            parts.append(slugify(circuit_name))
        else:
            # Fallback to circuit_id if we can't get the friendly name
            parts.append(circuit_id)

    # Add the select type (e.g., "priority")
    if suffix and not parts[-1].endswith(f"_{suffix}"):
        parts.append(suffix)

    return f"{platform}.{'_'.join(parts)}"


def construct_switch_entity_id(
    hass: HomeAssistant,
    config_entry_id: str,
    platform: str,
    circuit_id: str,
    use_circuit_numbers: bool,
    use_device_prefix: bool,
    sanitized_device_name: str,
    entity: er.RegistryEntry,
) -> str:
    """Construct entity ID for switch entities.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID
        platform: The platform name
        circuit_id: The circuit ID
        use_circuit_numbers: Whether to use circuit numbers
        use_device_prefix: Whether to include device prefix
        sanitized_device_name: The sanitized device name
        entity: The entity registry entry to get tabs attribute

    Returns:
        Constructed entity ID

    """
    parts = []

    if use_device_prefix:
        parts.append(sanitized_device_name)

    if use_circuit_numbers:
        # Get actual circuit numbers from coordinator data
        tabs = get_circuit_tabs_from_coordinator(hass, config_entry_id, circuit_id)
        if tabs:
            if len(tabs) == 2:
                # 240V circuit - use both tab numbers
                sorted_tabs = sorted(tabs)
                parts.append(f"circuit_{sorted_tabs[0]}_{sorted_tabs[1]}")
            elif len(tabs) == 1:
                # 120V circuit - use single tab number
                parts.append(f"circuit_{tabs[0]}")
            else:
                # Fallback to circuit_id
                parts.append(f"circuit_{circuit_id}")
        else:
            # Fallback to circuit_id
            parts.append(f"circuit_{circuit_id}")
    else:
        # Use circuit friendly name
        circuit_name = get_circuit_friendly_name(hass, config_entry_id, entity, circuit_id)
        if circuit_name:
            parts.append(slugify(circuit_name))
        else:
            # Fallback to circuit_id if we can't get the friendly name
            parts.append(circuit_id)

    parts.append("relay")

    return f"{platform}.{'_'.join(parts)}"


def construct_new_entity_id(
    hass: HomeAssistant,
    config_entry_id: str,
    entity: er.RegistryEntry,
    use_circuit_numbers: bool,
    use_device_prefix: bool,
    sanitized_device_name: str,
) -> str | None:
    """Construct new entity ID based on entity domain and naming flags.

    Uses the entity's domain (platform) to determine the proper construction method:
    - switch domain -> use switch construction (adds "relay" suffix)
    - select domain -> use select construction (preserves select suffix)
    - sensor domain -> use circuit construction (preserves sensor suffix)

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID
        entity: The entity registry entry
        use_circuit_numbers: Whether to use circuit numbers
        use_device_prefix: Whether to include device prefix
        sanitized_device_name: The sanitized device name

    Returns:
        New entity ID or None if construction fails

    """
    try:
        unique_id = entity.unique_id
        if not unique_id:
            return None

        # Parse unique ID to extract circuit info
        # Pattern: span_{serial}_{circuit_id}_{suffix} or span_{serial}_relay_{circuit_id}
        parts = unique_id.split("_", 2)
        if len(parts) < 3 or parts[0] != "span":
            return None

        remaining = parts[2]

        # Route based on entity domain (platform) for proper entity ID construction
        if entity.domain == "switch":
            # Switch entities: extract circuit_id from pattern like "relay_circuit_id"
            if remaining.startswith("relay_"):
                circuit_id = remaining[6:]  # Remove "relay_" prefix
            else:
                # Fallback: assume remaining is the circuit_id
                circuit_id = remaining
            return construct_switch_entity_id(
                hass,
                config_entry_id,
                entity.domain,
                circuit_id,
                use_circuit_numbers,
                use_device_prefix,
                sanitized_device_name,
                entity,
            )

        elif entity.domain == "select":
            # Select entities: pattern is span_{serial}_select_{circuit_id} or span_{serial}_{circuit_id}_{select_suffix}
            if remaining.startswith("select_"):
                # Pattern: span_{serial}_select_{circuit_id}
                circuit_id = remaining[7:]  # Remove "select_" prefix
                suffix = "priority"
                return construct_circuit_select_entity_id(
                    hass,
                    config_entry_id,
                    entity.domain,
                    circuit_id,
                    suffix,
                    use_circuit_numbers,
                    use_device_prefix,
                    sanitized_device_name,
                    entity,
                )
            elif "_" in remaining:
                # Pattern: span_{serial}_{circuit_id}_{select_suffix}
                circuit_id = remaining.split("_")[0]
                suffix = remaining.split("_", 1)[1]
                return construct_circuit_select_entity_id(
                    hass,
                    config_entry_id,
                    entity.domain,
                    circuit_id,
                    suffix,
                    use_circuit_numbers,
                    use_device_prefix,
                    sanitized_device_name,
                    entity,
                )
            else:
                # Simple select pattern - treat as circuit select
                circuit_id = remaining
                suffix = "priority"
                return construct_circuit_select_entity_id(
                    hass,
                    config_entry_id,
                    entity.domain,
                    circuit_id,
                    suffix,
                    use_circuit_numbers,
                    use_device_prefix,
                    sanitized_device_name,
                    entity,
                )

        else:
            # Sensor and other entities: pattern is span_{serial}_{circuit_id}_{suffix}
            if "_" in remaining:
                circuit_id = remaining.split("_")[0]
                suffix = remaining.split("_", 1)[1]
            else:
                # Simple pattern without suffix
                circuit_id = remaining
                suffix = ""

            return construct_circuit_entity_id(
                hass,
                config_entry_id,
                entity.domain,
                circuit_id,
                suffix,
                use_circuit_numbers,
                use_device_prefix,
                sanitized_device_name,
                entity,
            )

    except Exception as e:
        _LOGGER.error("Failed to construct new entity ID for %s: %s", entity.entity_id, e)
        return None


async def migrate_entity_ids_with_flags(
    hass: HomeAssistant,
    config_entry_id: str,
    use_circuit_numbers: bool,
    use_device_prefix: bool,
) -> bool:
    """Migrate entity IDs based on provided naming flags.

    This method migrates circuit, switch, and select entities to use the specified
    naming pattern while preserving unique IDs for statistics continuity.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID to migrate
        use_circuit_numbers: Whether to use circuit numbers in entity IDs
        use_device_prefix: Whether to include device prefix in entity IDs

    Returns:
        True if migration was successful, False otherwise

    """
    _LOGGER.info(
        "Starting entity ID migration with flags: use_circuit_numbers=%s, use_device_prefix=%s",
        use_circuit_numbers,
        use_device_prefix,
    )

    try:
        # Get entity registry
        registry = er.async_get(hass)

        # Find the active config entry ID in hass.data (might be different from stored ID due to reloads)
        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            _LOGGER.error("No %s data found in hass.data - integration not loaded", DOMAIN)
            return False

        # Verify the config entry ID exists in the loaded data
        if config_entry_id not in domain_data:
            _LOGGER.error("Config entry ID %s not found in loaded domain data", config_entry_id)
            available_entries = list(domain_data.keys())
            _LOGGER.debug("Available config entry IDs: %s", available_entries)
            return False

        active_config_entry_id = config_entry_id
        _LOGGER.debug("Using config entry ID: %s", active_config_entry_id)

        # Get device name from device registry (this is the name shown in UI)
        device_name = get_device_name_from_registry(hass, active_config_entry_id)
        if not device_name:
            _LOGGER.error(
                "Could not get device name from registry - migration aborted to prevent incorrect entity renaming"
            )
            return False

        sanitized_device_name = slugify(device_name)
        _LOGGER.info(
            "Using device name for migration: %s (sanitized: %s)",
            device_name,
            sanitized_device_name,
        )

        # Get entities for this config entry
        config_entry_entities = er.async_entries_for_config_entry(registry, active_config_entry_id)

        _LOGGER.info(
            "Found %d entities for config_entry_id: %s",
            len(config_entry_entities),
            active_config_entry_id,
        )

        # Filter entities that need migration (circuits, switches, selects)
        entities_to_migrate = []
        for entity in config_entry_entities:
            if should_migrate_entity(entity, sanitized_device_name):
                entities_to_migrate.append(entity)
                _LOGGER.debug("Found entity to migrate: %s", entity.entity_id)

        if not entities_to_migrate:
            _LOGGER.warning(
                "No entities found to migrate for config entry: %s", active_config_entry_id
            )
            return True

        _LOGGER.info("Found %d entities to migrate", len(entities_to_migrate))

        # Migrate each entity
        migrated_count = 0
        for entity in entities_to_migrate:
            new_entity_id = construct_new_entity_id(
                hass,
                config_entry_id,
                entity,
                use_circuit_numbers,
                use_device_prefix,
                sanitized_device_name,
            )

            if new_entity_id and new_entity_id != entity.entity_id:
                _LOGGER.info(
                    "Entity migration: %s -> %s",
                    entity.entity_id,
                    new_entity_id,
                )
                registry.async_update_entity(entity.entity_id, new_entity_id=new_entity_id)
                migrated_count += 1
            else:
                _LOGGER.debug("Skipping entity (no change needed): %s", entity.entity_id)

        _LOGGER.info("Migrated %d entities", migrated_count)
        return True

    except Exception as e:
        _LOGGER.error("Entity ID migration with flags failed: %s", e)
        return False
