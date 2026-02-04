"""Entity ID naming pattern migration utilities for Span Panel integration.

.. deprecated::
    This module is deprecated. Import from :mod:`custom_components.span_panel.entity_id_migration`
    instead. This module will be removed in version 2.0.

All functionality has been moved to the entity_id_migration package:
- EntityIdMigrationManager → custom_components.span_panel.entity_id_migration.manager

Usage (NEW - preferred):
    from custom_components.span_panel.entity_id_migration import EntityIdMigrationManager

Usage (OLD - deprecated):
    from custom_components.span_panel.entity_id_naming_patterns import EntityIdMigrationManager
"""

from __future__ import annotations

import warnings

warnings.warn(
    "entity_id_naming_patterns module is deprecated. "
    "Import from custom_components.span_panel.entity_id_migration instead. "
    "This module will be removed in version 2.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from .entity_id_migration import EntityIdMigrationManager  # noqa: E402

__all__ = ["EntityIdMigrationManager"]
