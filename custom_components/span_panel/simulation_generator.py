"""Build simulation YAML from a live panel snapshot.

This module inspects the current coordinator data and produces a YAML dict
that matches span_panel_api's simulation reference. It infers templates from
names and seeds energy profiles from current power readings.

YAML Format Structure
---------------------
The generated YAML contains these main sections:

- **panel_config**: Panel hardware configuration (serial, total_tabs, main_size)
- **circuit_templates**: Reusable templates for circuit behavior patterns
  - Each template defines energy_profile (power ranges, typical power, variation)
  - Includes relay_behavior (controllable/non_controllable)
  - Specifies priority (MUST_HAVE, NICE_TO_HAVE, NON_ESSENTIAL)
  - Optional: cycling_pattern, time_of_day_profile, smart_behavior
- **circuits**: List of individual circuits referencing templates
  - Each has: id, name, tabs, template reference
  - Optional overrides for specific circuits
- **unmapped_tabs**: Tab numbers not assigned to any circuit
- **unmapped_tab_templates**: Templates for unmapped tabs (e.g., solar)
- **tab_synchronizations**: Groups of tabs that should sync (e.g., 240V circuits)
- **simulation_params**: Update interval, time acceleration, noise factor

Example Output
--------------
{
    "panel_config": {
        "serial_number": "DSM010000ABCDEF",
        "total_tabs": 32,
        "main_size": 200
    },
    "circuit_templates": {
        "lighting": {
            "energy_profile": {
                "mode": "consumer",
                "power_range": [0.0, 300.0],
                "typical_power": 40.0,
                "power_variation": 0.1
            },
            "relay_behavior": "controllable",
            "priority": "NON_ESSENTIAL"
        }
    },
    "circuits": [
        {
            "id": "1",
            "name": "Kitchen Lights",
            "tabs": [1],
            "template": "lighting"
        }
    ],
    "unmapped_tabs": [2, 3, 4, ...],
    "simulation_params": {
        "update_interval": 5,
        "time_acceleration": 1.0,
        "noise_factor": 0.02
    }
}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SimulationYamlGenerator:
    """Generate YAML from live panel data."""

    hass: Any
    coordinator: Any
    solar_leg1: int | None = None
    solar_leg2: int | None = None

    async def build_yaml_from_live_panel(self) -> tuple[dict[str, Any], int]:
        """Build simulation YAML configuration from live panel data.

        Analyzes the current panel state from the coordinator and generates
        a complete simulation YAML configuration that can be used to recreate
        similar behavior in simulation mode.

        Process:
        1. Extract all circuits from coordinator data
        2. Infer appropriate templates from circuit names and power readings
        3. Create circuit entries with template references
        4. Determine panel size (8, 32, or 40 tabs) from mapped tabs
        5. Identify unmapped tabs
        6. Add solar configuration if solar legs provided
        7. Set sensible simulation parameters

        Returns:
            tuple[dict[str, Any], int]: A tuple containing:
                - Complete YAML configuration dictionary (see module docstring for structure)
                - Total number of tabs (8, 32, or 40) determined from circuit data

        Note:
            Circuits with IDs starting with "unmapped_tab_" are skipped as they
            represent placeholder circuits for unmapped tabs and should not be
            included in the simulation configuration.

        Example:
            generator = SimulationYamlGenerator(hass, coordinator, solar_leg1=5, solar_leg2=6)
            yaml_dict, num_tabs = await generator.build_yaml_from_live_panel()
            # yaml_dict now contains complete simulation configuration
            # num_tabs is 8, 32, or 40 based on actual circuit distribution

        """
        data = getattr(self.coordinator, "data", None)
        circuits_obj = getattr(data, "circuits", None)

        # Prepare containers
        circuit_templates: dict[str, Any] = {}
        circuits: list[dict[str, Any]] = []
        mapped_tabs: set[int] = set()

        # Iterate circuits
        iter_dict: dict[str, Any] = {}
        # Safely extract iterable circuits mapping without accessing attributes on None
        if isinstance(circuits_obj, dict):
            iter_dict = circuits_obj
        elif circuits_obj is not None:
            inner_circuits = getattr(circuits_obj, "circuits", None)
            if isinstance(inner_circuits, dict):
                iter_dict = inner_circuits

        for cid, c in iter_dict.items():
            name = str(getattr(c, "name", cid))
            power_w = float(getattr(c, "instant_power_w", 0.0) or 0.0)
            raw_tabs = getattr(c, "tabs", []) if hasattr(c, "tabs") else []
            tabs = (
                list(raw_tabs)
                if isinstance(raw_tabs, (list | tuple))
                else ([] if raw_tabs in (None, "UNSET") else [int(raw_tabs)])
            )
            mapped_tabs.update(tabs)

            # Skip unmapped tab circuits - they should be handled as unmapped tabs, not circuits
            if str(cid).startswith("unmapped_tab_"):
                continue

            template_key = self._infer_template_key(name, power_w, tabs)
            if template_key not in circuit_templates:
                circuit_templates[template_key] = self._make_template(template_key, power_w, name)

            entry: dict[str, Any] = {
                "id": str(cid),
                "name": name,
                "tabs": tabs,
                "template": template_key,
            }
            if power_w != 0.0:
                entry["overrides"] = {"energy_profile": {"typical_power": power_w}}

            circuits.append(entry)

        # Compute total tabs
        num_tabs = 32
        if mapped_tabs:
            max_tab = max(mapped_tabs)
            if max_tab <= 8:
                num_tabs = 8
            elif max_tab <= 32:
                num_tabs = 32
            else:
                num_tabs = 40

        # Panel config
        serial = (
            getattr(getattr(data, "status", None), "serial_number", None) or "span_panel_simulation"
        )
        snapshot_yaml: dict[str, Any] = {
            "panel_config": {
                "serial_number": str(serial),
                "total_tabs": num_tabs,
                "main_size": 200,
            },
            "circuit_templates": circuit_templates,
            "circuits": circuits,
            "unmapped_tabs": sorted(set(range(1, num_tabs + 1)) - mapped_tabs),
            "simulation_params": {
                "update_interval": 5,
                "time_acceleration": 1.0,
                "noise_factor": 0.02,
            },
        }

        # Add solar configuration if legs provided and valid
        self._maybe_add_solar(snapshot_yaml)

        return snapshot_yaml, num_tabs

    def _maybe_add_solar(self, yaml_doc: dict[str, Any]) -> None:
        """Add solar production configuration to YAML if solar legs are valid.

        Modifies the YAML document in-place to add solar production configuration
        for 240V split-phase solar systems using two unmapped tabs.

        Solar configuration includes:
        - A "solar_production" template with producer energy profile
        - Unmapped tab templates for both solar legs
        - Tab synchronization group for 240V split-phase behavior
        - Updates to unmapped_tabs list

        Args:
            yaml_doc: The YAML configuration dictionary to modify in-place

        Requirements for solar to be added:
        - Both solar_leg1 and solar_leg2 must be set
        - Both legs must be > 0
        - Legs must be different (leg1 != leg2)

        Note:
            If requirements not met, the function returns without modifying yaml_doc.
            This allows the generator to gracefully handle panels without solar.

        Example solar configuration added:
            {
                "circuit_templates": {
                    "solar_production": {
                        "energy_profile": {
                            "mode": "producer",
                            "power_range": [-2000.0, 0.0],
                            "typical_power": -1500.0,
                            ...
                        },
                        "time_of_day_profile": {
                            "enabled": True,
                            "peak_hours": [11, 12, 13, 14, 15]
                        }
                    }
                },
                "unmapped_tab_templates": {
                    "5": <solar_production template>,
                    "6": <solar_production template>
                },
                "tab_synchronizations": [
                    {
                        "tabs": [5, 6],
                        "behavior": "240v_split_phase",
                        "power_split": "equal",
                        "energy_sync": True,
                        "template": "solar_production"
                    }
                ]
            }

        """
        l1 = int(self.solar_leg1 or 0)
        l2 = int(self.solar_leg2 or 0)
        if l1 <= 0 or l2 <= 0 or l1 == l2:
            return

        # Ensure solar template exists
        templates = yaml_doc.setdefault("circuit_templates", {})
        if "solar_production" not in templates:
            templates["solar_production"] = {
                "energy_profile": {
                    "mode": "producer",
                    "power_range": [-2000.0, 0.0],
                    "typical_power": -1500.0,
                    "power_variation": 0.2,
                    "efficiency": 0.85,
                },
                "relay_behavior": "non_controllable",
                "priority": "MUST_HAVE",
                "time_of_day_profile": {
                    "enabled": True,
                    "peak_hours": [11, 12, 13, 14, 15],
                },
            }

        # Unmapped tab templates for the two solar legs
        unmapped = yaml_doc.setdefault("unmapped_tab_templates", {})
        for tab in (l1, l2):
            key = str(tab)
            if key not in unmapped:
                unmapped[key] = templates["solar_production"]

        # Synchronization group for the two legs
        tab_syncs: list[dict[str, Any]] = yaml_doc.setdefault("tab_synchronizations", [])
        tab_syncs.append(
            {
                "tabs": [l1, l2],
                "behavior": "240v_split_phase",
                "power_split": "equal",
                "energy_sync": True,
                "template": "solar_production",
            }
        )

        # Ensure legs listed as unmapped
        yaml_doc["unmapped_tabs"] = sorted(set(yaml_doc.get("unmapped_tabs", [])) | {l1, l2})

    def _infer_template_key(self, name: str, power_w: float, tabs: list[int]) -> str:
        """Infer appropriate template key from circuit characteristics.

        Analyzes circuit name, power reading, and tab configuration to determine
        which template best matches the circuit's expected behavior pattern.

        Template inference rules (in priority order):
        1. **lighting**: Name contains "light" or "lights"
        2. **kitchen_outlets**: Name contains both "kitchen" and "outlet"
        3. **hvac**: Name contains "hvac", "furnace", "air conditioner", "ac", or "heat pump"
        4. **refrigerator**: Name contains "fridge", "refrigerator", or "wine fridge"
        5. **ev_charger**: Name contains "ev" or "charger"
        6. **pool_equipment**: Name contains "pool", "spa", or "fountain"
        7. **always_on**: Name contains "internet", "router", "network", or "modem"
        8. **major_appliance**: Circuit uses 2+ tabs (typically 240V circuits)
        9. **outlets**: Name contains "outlet"
        10. **producer**: Power reading is negative (generating power)
        11. **major_appliance**: Default fallback for unrecognized circuits

        Args:
            name: Circuit name from panel (case-insensitive matching)
            power_w: Current power reading in watts (negative = production)
            tabs: List of tab numbers this circuit occupies

        Returns:
            str: Template key matching one of the known templates that
                 will be created by _make_template()

        Example:
            _infer_template_key("Kitchen Lights", 45.0, [1])
            # Returns: "lighting"

            _infer_template_key("Main AC Unit", 3500.0, [15, 16])
            # Returns: "hvac"

            _infer_template_key("Solar Inverter", -1800.0, [5, 6])
            # Returns: "producer"

        """
        lname = name.lower()
        if any(k in lname for k in ("light", "lights")):
            return "lighting"
        if "kitchen" in lname and "outlet" in lname:
            return "kitchen_outlets"
        if any(k in lname for k in ("hvac", "furnace", "air conditioner", "ac", "heat pump")):
            return "hvac"
        if any(k in lname for k in ("fridge", "refrigerator", "wine fridge")):
            return "refrigerator"
        if any(k in lname for k in ("ev", "charger")):
            return "ev_charger"
        if any(k in lname for k in ("pool", "spa", "fountain")):
            return "pool_equipment"
        if any(k in lname for k in ("internet", "router", "network", "modem")):
            return "always_on"
        if len(tabs) >= 2:
            return "major_appliance"
        if "outlet" in lname:
            return "outlets"
        if power_w < 0:
            return "producer"
        return "major_appliance"

    def _make_template(self, key: str, typical: float, name: str) -> dict[str, Any]:
        """Create a circuit template dictionary with realistic behavior parameters.

        Generates a complete template configuration based on the template key,
        seeding energy profiles with actual power readings from the live panel.

        Each template includes:
        - **energy_profile**: Power consumption/production characteristics
          - mode: "consumer" or "producer"
          - power_range: [min, max] power in watts
          - typical_power: Expected average power (from live reading or sensible default)
          - power_variation: Randomness factor (0.0-1.0)
        - **relay_behavior**: "controllable" or "non_controllable"
        - **priority**: "MUST_HAVE", "NICE_TO_HAVE", or "NON_ESSENTIAL"
        - Optional features: cycling_pattern, time_of_day_profile, smart_behavior

        Template Types:
        ---------------
        **producer**: Solar or other generation (-power)
        - Negative power range based on typical output
        - Non-controllable, MUST_HAVE priority
        - 30% power variation for realistic generation patterns

        **ev_charger**: Electric vehicle charging
        - 0W to 7200W+ range (doubled from typical)
        - Controllable, NON_ESSENTIAL priority
        - Night-time charging profile (10pm-6am peak)
        - Smart grid response (can reduce power 60% during stress)

        **refrigerator**: Always-on appliances with cycling
        - 50-200W range, ~120W typical
        - Non-controllable, MUST_HAVE priority
        - Cycling: 10min on, 30min off

        **hvac**: Heating/cooling systems
        - 0W to 2800W+ range, ~1800W typical
        - Controllable, MUST_HAVE priority
        - Cycling: 20min on, 40min off

        **lighting**: General lighting circuits
        - 0W to 300W range, ~40W typical
        - Controllable, NON_ESSENTIAL priority
        - Evening peak hours (6pm-10pm)

        **kitchen_outlets**: High-power kitchen circuits
        - 0W to 2400W+ range, ~300W typical
        - Controllable, MUST_HAVE priority
        - High variation (40%) for intermittent use

        **outlets**: Standard outlet circuits
        - 0W to 1800W range, ~150W typical
        - Controllable, MUST_HAVE priority
        - 40% variation for varied appliances

        **always_on**: Network equipment, etc.
        - 40-100W constant range, ~60W typical
        - Controllable, MUST_HAVE priority
        - Low variation (10%) for stable loads

        **pool_equipment**: Pool pumps, heaters
        - 0W to 1200W+ range, ~800W typical
        - Controllable, NON_ESSENTIAL priority
        - Long cycling: 2h on, 4h off

        **major_appliance**: Fallback for unrecognized circuits
        - 0W to 2500W+ range, ~800W typical
        - Controllable, NON_ESSENTIAL priority
        - Moderate variation (30%)

        Args:
            key: Template key from _infer_template_key()
            typical: Actual power reading from live panel (used to seed ranges)
            name: Circuit name (currently unused, available for future enhancements)

        Returns:
            dict[str, Any]: Complete template dictionary ready for YAML output

        Note:
            Power ranges are automatically scaled based on the typical reading
            to ensure realistic simulation behavior. Negative typical values
            automatically create producer templates regardless of key.

        Example:
            template = _make_template("lighting", 65.0, "Living Room Lights")
            # Returns:
            # {
            #     "energy_profile": {
            #         "mode": "consumer",
            #         "power_range": [0.0, 130.0],  # 2x typical
            #         "typical_power": 65.0,
            #         "power_variation": 0.1
            #     },
            #     "relay_behavior": "controllable",
            #     "priority": "NON_ESSENTIAL",
            #     "time_of_day_profile": {
            #         "enabled": True,
            #         "peak_hours": [18, 19, 20, 21, 22]
            #     }
            # }

        """
        # Base ranges derived from snapshot
        if key == "producer" or typical < 0:
            pr_min = min(typical * 2.0, -50.0)
            profile = {
                "mode": "producer",
                "power_range": [pr_min, 0.0],
                "typical_power": typical,
                "power_variation": 0.3,
            }
            return {
                "energy_profile": profile,
                "relay_behavior": "non_controllable",
                "priority": "MUST_HAVE",
            }

        if key == "ev_charger":
            profile = {
                "mode": "consumer",
                "power_range": [0.0, max(abs(typical) * 2.0, 7200.0)],
                "typical_power": max(typical, 3000.0),
                "power_variation": 0.15,
            }
            return {
                "energy_profile": profile,
                "relay_behavior": "controllable",
                "priority": "NON_ESSENTIAL",
                # Prefer night charging and respond to grid stress
                "time_of_day_profile": {
                    "enabled": True,
                    "peak_hours": [22, 23, 0, 1, 2, 3, 4, 5, 6],
                },
                "smart_behavior": {"responds_to_grid": True, "max_power_reduction": 0.6},
            }

        if key == "refrigerator":
            profile = {
                "mode": "consumer",
                "power_range": [50.0, 200.0],
                "typical_power": max(typical, 120.0),
                "power_variation": 0.2,
            }
            return {
                "energy_profile": profile,
                "relay_behavior": "non_controllable",
                "priority": "MUST_HAVE",
                "cycling_pattern": {"on_duration": 600, "off_duration": 1800},
            }

        if key == "hvac":
            profile = {
                "mode": "consumer",
                "power_range": [0.0, max(abs(typical) * 2.0, 2800.0)],
                "typical_power": max(typical, 1800.0),
                "power_variation": 0.15,
            }
            return {
                "energy_profile": profile,
                "relay_behavior": "controllable",
                "priority": "MUST_HAVE",
                "cycling_pattern": {"on_duration": 1200, "off_duration": 2400},
            }

        if key == "lighting":
            profile = {
                "mode": "consumer",
                "power_range": [0.0, max(abs(typical) * 2.0, 300.0)],
                "typical_power": max(typical, 40.0),
                "power_variation": 0.1,
            }
            return {
                "energy_profile": profile,
                "relay_behavior": "controllable",
                "priority": "NON_ESSENTIAL",
                "time_of_day_profile": {"enabled": True, "peak_hours": [18, 19, 20, 21, 22]},
            }

        if key == "kitchen_outlets":
            profile = {
                "mode": "consumer",
                "power_range": [0.0, max(abs(typical) * 2.0, 2400.0)],
                "typical_power": max(typical, 300.0),
                "power_variation": 0.4,
            }
            return {
                "energy_profile": profile,
                "relay_behavior": "controllable",
                "priority": "MUST_HAVE",
            }

        if key == "outlets":
            profile = {
                "mode": "consumer",
                "power_range": [0.0, max(abs(typical) * 2.0, 1800.0)],
                "typical_power": max(typical, 150.0),
                "power_variation": 0.4,
            }
            return {
                "energy_profile": profile,
                "relay_behavior": "controllable",
                "priority": "MUST_HAVE",
            }

        if key == "always_on":
            profile = {
                "mode": "consumer",
                "power_range": [40.0, 100.0],
                "typical_power": max(typical, 60.0),
                "power_variation": 0.1,
            }
            return {
                "energy_profile": profile,
                "relay_behavior": "controllable",
                "priority": "MUST_HAVE",
            }

        if key == "pool_equipment":
            profile = {
                "mode": "consumer",
                "power_range": [0.0, max(abs(typical) * 2.0, 1200.0)],
                "typical_power": max(typical, 800.0),
                "power_variation": 0.1,
            }
            return {
                "energy_profile": profile,
                "relay_behavior": "controllable",
                "priority": "NON_ESSENTIAL",
                # Typical pump run: 2h on, 4h off, repeating
                "cycling_pattern": {"on_duration": 7200, "off_duration": 14400},
            }

        # major_appliance and fallback
        profile = {
            "mode": "consumer",
            "power_range": [0.0, max(abs(typical) * 2.0, 2500.0)],
            "typical_power": max(typical, 800.0),
            "power_variation": 0.3,
        }
        return {
            "energy_profile": profile,
            "relay_behavior": "controllable",
            "priority": "NON_ESSENTIAL",
        }
