"""Entity ID migration package for Span Panel integration.

This package provides utilities for migrating entity IDs when naming
patterns change in the Span Panel integration.

Main entry point: EntityIdMigrationManager

Modules:
- manager: Main migration coordinator
- legacy_migration: Legacy naming pattern migration (pre-1.0.4)
- naming_pattern_migration: Modern naming pattern migration
- registry_helpers: Entity registry and coordinator data access utilities

Usage:
    from custom_components.span_panel.entity_id_migration import EntityIdMigrationManager

    manager = EntityIdMigrationManager(hass, config_entry_id)
    success = await manager.migrate_entity_ids(old_flags, new_flags)

Extracted from entity_id_naming_patterns.py as part of Sub-Phase 5.1.
"""

from __future__ import annotations

from .manager import EntityIdMigrationManager

__all__ = ["EntityIdMigrationManager"]
