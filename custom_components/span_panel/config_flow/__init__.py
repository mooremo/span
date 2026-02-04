"""Config flow package for SPAN Panel integration.

This is the entry point for Home Assistant's config flow system.
Home Assistant expects to find SpanPanelConfigFlow in this module.

Package structure:
- setup_flow: Initial setup flow (SpanPanelConfigFlow)
- options_flow: Runtime options configuration (OptionsFlowHandler)
- flow_helpers: Shared schemas, constants, and utilities

Extracted from config_flow.py as part of Sub-Phase 5.2.
"""

from __future__ import annotations

from homeassistant import config_entries

from ..config_flow_utils import (
    create_config_client,
    get_available_simulation_configs,
)
from ..const import DOMAIN
from .flow_helpers import (
    OPTIONS_SCHEMA,
    SIM_EXPORT_PATH,
    SIM_FILE_KEY,
    SIM_IMPORT_PATH,
    STEP_AUTH_TOKEN_DATA_SCHEMA,
    STEP_USER_DATA_SCHEMA,
    TriggerFlowType,
    create_api_controller,
    get_user_data_schema,
)
from .options_flow import OptionsFlowHandler
from .setup_flow import SpanPanelConfigFlow

# Register the config flow handler with Home Assistant
# This is required for Home Assistant to discover the config flow
config_entries.HANDLERS.register(DOMAIN)(SpanPanelConfigFlow)

__all__ = [
    # Main flow classes
    "SpanPanelConfigFlow",
    "OptionsFlowHandler",
    # Helper exports
    "TriggerFlowType",
    "get_user_data_schema",
    "STEP_USER_DATA_SCHEMA",
    "STEP_AUTH_TOKEN_DATA_SCHEMA",
    "OPTIONS_SCHEMA",
    "create_api_controller",
    "SIM_FILE_KEY",
    "SIM_EXPORT_PATH",
    "SIM_IMPORT_PATH",
    # Re-exports from config_flow_utils
    "create_config_client",
    "get_available_simulation_configs",
]
