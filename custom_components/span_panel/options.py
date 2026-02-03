"""Configuration options for the SPAN Panel integration.

This module defines the Options class which manages user-configurable settings
for the SPAN Panel integration including solar sensors, battery monitoring,
display precision, energy reporting, API retry behavior, and simulation settings.
"""

from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_API_RETRIES,
    CONF_API_RETRY_BACKOFF_MULTIPLIER,
    CONF_API_RETRY_TIMEOUT,
    CONF_SIMULATION_START_TIME,
    DEFAULT_API_RETRIES,
    DEFAULT_API_RETRY_BACKOFF_MULTIPLIER,
    DEFAULT_API_RETRY_TIMEOUT,
    ENABLE_CIRCUIT_NET_ENERGY_SENSORS,
    ENABLE_PANEL_NET_ENERGY_SENSORS,
    ENABLE_SOLAR_NET_ENERGY_SENSORS,
)

INVERTER_ENABLE = "enable_solar_circuit"
INVERTER_LEG1 = "leg1"
INVERTER_LEG2 = "leg2"
INVERTER_MAXLEG = 32
BATTERY_ENABLE = "enable_battery_percentage"
POWER_DISPLAY_PRECISION = "power_display_precision"
ENERGY_DISPLAY_PRECISION = "energy_display_precision"
ENERGY_REPORTING_GRACE_PERIOD = "energy_reporting_grace_period"


