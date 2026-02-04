"""Options flow for SPAN Panel integration.

Handles runtime configuration changes:
- General options (scan interval, battery, solar)
- Entity naming pattern changes
- Migration triggering
- Simulation configuration

Extracted from config_flow.py as part of Sub-Phase 5.2.
"""

from __future__ import annotations

import logging
from pathlib import Path
import shutil
from time import time
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import selector
from homeassistant.util import slugify
from span_panel_api.simulation import DynamicSimulationEngine, SimulationConfig
import voluptuous as vol
import yaml

from ..config_flow_utils import (
    build_general_options_schema,
    get_available_simulation_configs,
    get_available_unmapped_tabs,
    get_current_naming_pattern,
    get_general_options_defaults,
    pattern_to_flags,
    process_general_options_input,
    validate_simulation_time,
)
from ..config_flow_utils.options import (
    build_entity_naming_options_schema,
    get_entity_naming_options_defaults,
    process_entity_naming_options_input,
)
from ..const import (
    CONF_SIMULATION_CONFIG,
    CONF_SIMULATION_OFFLINE_MINUTES,
    CONF_SIMULATION_START_TIME,
    COORDINATOR,
    DOMAIN,
    ENTITY_NAMING_PATTERN,
    USE_CIRCUIT_NUMBERS,
    USE_DEVICE_PREFIX,
    EntityNamingPattern,
)
from ..options import (
    INVERTER_ENABLE,
    INVERTER_LEG1,
    INVERTER_LEG2,
)
from ..simulation_utils import clone_panel_to_simulation
from .flow_helpers import (
    SIM_EXPORT_PATH,
    SIM_FILE_KEY,
    SIM_IMPORT_PATH,
)

