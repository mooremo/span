"""Initial setup flow for SPAN Panel integration.

Handles:
- User-initiated setup (manual entry)
- Zeroconf discovery
- Authentication (proximity and token)
- Initial entity naming pattern selection
- Config entry creation

Extracted from config_flow.py as part of Sub-Phase 5.2.
"""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import TYPE_CHECKING, Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowContext, ConfigFlowResult
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.selector import selector
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.util.network import is_ipv4_address
import voluptuous as vol

from ..config_flow_utils import (
    create_config_client,
    get_available_simulation_configs,
    validate_host,
    validate_simulation_time,
)
from ..config_flow_utils.authentication import (
    authenticate_via_proximity,
    authenticate_via_token,
)
from ..const import (
    CONF_SIMULATION_CONFIG,
    CONF_SIMULATION_START_TIME,
    CONF_USE_SSL,
    DOMAIN,
    ENTITY_NAMING_PATTERN,
    USE_CIRCUIT_NUMBERS,
    USE_DEVICE_PREFIX,
    EntityNamingPattern,
)
from ..exceptions import ConfigFlowError
from ..helpers import generate_unique_simulator_serial_number
from ..options import (
    ENERGY_DISPLAY_PRECISION,
    POWER_DISPLAY_PRECISION,
)
from ..span_panel_hardware_status import SpanPanelHardwareStatus
from .flow_helpers import (
    STEP_AUTH_TOKEN_DATA_SCHEMA,
    TriggerFlowType,
    get_user_data_schema,
)

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class SpanPanelConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Span Panel."""

    VERSION = 2
    MINOR_VERSION = 1
    domain = DOMAIN

    def is_matching(self, other_flow: SpanPanelConfigFlow) -> bool:
        """Return True if other_flow is a matching Span Panel."""
        return bool(other_flow and other_flow.context.get("source") == "zeroconf")

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.trigger_flow_type: TriggerFlowType | None = None
        self.host: str | None = None
        self.serial_number: str | None = None
        self.access_token: str | None = None
        self.use_ssl: bool = False
        self.power_display_precision: int = 0
        self.energy_display_precision: int = 2
        self._is_flow_setup: bool = False
        self.context: ConfigFlowContext = {}
        # Initial naming selection chosen during pre-setup
        self._chosen_use_device_prefix: bool | None = None
        self._chosen_use_circuit_numbers: bool | None = None

    async def setup_flow(
        self, trigger_type: TriggerFlowType, host: str, use_ssl: bool = False
    ) -> None:
        """Set up the flow."""
        if self._is_flow_setup is True:
            _LOGGER.error("Flow setup attempted when already set up")
            raise ConfigFlowError("Flow is already set up")

        # Use config settings for quick feedback - no retries and shorter timeout
        async with create_config_client(host, use_ssl) as client:
            status_response = await client.get_status()
            # Convert to our data class format
            status_dict = status_response.to_dict()  # type: ignore[attr-defined]
            panel_status = SpanPanelHardwareStatus.from_dict(status_dict)

        self.trigger_flow_type = trigger_type
        self.host = host
        self.serial_number = panel_status.serial_number

        # Keep the existing context values and add the host value
        self.context = {
            **self.context,
            "title_placeholders": {
                **self.context.get("title_placeholders", {}),
                CONF_HOST: self.host,
            },
        }

        self._is_flow_setup = True

    def ensure_flow_is_set_up(self) -> None:
        """Ensure the flow is set up."""
        if self._is_flow_setup is False:
            _LOGGER.error("Flow method called before setup")
            raise ConfigFlowError("Flow is not set up")

    async def ensure_not_already_configured(self) -> None:
        """Ensure the panel is not already configured."""
        self.ensure_flow_is_set_up()

        # Abort if we had already set this panel up
        await self.async_set_unique_id(self.serial_number)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self.host})

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """Handle a flow initiated by zeroconf discovery."""
        # Do not probe device if the host is already configured
        self._async_abort_entries_match({CONF_HOST: discovery_info.host})

        # Try to use IPv4 first since we cannot guarantee IPv6 is available
        host: str | None = discovery_info.host
        # Use ip_addresses_by_version if available (newer HA), fall back to host
        ip_addresses = getattr(discovery_info, "ip_addresses_by_version", None)
        if ip_addresses and 4 in ip_addresses:
            for ip in ip_addresses[4]:
                if is_ipv4_address(ip):
                    host = str(ip)
                    break

        if host is None:
            return self.async_abort(reason="no_host")

        await self.setup_flow(TriggerFlowType.CREATE_ENTRY, host)
        return await self.async_step_confirm_discovery()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        errors: dict[str, str] = {}

        # Initially ask user for host and mode
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=get_user_data_schema())

        # Check whether user requested simulator mode
        simulator_mode = user_input.get("simulator_mode", False)

        # Capture precision settings from user input
        self.power_display_precision = user_input.get(POWER_DISPLAY_PRECISION, 0)
        self.energy_display_precision = user_input.get(ENERGY_DISPLAY_PRECISION, 2)

        if simulator_mode:
            return await self._handle_simulator_setup(user_input)

        # Live panel path
        host = user_input.get(CONF_HOST, "").strip()

        if not host:
            errors[CONF_HOST] = "invalid_host"
            return self.async_show_form(
                step_id="user",
                data_schema=get_user_data_schema(host),
                errors=errors,
            )

        # Use SSL if user checked the box
        use_ssl = user_input.get(CONF_USE_SSL, False)
        self.use_ssl = use_ssl

        # Validate host connectivity
        try:
            await validate_host(host, use_ssl)
        except Exception as e:
            _LOGGER.debug("Host validation failed: %s", e)
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user",
                data_schema=get_user_data_schema(host),
                errors=errors,
            )

        await self.setup_flow(TriggerFlowType.CREATE_ENTRY, host, use_ssl)

        return await self.async_step_choose_auth_type()

    async def _handle_simulator_setup(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Handle simulator mode setup."""
        # Precision settings already stored in async_step_user

        # Check if this is the initial simulator selection or the config selection
        if CONF_SIMULATION_CONFIG not in user_input:
            # Show simulator configuration selection
            return await self.async_step_simulator_config()

        # Get the simulation config and host
        simulation_config = user_input[CONF_SIMULATION_CONFIG]
        simulation_start_time = user_input.get(CONF_SIMULATION_START_TIME, "").strip()

        # Generate unique simulator serial number first
        simulator_serial = generate_unique_simulator_serial_number(self.hass)

        # Use the generated simulator serial number as the host
        # This ensures the span panel API uses the correct serial number
        host = simulator_serial

        # Create entry for simulator mode
        base_name = "Span Simulator"
        device_name = self.get_unique_device_name(base_name)

        # Prepare config data
        config_data = {
            CONF_HOST: host,  # This is now the simulator serial number (sim-nnn)
            CONF_ACCESS_TOKEN: "simulator_token",
            CONF_USE_SSL: False,
            "simulation_mode": True,
            CONF_SIMULATION_CONFIG: simulation_config,
            "device_name": device_name,
            "simulator_serial_number": simulator_serial,
        }

        # Add simulation start time if provided
        if simulation_start_time:
            try:
                validated_time = validate_simulation_time(simulation_start_time)
                config_data[CONF_SIMULATION_START_TIME] = validated_time
            except ValueError as e:
                return self.async_show_form(
                    step_id="simulator_config",
                    data_schema=self.add_suggested_values_to_schema(
                        vol.Schema(
                            {
                                vol.Required(
                                    CONF_SIMULATION_CONFIG,
                                    default="simulation_config_32_circuit",
                                ): vol.In(get_available_simulation_configs()),
                                vol.Optional(CONF_HOST, default=""): str,
                                vol.Optional(CONF_SIMULATION_START_TIME, default=""): str,
                            }
                        ),
                        user_input,
                    ),
                    errors={"base": str(e)},
                )

        _LOGGER.debug(
            "SIMULATOR_CONFIG_DEBUG: Creating simulator entry with precision - power: %s, energy: %s",
            self.power_display_precision,
            self.energy_display_precision,
        )
        # Determine simulator naming flags based on selection (default Friendly Names)
        selected_pattern = user_input.get(
            ENTITY_NAMING_PATTERN, EntityNamingPattern.FRIENDLY_NAMES.value
        )
        sim_use_device_prefix = True
        sim_use_circuit_numbers = selected_pattern == EntityNamingPattern.CIRCUIT_NUMBERS.value

        return self.async_create_entry(
            title=device_name,
            data=config_data,
            options={
                USE_DEVICE_PREFIX: sim_use_device_prefix,
                USE_CIRCUIT_NUMBERS: sim_use_circuit_numbers,
                POWER_DISPLAY_PRECISION: self.power_display_precision,
                ENERGY_DISPLAY_PRECISION: self.energy_display_precision,
            },
        )

    async def async_step_simulator_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle simulator configuration selection."""
        if user_input is None:
            # Discover files dynamically and build dropdown options
            available_configs = get_available_simulation_configs()
            options_list = [
                {"value": key, "label": label} for key, label in available_configs.items()
            ]

            # Choose a sensible default
            default_key = (
                "simulation_config_32_circuit"
                if "simulation_config_32_circuit" in available_configs
                else next(iter(available_configs.keys()))
            )

            # Create schema with forced dropdown for simulation configuration
            schema = vol.Schema(
                {
                    vol.Required(CONF_SIMULATION_CONFIG, default=default_key): selector(
                        {
                            "select": {
                                "options": options_list,
                                "mode": "dropdown",
                            }
                        }
                    ),
                    vol.Optional(CONF_HOST, default=""): str,
                    vol.Optional(CONF_SIMULATION_START_TIME, default=""): str,
                    vol.Required(
                        ENTITY_NAMING_PATTERN,
                        default=EntityNamingPattern.FRIENDLY_NAMES.value,
                    ): vol.In(
                        {
                            EntityNamingPattern.FRIENDLY_NAMES.value: "Circuit Friendly Names",
                            EntityNamingPattern.CIRCUIT_NUMBERS.value: "Tab Based Names",
                        }
                    ),
                }
            )

            return self.async_show_form(
                step_id="simulator_config",
                data_schema=schema,
                description_placeholders={
                    "config_count": str(len(available_configs)),
                },
            )

        # Continue with simulator setup using the selected config
        # Ensure simulator_mode is set since it's not in the form data
        user_input_with_sim_mode = dict(user_input)
        user_input_with_sim_mode["simulator_mode"] = True
        return await self._handle_simulator_setup(user_input_with_sim_mode)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Handle a flow initiated by re-auth."""
        use_ssl = entry_data.get(CONF_USE_SSL, False)
        self.use_ssl = use_ssl
        await self.setup_flow(TriggerFlowType.UPDATE_ENTRY, entry_data[CONF_HOST], use_ssl)
        return await self.async_step_auth_token(dict(entry_data))

    async def async_step_confirm_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt user to confirm a discovered Span Panel."""
        self.ensure_flow_is_set_up()

        # Prompt the user for confirmation
        if user_input is None:
            self._set_confirm_only()
            host = self.host if self.host is not None else ""
            return self.async_show_form(
                step_id="confirm_discovery",
                description_placeholders={
                    "host": host,
                },
            )

        # Transition to choose auth type
        return await self.async_step_choose_auth_type()

    async def async_step_choose_auth_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask user to choose between proximity auth and token entry."""
        self.ensure_flow_is_set_up()

        if user_input is None:
            return self.async_show_menu(
                step_id="choose_auth_type",
                menu_options={
                    "auth_proximity": "Authenticate via Proximity (press button on panel)",
                    "auth_token": "Authenticate via Access Token",
                },
            )
        return self.async_abort(reason="unknown")

    async def async_step_auth_proximity(
        self, entry_data: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step that guides users through proximity authentication."""
        self.ensure_flow_is_set_up()

        if self.host is None:
            return self.async_abort(reason="host_not_set")

        # Create client and authenticate via proximity
        async with create_config_client(self.host, self.use_ssl) as client:
            result = await authenticate_via_proximity(self.hass, client, self.host, self.use_ssl)

        if result.success:
            # Store the access token
            self.access_token = result.access_token
            return await self.async_step_resolve_entity(entry_data)

        if result.requires_retry:
            # Show the form again to let user retry
            return self.async_show_form(
                step_id="auth_proximity",
                errors={"base": result.error_reason or "auth_general_error"},
            )

        # Non-retriable error - abort
        return self.async_abort(reason=result.error_reason or "auth_general_error")

    async def async_step_auth_token(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step that prompts user for an access token."""
        self.ensure_flow_is_set_up()
        errors: dict[str, str] = {}

        if user_input is not None:
            result = await authenticate_via_token(
                self.hass,
                self.host or "",
                user_input.get(CONF_ACCESS_TOKEN, ""),
                self.use_ssl,
            )

            if result.success:
                self.access_token = result.access_token
                return await self.async_step_resolve_entity(user_input)

            errors["base"] = result.error_reason or "invalid_auth"

        return self.async_show_form(
            step_id="auth_token",
            data_schema=STEP_AUTH_TOKEN_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_resolve_entity(
        self, entry_data: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """After auth, continue with the entity resolution/entry creation flow."""
        self.ensure_flow_is_set_up()

        await self.ensure_not_already_configured()

        if self.trigger_flow_type == TriggerFlowType.CREATE_ENTRY:
            # New entry flow - show naming pattern selection
            return await self.async_step_choose_entity_naming_initial()

        if self.trigger_flow_type == TriggerFlowType.UPDATE_ENTRY:
            # Handle reauth
            existing_entry = await self.async_set_unique_id(self.serial_number)
            if existing_entry is None:
                return self.async_abort(reason="reauth_failed_existing")
            # Create a new entry for reauth
            return self.async_update_reload_and_abort(
                existing_entry,
                data={
                    CONF_HOST: self.host,
                    CONF_ACCESS_TOKEN: self.access_token,
                    CONF_USE_SSL: self.use_ssl,
                },
            )

        return self.async_abort(reason="unknown")

    def create_new_entry(
        self, host: str, serial_number: str, access_token: str
    ) -> ConfigFlowResult:
        """Create a new config entry for a Span Panel.

        Uses the naming pattern selection from choose_entity_naming_initial step.
        """
        device_name = serial_number

        # Use the naming flags selected during choose_entity_naming_initial
        use_device_prefix = (
            self._chosen_use_device_prefix if self._chosen_use_device_prefix is not None else True
        )
        use_circuit_numbers = (
            self._chosen_use_circuit_numbers
            if self._chosen_use_circuit_numbers is not None
            else False
        )

        return self.async_create_entry(
            title=device_name,
            data={
                CONF_HOST: host,
                CONF_ACCESS_TOKEN: access_token,
                CONF_USE_SSL: self.use_ssl,
                "device_name": device_name,
            },
            options={
                USE_DEVICE_PREFIX: use_device_prefix,
                USE_CIRCUIT_NUMBERS: use_circuit_numbers,
                POWER_DISPLAY_PRECISION: self.power_display_precision,
                ENERGY_DISPLAY_PRECISION: self.energy_display_precision,
            },
        )

    def get_unique_device_name(self, base_name: str) -> str:
        """Generate a unique device name by checking existing entries."""
        existing_entries = self.hass.config_entries.async_entries(DOMAIN)
        existing_names = {entry.title for entry in existing_entries}

        if base_name not in existing_names:
            return base_name

        i = 2
        while f"{base_name} {i}" in existing_names:
            i += 1
        return f"{base_name} {i}"

    async def async_step_choose_entity_naming_initial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pre-setup choice of Entity ID naming pattern.

        Default to Friendly Names; both choices imply device prefix enabled.
        """
        self.ensure_flow_is_set_up()

        pattern_options = {
            EntityNamingPattern.FRIENDLY_NAMES.value: "Circuit Friendly Names",
            EntityNamingPattern.CIRCUIT_NUMBERS.value: "Tab Based Names",
        }

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(
                        ENTITY_NAMING_PATTERN,
                        default=EntityNamingPattern.FRIENDLY_NAMES.value,
                    ): vol.In(pattern_options)
                }
            )
            return self.async_show_form(
                step_id="choose_entity_naming_initial",
                data_schema=schema,
            )

        selected = user_input.get(ENTITY_NAMING_PATTERN, EntityNamingPattern.FRIENDLY_NAMES.value)
        self._chosen_use_device_prefix = True
        self._chosen_use_circuit_numbers = selected == EntityNamingPattern.CIRCUIT_NUMBERS.value

        # Proceed to create the entry
        if self.host is None or self.serial_number is None or self.access_token is None:
            raise ConfigFlowError("Missing required parameters during entry creation")
        return self.create_new_entry(self.host, self.serial_number, self.access_token)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        # Import here to avoid circular imports
        from .options_flow import OptionsFlowHandler  # pylint: disable=import-outside-toplevel

        return OptionsFlowHandler()
