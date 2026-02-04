"""Entity registry utilities for Span Panel integration.

Provides functions for entity registry access and persistent notifications.

Extracted from helpers.py as part of Sub-Phase 5.3.
"""

from __future__ import annotations

import logging

from homeassistant.components.persistent_notification import async_create
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_friendly_name_from_registry(
    hass: HomeAssistant, unique_id: str | None, default_name: str, platform: str = "sensor"
) -> str:
    """Check entity registry for user's customized friendly name.

    If a user has customized the friendly name of an entity in Home Assistant,
    this function will return the user's custom name instead of the default one.
    This prevents the integration from overriding user customizations.

    Args:
        hass: Home Assistant instance
        unique_id: The unique ID to look up in the registry (None to skip registry check)
        default_name: The default friendly name to use if not found in registry
        platform: Platform name ("sensor", "switch", "binary_sensor", "select")

    Returns:
        The user's custom friendly name from registry if found, otherwise the default name

    """
    # If no unique_id provided, return default name immediately
    if unique_id is None:
        return default_name

    entity_registry = er.async_get(hass)

    # First get the entity_id using the unique_id
    existing_entity_id = entity_registry.async_get_entity_id(platform, DOMAIN, unique_id)

    if existing_entity_id:
        # Now get the full entity entry using the entity_id
        entity_entry = entity_registry.entities.get(existing_entity_id)

        if entity_entry and entity_entry.name:
            _LOGGER.debug(
                "Found custom friendly name in registry: unique_id=%s -> name=%s",
                unique_id,
                entity_entry.name,
            )
            return entity_entry.name

    return default_name


async def async_create_span_notification(
    hass: HomeAssistant,
    message: str,
    title: str,
    notification_id: str,
    level: str = "warning",
) -> None:
    """Create a persistent notification for SPAN Panel issues.

    Args:
        hass: Home Assistant instance
        message: Notification message content
        title: Notification title
        notification_id: Unique identifier for the notification
        level: Severity level (info, warning, error)

    """
    _LOGGER.log(
        getattr(logging, level.upper(), logging.WARNING),
        "SPAN Panel %s: %s - %s",
        level,
        title,
        message,
    )

    async_create(
        hass,
        message=message,
        title=title,
        notification_id=notification_id,
    )


__all__ = [
    "get_friendly_name_from_registry",
    "async_create_span_notification",
]
