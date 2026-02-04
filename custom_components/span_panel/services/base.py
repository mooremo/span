"""Base service registration utilities for SPAN Panel services.

This module provides shared utilities for registering Home Assistant services
with consistent error handling, duplicate registration protection, and thread safety.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import logging
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

# Shared lock for all service registrations (prevents race conditions in multi-panel setups)
_registration_lock = asyncio.Lock()


async def register_span_service(
    hass: HomeAssistant,
    service_name: str,
    handler: Callable[[ServiceCall], Awaitable[dict[str, Any]]],
    schema: vol.Schema,
    domain: str,
    supports_response: SupportsResponse = SupportsResponse.OPTIONAL,
) -> None:
    """Register a SPAN Panel service with duplicate registration protection.

    This function provides:
    - Thread-safe registration using asyncio lock
    - Duplicate registration detection (multi-panel setups)
    - Consistent error handling and logging
    - Standardized service metadata

    Args:
        hass: Home Assistant instance
        service_name: Name of the service (e.g., "cleanup_energy_spikes")
        handler: Async function to handle service calls
        schema: Voluptuous schema for service parameters
        domain: Integration domain (usually DOMAIN constant)
        supports_response: Whether service supports responses (default: OPTIONAL)

    Raises:
        Exception: If registration fails after validation

    Example:
        ```python
        from .base import register_span_service

        async def handle_my_service(call: ServiceCall) -> dict[str, Any]:
            return {"result": "success"}

        await register_span_service(
            hass=hass,
            service_name="my_service",
            handler=handle_my_service,
            schema=MY_SERVICE_SCHEMA,
            domain=DOMAIN,
        )
        ```

    """
    service_key = f"{domain}_{service_name}_registered"

    # Use lock to prevent race condition in concurrent multi-panel setups
    async with _registration_lock:
        # Check again inside lock (double-check pattern)
        if hass.data.get(service_key):
            _LOGGER.debug(
                "Service %s.%s already registered, skipping",
                domain,
                service_name,
            )
            return

        try:
            hass.services.async_register(
                domain,
                service_name,
                handler,
                schema=schema,
                supports_response=supports_response,
            )
            # Only set flag after successful registration
            hass.data[service_key] = True
            _LOGGER.debug("Registered %s.%s service", domain, service_name)
        except Exception as e:
            _LOGGER.error(
                "Failed to register %s.%s service: %s",
                domain,
                service_name,
                e,
            )
            raise
