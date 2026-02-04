"""Helper utilities for SPAN Panel config flow.

Provides schema definitions, helper functions, and shared utilities
used across setup, options, and simulator flows.

Extracted from config_flow.py as part of Sub-Phase 5.2.
"""

from __future__ import annotations

import enum
from typing import Any

from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
import voluptuous as vol

from ..const import (
    CONF_API_RETRIES,
    CONF_API_RETRY_BACKOFF_MULTIPLIER,
    CONF_API_RETRY_TIMEOUT,
    CONF_USE_SSL,
    ENTITY_NAMING_PATTERN,
    EntityNamingPattern,
)
from ..options import (
    BATTERY_ENABLE,
    ENERGY_DISPLAY_PRECISION,
    ENERGY_REPORTING_GRACE_PERIOD,
    INVERTER_ENABLE,
    INVERTER_LEG1,
    INVERTER_LEG2,
    POWER_DISPLAY_PRECISION,
)
from ..span_panel_api import SpanPanelApi

# Simulation config import/export option keys
SIM_FILE_KEY = "simulation_config_file"
SIM_EXPORT_PATH = "simulation_export_path"
SIM_IMPORT_PATH = "simulation_import_path"


class TriggerFlowType(enum.Enum):
    """Types of configuration flow triggers."""

    CREATE_ENTRY = enum.auto()
    UPDATE_ENTRY = enum.auto()


def get_user_data_schema(default_host: str = "") -> vol.Schema:
    """Get the user data schema with optional default host.

    Args:
        default_host: Default value for host field

    Returns:
        Voluptuous schema for user input

    """
    return vol.Schema(
        {
            vol.Optional(CONF_HOST, default=default_host): str,
            vol.Optional(CONF_USE_SSL, default=False): bool,
            vol.Optional("simulator_mode", default=False): bool,
            vol.Optional(POWER_DISPLAY_PRECISION, default=0): int,
            vol.Optional(ENERGY_DISPLAY_PRECISION, default=2): int,
        }
    )


# Pre-built schemas for common steps
STEP_USER_DATA_SCHEMA = get_user_data_schema()

STEP_AUTH_TOKEN_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ACCESS_TOKEN): str,
    }
)

# Options flow schema
OPTIONS_SCHEMA: Any = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL): vol.All(int, vol.Range(min=5)),
        vol.Optional(BATTERY_ENABLE): bool,
        vol.Optional(INVERTER_ENABLE): bool,
        vol.Optional(INVERTER_LEG1): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional(INVERTER_LEG2): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional(ENTITY_NAMING_PATTERN): vol.In([e.value for e in EntityNamingPattern]),
        vol.Optional(CONF_API_RETRIES): vol.All(int, vol.Range(min=0, max=10)),
        vol.Optional(CONF_API_RETRY_TIMEOUT): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=10.0)
        ),
        vol.Optional(CONF_API_RETRY_BACKOFF_MULTIPLIER): vol.All(
            vol.Coerce(float), vol.Range(min=1.0, max=5.0)
        ),
        vol.Optional(ENERGY_REPORTING_GRACE_PERIOD): vol.All(int, vol.Range(min=0, max=60)),
    }
)


def create_api_controller(
    hass: HomeAssistant,
    host: str,
    access_token: str | None = None,  # nosec
) -> SpanPanelApi:
    """Create a Span Panel API controller.

    Args:
        hass: Home Assistant instance
        host: Panel host address
        access_token: Optional access token for authentication

    Returns:
        Configured SpanPanelApi instance

    """
    params: dict[str, Any] = {"host": host}
    if access_token is not None:
        params["access_token"] = access_token
    return SpanPanelApi(**params)


__all__ = [
    "SIM_FILE_KEY",
    "SIM_EXPORT_PATH",
    "SIM_IMPORT_PATH",
    "TriggerFlowType",
    "get_user_data_schema",
    "STEP_USER_DATA_SCHEMA",
    "STEP_AUTH_TOKEN_DATA_SCHEMA",
    "OPTIONS_SCHEMA",
    "create_api_controller",
]
