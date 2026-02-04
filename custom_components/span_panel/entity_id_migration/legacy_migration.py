"""Legacy entity ID migration for Span Panel integration.

Handles migration from pre-1.0.4 naming (no device prefix) to modern naming
with device prefix. This migration includes ALL sensors (panel and circuit).

Extracted from entity_id_naming_patterns.py as part of Sub-Phase 5.1.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from ..const import DOMAIN
from .registry_helpers import get_device_name_from_registry

_LOGGER = logging.getLogger(__name__)


async def migrate_legacy_to_prefix(
    hass: HomeAssistant,
    config_entry_id: str,
    old_flags: dict[str, bool],
    new_flags: dict[str, bool],
) -> bool:
    """Migrate from legacy naming (no device prefix) to device prefix + friendly names.

    This migration includes ALL sensors (panel-level and circuit-level) since legacy
    installations need comprehensive migration to the new naming structure.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID to migrate
        old_flags: {USE_CIRCUIT_NUMBERS: False, USE_DEVICE_PREFIX: False}
        new_flags: {USE_CIRCUIT_NUMBERS: False, USE_DEVICE_PREFIX: True}

    Returns:
        True if migration was successful, False otherwise

    """
    _LOGGER.info("Performing legacy to device prefix migration")

    try:
        _LOGGER.info("Starting legacy migration for config entry: %s", config_entry_id)

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

        # Use the active config entry ID we found
        effective_config_entry_id = active_config_entry_id

        # Get entities for this config entry using HA helper
        _LOGGER.debug(
            "Attempting to get entities for config_entry_id: %s", effective_config_entry_id
        )

        # Check if config entry exists first
        config_entry = hass.config_entries.async_get_entry(effective_config_entry_id)
        if config_entry is None:
            _LOGGER.error(
                "Config entry %s not found in config entries registry - migration aborted",
                effective_config_entry_id,
            )
            available_entries = [entry.entry_id for entry in hass.config_entries.async_entries()]
            _LOGGER.debug("Available config entry IDs: %s", available_entries)
            return False

        try:
            config_entry_entities = er.async_entries_for_config_entry(
                registry, effective_config_entry_id
            )
        except KeyError:
            _LOGGER.error(
                "Config entry ID %s not found in entity registry - migration aborted",
                effective_config_entry_id,
            )
            return False

        _LOGGER.info(
            "Found %d entities for config_entry_id: %s",
            len(config_entry_entities),
            effective_config_entry_id,
        )

        # Filter entities that need renaming (don't already have device prefix)
        entities_to_migrate = []
        for entity in config_entry_entities:
            object_id = entity.entity_id.split(".", 1)[1]
            _LOGGER.debug(
                "Checking entity %s: object_id='%s', prefix='%s_', starts_with=%s",
                entity.entity_id,
                object_id,
                sanitized_device_name,
                object_id.startswith(f"{sanitized_device_name}_"),
            )
            if not object_id.startswith(f"{sanitized_device_name}_"):
                entities_to_migrate.append(entity)
                _LOGGER.debug("Found entity to migrate: %s", entity.entity_id)
            else:
                _LOGGER.debug("Skipping entity (already has prefix): %s", entity.entity_id)

        if not entities_to_migrate:
            _LOGGER.warning(
                "No entities found to migrate for config entry: %s", active_config_entry_id
            )
            return True

        _LOGGER.info("Found %d entities to migrate", len(entities_to_migrate))

        # Remove duplicates from the migration list
        seen_entity_ids: set[str] = set()
        unique_entities_to_migrate = []
        for entity in entities_to_migrate:
            if entity.entity_id not in seen_entity_ids:
                seen_entity_ids.add(entity.entity_id)
                unique_entities_to_migrate.append(entity)
            else:
                _LOGGER.debug("Removing duplicate entity: %s", entity.entity_id)

        entities_to_migrate = unique_entities_to_migrate
        _LOGGER.info("After deduplication: %d unique entities to migrate", len(entities_to_migrate))

        # Migrate each entity (remove from list after processing to avoid duplicates)
        migrated_count = 0

        while entities_to_migrate:
            entity = entities_to_migrate.pop(0)  # Take first entity and remove it from list
            current_entity_id = entity.entity_id
            platform, object_id = current_entity_id.split(".", 1)

            # Safety check: skip if entity already has the device prefix
            if object_id.startswith(f"{sanitized_device_name}_"):
                _LOGGER.debug("Skipping entity (already has prefix): %s", current_entity_id)
                continue

            # Generate new entity ID with device prefix
            new_object_id = f"{sanitized_device_name}_{object_id}"
            new_entity_id = f"{platform}.{new_object_id}"

            _LOGGER.info(
                "Entity migration: %s -> %s",
                current_entity_id,
                new_entity_id,
            )

            # Update the entity registry (statistics should be transferred automatically in HA 2023.4+)
            registry.async_update_entity(current_entity_id, new_entity_id=new_entity_id)
            migrated_count += 1

        _LOGGER.info("Migrated %d entities", migrated_count)

        # Migration completed - reload will be handled by integration startup

        return True

    except Exception as e:
        _LOGGER.error("Legacy migration failed: %s", e)
        return False
