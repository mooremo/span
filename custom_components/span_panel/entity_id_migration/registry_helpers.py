"""Entity registry and coordinator data access utilities for migration.

This module provides utility functions for accessing Home Assistant's entity registry
and coordinator data during entity ID migrations.

Extracted from entity_id_naming_patterns.py as part of Sub-Phase 5.1.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from ..const import COORDINATOR, DOMAIN
from ..span_panel_circuit import SpanPanelCircuit

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


def get_device_name_from_registry(hass: HomeAssistant, config_entry_id: str) -> str | None:
    """Get the device name from the device registry.

    This gets the actual device name as shown in the UI, which may be different
    from the config entry data if the user has renamed the device.

    Args:
        hass: Home Assistant instance
        config_entry_id: The config entry ID to find the device for

    Returns:
        Device name from registry or None if not found

    """
    try:
        device_registry = dr.async_get(hass)

        # Get all devices for this config entry
        devices = dr.async_entries_for_config_entry(device_registry, config_entry_id)

        if not devices:
            _LOGGER.warning("No devices found for config entry: %s", config_entry_id)
            return None

        # For SPAN panels, there should typically be one main device
        # Get the first device (main panel device)
        main_device = devices[0]

        # Use name_by_user if available (user-customized name), otherwise fall back to name
        device_name = main_device.name_by_user or main_device.name

        _LOGGER.debug(
            "Retrieved device name from registry: %s (name_by_user: %s, name: %s)",
            device_name,
            main_device.name_by_user,
            main_device.name,
        )
        return device_name

    except Exception as e:
        _LOGGER.debug("Failed to get device name for config entry %s: %s", config_entry_id, str(e))
        return None


def get_circuit_name_by_id(
    hass: HomeAssistant, config_entry_id: str, circuit_id: str
) -> str | None:
    """Get circuit friendly name by circuit ID only.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID
        circuit_id: Circuit ID to look up

    Returns:
        Circuit friendly name or None if not found

    """
    try:
        coordinator_data = hass.data[DOMAIN][config_entry_id]
        coordinator = coordinator_data[COORDINATOR]
        span_panel = coordinator.data

        if circuit_id not in span_panel.circuits:
            return None

        circuit_data: SpanPanelCircuit = span_panel.circuits[circuit_id]
        return circuit_data.name
    except Exception:
        return None


def get_circuit_tabs_from_coordinator(
    hass: HomeAssistant, config_entry_id: str, circuit_id: str
) -> list[int] | None:
    """Get circuit tabs from coordinator data.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID
        circuit_id: The circuit ID

    Returns:
        List of tab numbers or None if not found

    """
    try:
        # Find the active config entry ID in hass.data (might be different from stored ID due to reloads)
        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            _LOGGER.warning(
                "No %s data found in hass.data - returning None for circuit tabs", DOMAIN
            )
            return None

        # Verify the config entry ID exists in the loaded data
        if config_entry_id not in domain_data:
            _LOGGER.warning(
                "Config entry ID %s not found in loaded domain data - returning None for circuit tabs",
                config_entry_id,
            )
            available_entries = list(domain_data.keys())
            _LOGGER.debug("Available config entry IDs: %s", available_entries)
            return None

        # Get circuit tabs from coordinator data
        coordinator_data = hass.data[DOMAIN][config_entry_id]
        coordinator = coordinator_data[COORDINATOR]
        span_panel = coordinator.data

        # Look up circuit in span_panel data
        circuit: SpanPanelCircuit | None = span_panel.circuits.get(circuit_id)
        if circuit and circuit.tabs:
            return circuit.tabs

        return None

    except Exception as e:
        _LOGGER.debug("Failed to get circuit tabs for %s: %s", circuit_id, e)
        return None


def get_circuit_friendly_name(
    hass: HomeAssistant,
    config_entry_id: str,
    entity: er.RegistryEntry,
    circuit_id: str,
) -> str | None:
    """Get the circuit friendly name from entity state or coordinator data.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID
        entity: The entity registry entry
        circuit_id: The circuit ID

    Returns:
        Circuit friendly name or None if not found

    """
    try:
        # Find the active config entry ID in hass.data (might be different from stored ID due to reloads)
        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            _LOGGER.warning(
                "No %s data found in hass.data - returning None for circuit name", DOMAIN
            )
            return None

        # Verify the config entry ID exists in the loaded data
        if config_entry_id not in domain_data:
            _LOGGER.warning(
                "Config entry ID %s not found in loaded domain data - returning None for circuit name",
                config_entry_id,
            )
            available_entries = list(domain_data.keys())
            _LOGGER.debug("Available config entry IDs: %s", available_entries)
            return None

        # Get circuit name from coordinator data
        coordinator_data = hass.data[DOMAIN][config_entry_id]
        coordinator = coordinator_data[COORDINATOR]
        span_panel = coordinator.data

        # Look up circuit in span_panel data
        circuit: SpanPanelCircuit | None = span_panel.circuits.get(circuit_id)
        if circuit and circuit.name:
            return circuit.name

        return None

    except Exception as e:
        _LOGGER.debug("Failed to get circuit friendly name for %s: %s", circuit_id, e)
        return None