class Options:
    """Configuration options for SPAN Panel integration.

    This class encapsulates all user-configurable settings for the integration,
    providing type-safe access to configuration options with sensible defaults.

    Attributes:
        enable_solar_sensors (bool): Enable solar production sensors.
            Default: False. When True, creates sensors for solar production on
            unmapped tabs (requires inverter_leg1 and inverter_leg2).

        inverter_leg1 (int): First leg (tab number) of solar inverter.
            Valid range: 1-32 for typical panels (up to 40 for large panels).
            Default: 0 (disabled). Must differ from inverter_leg2.

        inverter_leg2 (int): Second leg (tab number) of solar inverter.
            Valid range: 1-32 for typical panels (up to 40 for large panels).
            Default: 0 (disabled). Must differ from inverter_leg1.

        enable_battery_percentage (bool): Enable battery percentage sensor.
            Default: False. When True, creates sensor showing battery state of
            charge (requires panel with battery storage).

        power_display_precision (int): Decimal places for power sensors (Watts).
            Valid range: 0-3. Default: 0 (whole watts).
            Example: 1234.56 W with precision=2 displays as "1234.56"

        energy_display_precision (int): Decimal places for energy sensors (kWh).
            Valid range: 0-5. Default: 2.
            Example: 123.456 kWh with precision=2 displays as "123.46"

        energy_reporting_grace_period (int): Seconds to wait before reporting
            zero energy after panel comes online. Valid range: 0-300.
            Default: 15. Prevents spurious zero readings during panel startup.

        enable_panel_net_energy_sensors (bool): Enable panel net energy sensors.
            Default: True. Creates sensors showing net energy (imported - exported)
            for the entire panel.

        enable_circuit_net_energy_sensors (bool): Enable circuit net energy sensors.
            Default: True. Creates net energy sensors for individual circuits.

        enable_solar_net_energy_sensors (bool): Enable solar net energy sensors.
            Default: True. Creates net energy sensors for solar production.

        api_retries (int): Number of API request retries on failure.
            Valid range: 0-10. Default: 3.
            Set to 0 to disable retries (faster failure, less resilient).

        api_retry_timeout (float): Initial retry timeout in seconds.
            Valid range: 0.1-30.0. Default: 0.5.
            Timeout increases with backoff multiplier on subsequent retries.

        api_retry_backoff_multiplier (float): Exponential backoff multiplier.
            Valid range: 1.0-10.0. Default: 2.0.
            Each retry waits multiplier * previous_timeout.
            Example: 0.5s, 1.0s, 2.0s, 4.0s with multiplier=2.0

        simulation_start_time (datetime | None): Start time for simulation mode.
            Default: None (use current time). Only used in simulation mode.
            Format: ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SS).

    Configuration via Home Assistant UI:
        All options are configurable through the Home Assistant integration
        configuration UI under Settings → Devices & Services → SPAN Panel
        → Configure.

    Impact on Performance:
        - Solar sensors: Minimal impact (~2-3 additional entities)
        - Battery sensor: Adds one API call per update (~30-50ms)
        - Net energy sensors: Computed locally, negligible impact
        - API retries: Increases latency on failures, improves reliability
        - Display precision: No performance impact (formatting only)

    """

    # pylint: disable=R0903

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize configuration options from config entry.

        Extracts and validates all configuration options from the Home Assistant
        config entry, applying defaults where options are not set.

        Args:
            entry: Home Assistant ConfigEntry containing user configuration

        Note:
            Invalid values are coerced to defaults. For example, negative values
            are replaced with defaults, and string values are converted to
            appropriate types (int, float, bool).

        """
        self.enable_solar_sensors: bool = entry.options.get(INVERTER_ENABLE, False)
        self.inverter_leg1: int = entry.options.get(INVERTER_LEG1, 0)
        self.inverter_leg2: int = entry.options.get(INVERTER_LEG2, 0)
        self.enable_battery_percentage: bool = entry.options.get(BATTERY_ENABLE, False)
        self.power_display_precision: int = entry.options.get(POWER_DISPLAY_PRECISION, 0)
        self.energy_display_precision: int = entry.options.get(ENERGY_DISPLAY_PRECISION, 2)
        self.energy_reporting_grace_period: int = entry.options.get(
            ENERGY_REPORTING_GRACE_PERIOD, 15
        )
        self.enable_panel_net_energy_sensors: bool = entry.options.get(
            ENABLE_PANEL_NET_ENERGY_SENSORS, True
        )
        self.enable_circuit_net_energy_sensors: bool = entry.options.get(
            ENABLE_CIRCUIT_NET_ENERGY_SENSORS, True
        )
        self.enable_solar_net_energy_sensors: bool = entry.options.get(
            ENABLE_SOLAR_NET_ENERGY_SENSORS, True
        )

        # API retry configuration options
        self.api_retries: int = int(entry.options.get(CONF_API_RETRIES, DEFAULT_API_RETRIES))
        self.api_retry_timeout: float = float(
            entry.options.get(CONF_API_RETRY_TIMEOUT, str(DEFAULT_API_RETRY_TIMEOUT))
        )
        self.api_retry_backoff_multiplier: float = float(
            entry.options.get(
                CONF_API_RETRY_BACKOFF_MULTIPLIER, DEFAULT_API_RETRY_BACKOFF_MULTIPLIER
            )
        )

        # Simulation time configuration
        simulation_start_time_str = entry.options.get(CONF_SIMULATION_START_TIME)
        self.simulation_start_time: datetime | None = None
        if simulation_start_time_str:
            try:
                self.simulation_start_time = datetime.fromisoformat(simulation_start_time_str)
            except (ValueError, TypeError):
                # If parsing fails, use None (current time)
                self.simulation_start_time = None

    def get_options(self) -> dict[str, Any]:
        """Return current options as a dictionary for persistence.

        Converts the Options object back to a dictionary format suitable for
        storing in Home Assistant's config entry. Used when updating configuration
        through the UI or programmatically.

        Returns:
            dict[str, Any]: Dictionary mapping option keys to current values.
                Keys match the constants defined at module level (INVERTER_ENABLE,
                BATTERY_ENABLE, etc.). Simulation start time is converted to ISO
                format string if set.

        Example:
            options = Options(entry)
            options_dict = options.get_options()
            # {
            #     "enable_solar_circuit": True,
            #     "leg1": 5,
            #     "leg2": 6,
            #     "enable_battery_percentage": False,
            #     "power_display_precision": 0,
            #     ...
            # }

        """
        options: dict[str, Any] = {
            INVERTER_ENABLE: self.enable_solar_sensors,
            INVERTER_LEG1: self.inverter_leg1,
            INVERTER_LEG2: self.inverter_leg2,
            BATTERY_ENABLE: self.enable_battery_percentage,
            POWER_DISPLAY_PRECISION: self.power_display_precision,
            ENERGY_DISPLAY_PRECISION: self.energy_display_precision,
            ENERGY_REPORTING_GRACE_PERIOD: self.energy_reporting_grace_period,
            ENABLE_PANEL_NET_ENERGY_SENSORS: self.enable_panel_net_energy_sensors,
            ENABLE_CIRCUIT_NET_ENERGY_SENSORS: self.enable_circuit_net_energy_sensors,
            ENABLE_SOLAR_NET_ENERGY_SENSORS: self.enable_solar_net_energy_sensors,
            CONF_API_RETRIES: self.api_retries,
            CONF_API_RETRY_TIMEOUT: self.api_retry_timeout,
            CONF_API_RETRY_BACKOFF_MULTIPLIER: self.api_retry_backoff_multiplier,
        }

        # Add simulation start time if set
        if self.simulation_start_time is not None:
            options[CONF_SIMULATION_START_TIME] = self.simulation_start_time.isoformat()

        return options