_LOGGER = logging.getLogger(__name__)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the options flow for Span Panel."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the main options menu."""
        if user_input is None:
            menu_options = {
                "general_options": "General Options",
            }

            # Add entity naming options only for live panels (not simulations)
            if not self.config_entry.data.get("simulation_mode", False):
                menu_options["entity_naming_options"] = "Entity Naming Options"

            # Add simulation options if this is a simulation mode integration
            if self.config_entry.data.get("simulation_mode", False):
                menu_options["simulation_start_time"] = "Simulation Start Time"
                menu_options["simulation_offline_minutes"] = "Simulation Offline Minutes"
            else:
                # Live panel: offer cloning into a simulation config
                menu_options["clone_panel_to_simulation"] = "Clone Panel To Simulation"

            return self.async_show_menu(
                step_id="init",
                menu_options=menu_options,
            )

            # This shouldn't be reached since we're showing a menu
        return self.async_abort(reason="unknown")

    async def async_step_general_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the general options (excluding entity naming)."""
        # Get available unmapped tabs for dropdown
        available_tabs = await get_available_unmapped_tabs(self.hass, self.config_entry)

        if user_input is not None:
            # Process the user input using the utility function
            filtered_input, errors = process_general_options_input(
                self.config_entry, user_input, available_tabs
            )

            # If no errors, proceed with saving options
            if not errors:
                return self.async_create_entry(title="", data=filtered_input)
        else:
            errors = {}

        # Get current values for dynamic filtering
        try:
            current_leg1 = int(self.config_entry.options.get(INVERTER_LEG1, 0))
        except (TypeError, ValueError):
            current_leg1 = 0
        try:
            current_leg2 = int(self.config_entry.options.get(INVERTER_LEG2, 0))
        except (TypeError, ValueError):
            current_leg2 = 0

        # Build the schema using utility function
        schema = build_general_options_schema(
            self.config_entry, available_tabs, current_leg1, current_leg2
        )

        defaults = get_general_options_defaults(self.config_entry, current_leg1, current_leg2)

        return self.async_show_form(
            step_id="general_options",
            data_schema=self.add_suggested_values_to_schema(schema, defaults),
            errors=errors,
        )

    async def async_step_entity_naming_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage entity naming options including legacy upgrade and naming patterns."""
        if user_input is not None:
            # Process the user input for entity naming options
            filtered_input, errors = process_entity_naming_options_input(
                self.config_entry, user_input
            )

            # If no errors, proceed with saving options
            if not errors:
                # Check if there are pending migrations that need to be handled by coordinator
                if filtered_input.get("pending_legacy_migration", False) or filtered_input.get(
                    "pending_naming_migration", False
                ):
                    # Merge with existing options to preserve all settings
                    merged_options = dict(self.config_entry.options)
                    merged_options.update(filtered_input)

                    # Log the migration flags for debugging
                    _LOGGER.info(
                        "Setting migration flags: pending_naming_migration=%s, old_flags=(%s,%s), new_flags=(%s,%s)",
                        merged_options.get("pending_naming_migration", False),
                        merged_options.get("old_use_circuit_numbers", "None"),
                        merged_options.get("old_use_device_prefix", "None"),
                        merged_options.get(USE_CIRCUIT_NUMBERS, "None"),
                        merged_options.get(USE_DEVICE_PREFIX, "None"),
                    )

                    # Return the merged options to trigger reload with migration flags
                    return self.async_create_entry(title="", data=merged_options)
                else:
                    # No pending migrations, proceed with normal reload
                    # Merge with existing options to preserve all settings
                    merged_options = dict(self.config_entry.options)
                    merged_options.update(filtered_input)
                    return self.async_create_entry(title="", data=merged_options)
        else:
            errors = {}

        # Build the entity naming options schema
        schema = build_entity_naming_options_schema(self.config_entry)
        defaults = get_entity_naming_options_defaults(self.config_entry)

        return self.async_show_form(
            step_id="entity_naming_options",
            data_schema=self.add_suggested_values_to_schema(schema, defaults),
            errors=errors,
        )

    async def async_step_entity_naming(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage entity naming pattern options."""
        if user_input is not None:
            # Check if entity naming pattern changed
            current_pattern = self._get_current_naming_pattern()
            new_pattern = user_input.get(ENTITY_NAMING_PATTERN, current_pattern)

            # For legacy installations, treat the selection as a change even
            # if it matches the default since we default to Friendly Names
            # for display but the actual pattern is Legacy
            pattern_changed = False
            if current_pattern == EntityNamingPattern.LEGACY_NAMES.value:
                # Pre-1.0.4 installation - any selection is a migration
                # But only if they actually selected something (not just submitted
                # with defaults)
                if ENTITY_NAMING_PATTERN in user_input:
                    pattern_changed = True
            else:
                # Modern installation - only migrate if pattern actually changed
                pattern_changed = new_pattern != current_pattern

            if pattern_changed:
                # Entity naming pattern changed - update the configuration flags
                naming_options = {}
                if new_pattern == EntityNamingPattern.CIRCUIT_NUMBERS.value:
                    naming_options[USE_CIRCUIT_NUMBERS] = True
                    naming_options[USE_DEVICE_PREFIX] = True
                elif new_pattern == EntityNamingPattern.FRIENDLY_NAMES.value:
                    naming_options[USE_CIRCUIT_NUMBERS] = False
                    naming_options[USE_DEVICE_PREFIX] = True

                _LOGGER.info(
                    "Pattern change: %s -> %s, setting flags: USE_CIRCUIT_NUMBERS=%s, USE_DEVICE_PREFIX=%s",
                    current_pattern,
                    new_pattern,
                    naming_options.get(USE_CIRCUIT_NUMBERS),
                    naming_options.get(USE_DEVICE_PREFIX),
                )

                # Entity ID migration will be handled after reload via pending_legacy_migration flag

                # Update only the naming-related options, preserve ALL other options
                current_options = dict(self.config_entry.options)

                # Only update the specific naming flags, preserve everything else
                current_options[USE_CIRCUIT_NUMBERS] = naming_options[USE_CIRCUIT_NUMBERS]
                current_options[USE_DEVICE_PREFIX] = naming_options[USE_DEVICE_PREFIX]

                # Debug: Log what options we're preserving
                preserved_options = {
                    k: v
                    for k, v in current_options.items()
                    if k not in [USE_CIRCUIT_NUMBERS, USE_DEVICE_PREFIX]
                }
                _LOGGER.debug("Preserving existing options: %s", preserved_options)
                _LOGGER.debug(
                    "Solar sensor enabled: %s",
                    current_options.get(INVERTER_ENABLE, False),
                )
                _LOGGER.debug("Inverter leg 1: %s", current_options.get(INVERTER_LEG1, 0))
                _LOGGER.debug("Inverter leg 2: %s", current_options.get(INVERTER_LEG2, 0))
                _LOGGER.debug("All options after update: %s", current_options)

                # Schedule reload after the options flow completes
                async def reload_after_options_complete() -> None:
                    # Wait for the options flow to complete first
                    await self.hass.async_block_till_done()
                    _LOGGER.info("Reloading integration after entity naming pattern change")
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                self.hass.async_create_task(reload_after_options_complete())

                # Return success with the updated options - this will update the config entry
                _LOGGER.debug("Returning updated options to complete the flow")
                return self.async_create_entry(title="", data=current_options)
            else:
                # No pattern change - just return success
                return self.async_create_entry(title="", data={})

        # Show entity naming form
        current_pattern = self._get_current_naming_pattern()

        # For legacy installations, default to Friendly Names but allow user to choose
        # For modern installations, show the current pattern
        if current_pattern == EntityNamingPattern.LEGACY_NAMES.value:
            display_pattern = EntityNamingPattern.FRIENDLY_NAMES.value
        else:
            display_pattern = current_pattern

        defaults: dict[str, Any] = {
            ENTITY_NAMING_PATTERN: display_pattern,
        }

        # Provide placeholders for the translation system
        description_placeholders = {
            "friendly_example": "**Friendly Names Example**: span_panel_kitchen_outlets_power",
            "circuit_example": "**Circuit Numbers Example**: span_panel_circuit_15_power",
        }

        _LOGGER.debug("Entity naming step - current pattern: %s", current_pattern)
        _LOGGER.debug(
            "Entity naming step - description placeholders: %s",
            description_placeholders,
        )

        return self.async_show_form(
            step_id="entity_naming",
            data_schema=self.add_suggested_values_to_schema(
                self._get_entity_naming_schema(), defaults
            ),
            description_placeholders=description_placeholders,
        )

    async def async_step_simulation_start_time(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit simulation start time settings."""
        if user_input is not None:
            simulation_start_time = user_input.get(CONF_SIMULATION_START_TIME, "").strip()

            _LOGGER.info("Edit simulation start time - start_time: %s", simulation_start_time)

            if simulation_start_time:
                try:
                    simulation_start_time = validate_simulation_time(simulation_start_time)
                    user_input[CONF_SIMULATION_START_TIME] = simulation_start_time
                except ValueError as e:
                    return self.async_show_form(
                        step_id="simulation_start_time",
                        data_schema=self.add_suggested_values_to_schema(
                            self._get_simulation_start_time_schema(),
                            self._get_simulation_start_time_defaults(),
                        ),
                        errors={"base": str(e)},
                    )

            # Merge with existing options to preserve other settings
            merged_options = dict(self.config_entry.options)
            merged_options.update(user_input)

            # Clean up any simulation-only change flag since this will trigger a reload
            merged_options.pop("_simulation_only_change", None)

            _LOGGER.info("Saving simulation start time: %s", user_input)
            _LOGGER.info("Merged options: %s", merged_options)

            return self.async_create_entry(title="", data=merged_options)

        return self.async_show_form(
            step_id="simulation_start_time",
            data_schema=self.add_suggested_values_to_schema(
                self._get_simulation_start_time_schema(),
                self._get_simulation_start_time_defaults(),
            ),
        )

    async def async_step_simulation_offline_minutes(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit simulation offline minutes settings."""
        if user_input is not None:
            offline_minutes = user_input.get(CONF_SIMULATION_OFFLINE_MINUTES, 0)

            _LOGGER.info("Edit simulation offline minutes - offline_minutes: %s", offline_minutes)

            # Merge with existing options to preserve other settings
            merged_options = dict(self.config_entry.options)
            merged_options.update(user_input)

            # Add a flag to indicate this is a simulation-only change
            merged_options["_simulation_only_change"] = True

            # Add a timestamp to force change detection even when offline_minutes value is the same
            # This ensures the update listener is called to restart the offline timer
            merged_options["_simulation_timestamp"] = int(time())

            return self.async_create_entry(title="", data=merged_options)

        return self.async_show_form(
            step_id="simulation_offline_minutes",
            data_schema=self.add_suggested_values_to_schema(
                self._get_simulation_offline_minutes_schema(),
                self._get_simulation_offline_minutes_defaults(),
            ),
        )

    async def async_step_simulation_export(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle simulation config export."""
        errors: dict[str, str] = {}

        if user_input is not None:
            config_key = user_input.get(SIM_FILE_KEY, "")
            export_path_raw = str(user_input.get(SIM_EXPORT_PATH, "")).strip()

            if not config_key:
                errors[SIM_FILE_KEY] = "Please select a simulation config to export"
            elif not export_path_raw:
                errors[SIM_EXPORT_PATH] = "Export path is required"
            else:
                try:
                    current_file = Path(__file__)
                    config_dir = current_file.parent.parent / "simulation_configs"
                    src_yaml = config_dir / f"{config_key}.yaml"

                    export_path = Path(export_path_raw)
                    await self.hass.async_add_executor_job(
                        lambda: export_path.parent.mkdir(parents=True, exist_ok=True)
                    )
                    if not await self.hass.async_add_executor_job(src_yaml.exists):
                        raise FileNotFoundError(f"Source simulation file not found: {src_yaml}")
                    await self.hass.async_add_executor_job(shutil.copyfile, src_yaml, export_path)
                    _LOGGER.info("Exported simulation config '%s' to %s", config_key, export_path)

                    # Build friendly name for confirmation
                    friendly = get_available_simulation_configs().get(config_key, config_key)
                    return self.async_create_entry(
                        title="",
                        data={},
                        description=f"Exported '{friendly}' to {export_path}",
                    )

                except Exception as e:
                    _LOGGER.error("Simulation config export error: %s", e)
                    errors["base"] = f"Export failed: {e}"

        # Show export form
        available_configs = get_available_simulation_configs()
        options_list = [{"value": k, "label": v} for k, v in available_configs.items()]
        current_config_key = self.config_entry.data.get(
            CONF_SIMULATION_CONFIG, "simulation_config_32_circuit"
        )
        default_export = f"/tmp/{current_config_key}.yaml"  # nosec

        export_schema = vol.Schema(
            {
                vol.Required(SIM_FILE_KEY, default=current_config_key): selector(
                    {
                        "select": {
                            "options": options_list,
                            "mode": "dropdown",
                        }
                    }
                ),
                vol.Required(SIM_EXPORT_PATH, default=default_export): str,
            }
        )

        return self.async_show_form(
            step_id="simulation_export",
            data_schema=export_schema,
            errors=errors,
        )

    async def async_step_simulation_import(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle simulation config import."""
        errors: dict[str, str] = {}

        if user_input is not None:
            import_path_raw = str(user_input.get(SIM_IMPORT_PATH, "")).strip()

            if not import_path_raw:
                errors[SIM_IMPORT_PATH] = "Import path is required"
            else:
                try:
                    import_path = Path(import_path_raw)
                    if not await self.hass.async_add_executor_job(import_path.exists):
                        raise FileNotFoundError(f"Import file not found: {import_path}")

                    # Load and validate YAML using span-panel-api's validator
                    def load_yaml_file() -> dict[str, Any]:
                        with import_path.open("r", encoding="utf-8") as f:
                            result = yaml.safe_load(f)
                            if result is None:
                                return {}
                            if isinstance(result, dict):
                                return result
                            return {}

                    loaded_yaml = await self.hass.async_add_executor_job(load_yaml_file)
                    # Use DynamicSimulationEngine internal validation
                    config = SimulationConfig(**loaded_yaml)
                    engine = DynamicSimulationEngine(config_data=config)
                    await engine.initialize_async()

                    # Copy to simulation_configs directory
                    current_file = Path(__file__)
                    config_dir = current_file.parent.parent / "simulation_configs"
                    dest_name = (
                        import_path.name if import_path.suffix else f"{import_path.name}.yaml"
                    )
                    dest_yaml = config_dir / dest_name
                    await self.hass.async_add_executor_job(
                        lambda: dest_yaml.parent.mkdir(parents=True, exist_ok=True)
                    )
                    await self.hass.async_add_executor_job(shutil.copyfile, import_path, dest_yaml)
                    _LOGGER.info("Imported and validated simulation config to %s", dest_yaml)

                    # Update config entry to point to the imported simulation config
                    try:
                        new_data = dict(self.config_entry.data)
                        new_data[CONF_SIMULATION_CONFIG] = dest_yaml.stem
                        self.hass.config_entries.async_update_entry(
                            self.config_entry, data=new_data
                        )
                        _LOGGER.debug("Set CONF_SIMULATION_CONFIG to %s", dest_yaml.stem)
                    except Exception as update_err:
                        _LOGGER.warning(
                            "Failed to set CONF_SIMULATION_CONFIG to %s: %s",
                            dest_yaml.stem,
                            update_err,
                        )

                    return self.async_create_entry(
                        title="",
                        data={},
                        description=f"Imported '{dest_yaml.stem}' into simulation configurations",
                    )

                except Exception as e:
                    _LOGGER.error("Simulation config import error: %s", e)
                    errors["base"] = f"Import failed: {e}"

        # Show import form
        import_schema = vol.Schema(
            {
                vol.Required(SIM_IMPORT_PATH, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="simulation_import",
            data_schema=import_schema,
            errors=errors,
        )

    async def async_step_clone_panel_to_simulation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Clone the live panel into a simulation YAML stored in simulation_configs."""
        result = await clone_panel_to_simulation(self.hass, self.config_entry, user_input)

        # If result is a ConfigFlowResult, return it directly
        if hasattr(result, "type"):
            return result  # type: ignore[return-value]

        # Otherwise, result is (dest_path, errors) for the form
        if isinstance(result, tuple) and len(result) == 2:
            dest_path, errors = result
            if not isinstance(errors, dict):
                errors = {}
        else:
            # Fallback if result format is unexpected
            _LOGGER.error(
                "Unexpected result format from clone_panel_to_simulation: %s",
                type(result),
            )
            return self.async_abort(reason="unknown")

        # If user_input was provided and there are no errors, the operation succeeded
        if user_input is not None and not errors:
            return self.async_create_entry(
                title="Simulation Created",
                data={},
                description=f"Cloned panel to {dest_path.name} in simulation_configs",
            )

        # Compute device name for form display
        device_name = self.config_entry.data.get("device_name", self.config_entry.title)

        # Confirm form with destination field
        schema = vol.Schema(
            {
                vol.Required("destination", default=str(dest_path)): selector(
                    {"text": {"multiline": False}}
                )
            }
        )
        return self.async_show_form(
            step_id="clone_panel_to_simulation",
            data_schema=schema,
            description_placeholders={
                "panel": device_name or "Span Panel",
            },
            errors=errors,
        )

    async def async_step_manage_simulation_configs(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Menu to import or export simulation configs."""
        if user_input is None:
            return self.async_show_menu(
                step_id="manage_simulation_configs",
                menu_options={
                    "simulation_import": "Import Simulation Config",
                    "simulation_export": "Export Simulation Config",
                },
            )
        return self.async_abort(reason="unknown")

    def _get_simulation_start_time_schema(self) -> vol.Schema:
        """Get the simulation start time schema."""
        return vol.Schema(
            {
                vol.Optional(CONF_SIMULATION_START_TIME): str,
            }
        )

    def _get_simulation_start_time_defaults(self) -> dict[str, Any]:
        """Get the simulation start time defaults."""
        return {
            CONF_SIMULATION_START_TIME: self.config_entry.options.get(
                CONF_SIMULATION_START_TIME, ""
            ),
        }

    def _get_simulation_offline_minutes_schema(self) -> vol.Schema:
        """Get the simulation offline minutes schema."""
        return vol.Schema(
            {
                vol.Optional(CONF_SIMULATION_OFFLINE_MINUTES): int,
            }
        )

    def _get_simulation_offline_minutes_defaults(self) -> dict[str, Any]:
        """Get the simulation offline minutes defaults."""
        return {
            CONF_SIMULATION_OFFLINE_MINUTES: self.config_entry.options.get(
                CONF_SIMULATION_OFFLINE_MINUTES, 0
            ),
        }

    def _get_entity_naming_schema(self) -> vol.Schema:
        """Get the entity naming options schema."""
        current_pattern = self._get_current_naming_pattern()

        # Legacy installations can only migrate to friendly names first
        if current_pattern == EntityNamingPattern.LEGACY_NAMES.value:
            pattern_options = {
                EntityNamingPattern.FRIENDLY_NAMES.value: "Friendly Names (e.g., span_panel_kitchen_outlets_power)",
            }
        else:
            # Modern installations can switch between the two modern patterns
            pattern_options = {
                EntityNamingPattern.FRIENDLY_NAMES.value: "Friendly Names (e.g., span_panel_kitchen_outlets_power)",
                EntityNamingPattern.CIRCUIT_NUMBERS.value: "Circuit Numbers (e.g., span_panel_circuit_15_power)",
            }

        return vol.Schema(
            {
                vol.Optional(ENTITY_NAMING_PATTERN): vol.In(pattern_options),
            }
        )

    def _get_current_naming_pattern(self) -> str:
        """Determine the current entity naming pattern from configuration flags."""
        return get_current_naming_pattern(self.config_entry)

    async def _migrate_entity_ids(self, old_pattern: str, new_pattern: str) -> None:
        """Migrate entity IDs when naming pattern changes."""
        _LOGGER.info("Starting entity ID migration from %s to %s", old_pattern, new_pattern)

        # Get the coordinator to handle migration using actual entity objects
        coordinator_data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {})
        coordinator = coordinator_data.get(COORDINATOR)

        if not coordinator:
            _LOGGER.error("Cannot migrate entities: coordinator not found")
            return

        # Determine old and new flags based on patterns
        old_flags = self._pattern_to_flags(old_pattern)
        new_flags = self._pattern_to_flags(new_pattern)

        # Perform the migration using the coordinator with old and new flags
        success = await coordinator.migrate_entity_ids(old_flags, new_flags)

        if success:
            _LOGGER.debug("Entity migration completed successfully")
        else:
            _LOGGER.error("Entity migration failed")

    @staticmethod
    def _entities_have_device_prefix(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
        """Best-effort detection if entities already use the device prefix.

        Checks the entity registry for any entity belonging to this config entry where
        the object_id starts with the device name prefix. Both FRIENDLY_NAMES and CIRCUIT_NUMBERS
        patterns include the device name prefix; only LEGACY lacks it.
        """
        registry = er.async_get(hass)

        # Get the device name from config entry and sanitize it
        device_name = config_entry.data.get("device_name", config_entry.title)
        if not device_name:
            return False

        sanitized_device_name = slugify(device_name)
        for entry in registry.entities.values():
            try:
                if entry.config_entry_id != config_entry.entry_id:
                    continue
                object_id = entry.entity_id.split(".", 1)[1]
                # Check if the object_id starts with the device name followed by underscore
                if object_id.startswith(f"{sanitized_device_name}_"):
                    return True
            except (IndexError, AttributeError):
                continue
        return False

    def _pattern_to_flags(self, pattern: str) -> dict[str, bool]:
        """Convert entity naming pattern to configuration flags."""
        return pattern_to_flags(pattern)

    def _mark_for_legacy_migration(self) -> None:
        """Mark the config entry for legacy migration after reload.

        This method stores a flag in the config entry data that indicates a legacy
        migration is needed. The integration will check for this flag after startup
        but before the first update.
        """
        _LOGGER.info("Marking config entry for legacy migration after reload")

        # Update the config entry data to include the migration flag
        current_data = dict(self.config_entry.data)
        current_data["pending_legacy_migration"] = True

        _LOGGER.info(
            "Setting pending_legacy_migration flag in config entry data: %s",
            current_data,
        )

        # Update the config entry with the migration flag
        self.hass.config_entries.async_update_entry(self.config_entry, data=current_data)
