"""Migration manager coordinator for Span Panel integration.

This is the main entry point for entity ID migrations, orchestrating
different migration strategies based on configuration changes.

Extracted from entity_id_naming_patterns.py as part of Sub-Phase 5.1.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..const import USE_CIRCUIT_NUMBERS, USE_DEVICE_PREFIX
from .legacy_migration import migrate_legacy_to_prefix
from .naming_pattern_migration import migrate_entity_ids_with_flags

_LOGGER = logging.getLogger(__name__)


class EntityIdMigrationManager:
    """Manages entity ID migrations when naming patterns change.

    This is the main coordinator class that determines which migration
    strategy to use based on configuration flag changes.
    """

    def __init__(self, hass: HomeAssistant, config_entry_id: str) -> None:
        """Initialize the migration manager.

        Args:
            hass: Home Assistant instance
            config_entry_id: Config entry ID to manage migrations for

        """
        self.hass = hass
        self.config_entry_id = config_entry_id

    async def migrate_entity_ids(
        self, old_flags: dict[str, bool], new_flags: dict[str, bool]
    ) -> bool:
        """Migrate entity IDs when naming patterns change.

        Args:
            old_flags: Previous configuration flags
                {USE_CIRCUIT_NUMBERS: bool, USE_DEVICE_PREFIX: bool}
            new_flags: New configuration flags
                {USE_CIRCUIT_NUMBERS: bool, USE_DEVICE_PREFIX: bool}

        Handles multiple types of migrations:
        1. Legacy migration (no device prefix -> device prefix)
        2. Naming pattern changes (friendly names <-> circuit numbers)
        3. Combined migrations (legacy + naming pattern changes)

        Returns:
            True if migration was successful, False otherwise

        """
        _LOGGER.info(
            "Starting entity ID migration: old_flags=%s, new_flags=%s",
            old_flags,
            new_flags,
        )

        # Determine what type of migration is needed
        old_use_device_prefix = old_flags.get(USE_DEVICE_PREFIX, False)
        new_use_device_prefix = new_flags.get(USE_DEVICE_PREFIX, False)
        old_use_circuit_numbers = old_flags.get(USE_CIRCUIT_NUMBERS, False)
        new_use_circuit_numbers = new_flags.get(USE_CIRCUIT_NUMBERS, False)

        # Check if legacy migration is needed (no device prefix -> device prefix)
        needs_legacy_migration = not old_use_device_prefix and new_use_device_prefix

        # Check if naming pattern migration is needed (circuit numbers change)
        needs_naming_migration = old_use_circuit_numbers != new_use_circuit_numbers

        if needs_legacy_migration and needs_naming_migration:
            # Combined migration: legacy + naming pattern change
            _LOGGER.info("Performing combined migration: legacy + naming pattern change")
            legacy_success = await migrate_legacy_to_prefix(
                self.hass, self.config_entry_id, old_flags, new_flags
            )
            if legacy_success:
                # After legacy migration, do naming pattern migration
                return await migrate_entity_ids_with_flags(
                    self.hass,
                    self.config_entry_id,
                    new_use_circuit_numbers,
                    new_use_device_prefix,
                )
            return False
        elif needs_legacy_migration:
            # Legacy migration only
            _LOGGER.info("Performing legacy migration: no device prefix -> device prefix")
            return await migrate_legacy_to_prefix(
                self.hass, self.config_entry_id, old_flags, new_flags
            )
        elif needs_naming_migration:
            # Naming pattern migration only
            _LOGGER.info(
                "Performing naming pattern migration: circuit numbers %s -> %s",
                old_use_circuit_numbers,
                new_use_circuit_numbers,
            )
            return await migrate_entity_ids_with_flags(
                self.hass,
                self.config_entry_id,
                new_use_circuit_numbers,
                new_use_device_prefix,
            )
        else:
            # No migration needed
            _LOGGER.info("No migration needed - flags unchanged")
            return True
