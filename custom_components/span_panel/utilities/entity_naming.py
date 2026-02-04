"""Entity ID construction utilities for Span Panel integration.

Provides functions for constructing entity IDs based on configuration
flags (USE_CIRCUIT_NUMBERS, USE_DEVICE_PREFIX) and entity registry lookups.

Extracted from helpers.py as part of Sub-Phase 5.3.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from ..const import DOMAIN, USE_CIRCUIT_NUMBERS, USE_DEVICE_PREFIX
from ..util import panel_to_device_info

if TYPE_CHECKING:
    from ..coordinator import SpanPanelCoordinator
    from ..span_panel import SpanPanel
    from ..span_panel_circuit import SpanPanelCircuit

_LOGGER = logging.getLogger(__name__)


def get_circuit_number(circuit: SpanPanelCircuit) -> int | str:
    """Extract circuit number (tab position) from circuit object.

    Args:
        circuit: SpanPanelCircuit object

    Returns:
        Circuit number (tab position) or circuit_id if no tabs

    """
    return circuit.tabs[0] if circuit.tabs else circuit.circuit_id


def construct_entity_id(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    platform: str,
    circuit_name: str,
    circuit_number: int | str,
    suffix: str,
    unique_id: str | None = None,
) -> str | None:
    """Construct entity ID based on integration configuration flags.

    Used by switch, binary_sensor, and select entities.
    This function handles entity naming for individual circuit entities based on the
    USE_CIRCUIT_NUMBERS and USE_DEVICE_PREFIX configuration flags. It also checks
    the entity registry to respect user customizations when unique_id is provided.

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        platform: Platform name ("sensor", "switch", "select")
        circuit_name: Human-readable circuit name
        circuit_number: Circuit number/identifier
        suffix: Entity-specific suffix ("power", "energy_produced", etc.)
        unique_id: The unique ID for this entity (None to skip registry lookup)

    Returns:
        Constructed entity ID string or None if device info unavailable

    """
    # Check registry first only if unique_id is provided
    if unique_id is not None:
        entity_registry = er.async_get(coordinator.hass)
        existing_entity_id = entity_registry.async_get_entity_id(platform, DOMAIN, unique_id)

        if existing_entity_id:
            return existing_entity_id

    # Construct default entity_id
    config_entry = coordinator.config_entry

    # Get device name from config entry data
    device_name = config_entry.data.get("device_name", config_entry.title)
    if not device_name:
        return None

    # Default to False so legacy entries without the flag use friendly names
    use_circuit_numbers = config_entry.options.get(USE_CIRCUIT_NUMBERS, False)
    use_device_prefix = config_entry.options.get(USE_DEVICE_PREFIX, True)

    # Build entity ID components
    parts = []

    if use_device_prefix:
        # Sanitize device name for entity ID use
        sanitized_device_name = slugify(device_name)
        parts.append(sanitized_device_name)

    if use_circuit_numbers:
        parts.append(f"circuit_{circuit_number}")
    else:
        circuit_name_slug = slugify(circuit_name)
        parts.append(circuit_name_slug)

    # Only add suffix if it's different from the last word in the circuit name
    # This prevents duplication like "current_power_power"
    if suffix:
        circuit_name_words = circuit_name.lower().split()
        last_word = circuit_name_words[-1] if circuit_name_words else ""

        # Convert last word to same format as suffix for comparison
        last_word_normalized = last_word.replace(" ", "_")

        # Only add suffix if it's not the same as the last word in the name
        if suffix != last_word_normalized:
            parts.append(suffix)

    entity_id = f"{platform}.{'_'.join(parts)}"
    return entity_id


def construct_panel_entity_id(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    platform: str,
    suffix: str,
    device_name: str,
    unique_id: str | None = None,
    use_device_prefix: bool | None = None,
) -> str | None:
    """Construct entity ID for panel-level sensors based on integration configuration flags.

    This function handles entity naming for panel-level entities based on the
    USE_DEVICE_PREFIX configuration flag. It also checks the entity registry
    to respect user customizations when unique_id is provided.

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        platform: Platform name ("sensor", "switch", "select")
        suffix: Entity-specific suffix ("current_power", "feed_through_power", etc.)
        device_name: Device name for the panel
        unique_id: The unique ID for this entity (None to skip registry lookup)
        use_device_prefix: Whether to include device name prefix in entity ID (None to use config option)

    Returns:
        Constructed entity ID string or None if device info unavailable

    """
    # Check registry first only if unique_id is provided
    if unique_id is not None:
        entity_registry = er.async_get(coordinator.hass)
        existing_entity_id = entity_registry.async_get_entity_id(platform, DOMAIN, unique_id)

        # Debug logging for panel entity registry lookup
        _LOGGER.debug(
            "Panel helper registry lookup - unique_id=%s, found_entity_id=%s",
            unique_id,
            existing_entity_id,
        )

        if existing_entity_id:
            return existing_entity_id

    # Construct default entity_id
    config_entry = coordinator.config_entry

    if not device_name:
        return None

    if use_device_prefix is None:
        use_device_prefix = config_entry.options.get(USE_DEVICE_PREFIX, True)

    # Build entity ID components
    parts = []

    if use_device_prefix:
        # Sanitize device name for entity ID use
        sanitized_device_name = slugify(device_name)
        parts.append(sanitized_device_name)

    parts.append(suffix)

    entity_id = f"{platform}.{'_'.join(parts)}"
    return entity_id


def construct_panel_synthetic_entity_id(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    platform: str,
    suffix: str,
    device_name: str,
    unique_id: str | None = None,
) -> str | None:
    """Construct entity ID for synthetic panel-level sensors with device prefix logic.

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        platform: Platform name ("sensor", etc.)
        suffix: Entity-specific suffix ("current_power", etc.)
        device_name: Device name for the panel
        unique_id: The unique ID for this entity (None to skip registry lookup)

    Returns:
        Constructed entity ID string or None if device info unavailable

    """
    # Check registry first only if unique_id is provided
    if unique_id is not None:
        entity_registry = er.async_get(coordinator.hass)
        existing_entity_id = entity_registry.async_get_entity_id(platform, DOMAIN, unique_id)
        if existing_entity_id:
            return existing_entity_id
        else:
            # FATAL ERROR: Expected unique_id not found in registry
            raise ValueError(
                f"REGISTRY LOOKUP ERROR: Expected unique_id '{unique_id}' not found in registry. "
                "This indicates a migration or configuration mismatch."
            )

    config_entry = coordinator.config_entry
    if not device_name:
        return None
    use_device_prefix = config_entry.options.get(USE_DEVICE_PREFIX, True)
    parts = []
    if use_device_prefix:
        # Sanitize device name for entity ID use
        sanitized_device_name = slugify(device_name)
        parts.append(sanitized_device_name)
    parts.append(suffix)
    entity_id = f"{platform}.{'_'.join(parts)}"
    return entity_id


def construct_single_circuit_entity_id(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    platform: str,
    suffix: str,
    circuit_data: SpanPanelCircuit,
    unique_id: str | None = None,
    device_name: str | None = None,
) -> str | None:
    """Construct entity ID for single-circuit sensors.

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        platform: Platform name ("sensor", "switch", "select")
        suffix: Entity-specific suffix ("power", "energy_produced", etc.)
        circuit_data: Circuit data object
        unique_id: The unique ID for this entity (None to skip registry lookup)
        device_name: Device name for entity ID construction (None to use from config entry)

    Returns:
        Constructed entity ID string or None if device info unavailable

    """
    # Check registry first only if unique_id is provided
    if unique_id is not None:
        entity_registry = er.async_get(coordinator.hass)
        existing_entity_id = entity_registry.async_get_entity_id(platform, DOMAIN, unique_id)

        _LOGGER.debug(
            "Circuit helper registry lookup - unique_id=%s, found_entity_id=%s",
            unique_id,
            existing_entity_id,
        )

        if existing_entity_id:
            return existing_entity_id
        else:
            # FATAL ERROR: Expected unique_id not found in registry
            raise ValueError(
                f"REGISTRY LOOKUP ERROR: Expected unique_id '{unique_id}' not found in registry. "
                "This indicates a migration or configuration mismatch."
            )
    else:
        _LOGGER.debug("Circuit helper - no unique_id provided, skipping registry lookup")

    # Get device info
    device_info = panel_to_device_info(span_panel, device_name)
    if not device_info or not device_info.get("name"):
        return None

    use_circuit_numbers = coordinator.config_entry.options.get(USE_CIRCUIT_NUMBERS, False)

    if use_circuit_numbers:
        # Check if this is a 240V circuit (2 tabs) or 120V circuit (1 tab)
        if circuit_data.tabs and len(circuit_data.tabs) == 2:
            # 240V circuit - use both tab numbers
            sorted_tabs = sorted(circuit_data.tabs)
            circuit_part = f"circuit_{sorted_tabs[0]}_{sorted_tabs[1]}"
        elif circuit_data.tabs and len(circuit_data.tabs) == 1:
            # 120V circuit - use single tab number
            circuit_part = f"circuit_{circuit_data.tabs[0]}"
        else:
            # Fallback to original logic for circuits without tabs or with invalid tab count
            circuit_number = get_circuit_number(circuit_data)
            if circuit_number:
                circuit_part = f"circuit_{circuit_number}"
            else:
                circuit_part = "circuit_unknown"
    else:
        # Use friendly name pattern: sensor.span_panel_solar_east_power
        if circuit_data.name:
            circuit_part = slugify(circuit_data.name)
        else:
            circuit_part = "single_circuit"

    # Build the entity ID (only for non-voltage-specific cases)
    use_device_prefix = coordinator.config_entry.options.get(USE_DEVICE_PREFIX, False)
    parts = []

    if use_device_prefix:
        device_name = device_info.get("name")
        if device_name:
            # Sanitize device name for entity ID use
            sanitized_device_name = slugify(device_name)
            parts.append(sanitized_device_name)

    parts.append(circuit_part)

    # Add suffix if not already in circuit_part
    if suffix and not circuit_part.endswith(f"_{suffix}"):
        parts.append(suffix)

    return f"{platform}.{'_'.join(parts)}"


def construct_multi_circuit_entity_id(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    platform: str,
    suffix: str,
    circuit_numbers: list[int],
    friendly_name: str | None = None,
    unique_id: str | None = None,
) -> str | None:
    """Construct entity ID for multi-circuit sensors (like solar inverters).

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        platform: Platform name ("sensor", "switch", "select")
        suffix: Entity-specific suffix ("power", "energy_produced", etc.)
        circuit_numbers: List of circuit numbers this sensor combines
        friendly_name: Descriptive name for this sensor (required if unique_id is None)
        unique_id: The unique ID for this entity (None to skip registry lookup)

    Returns:
        Constructed entity ID string or None if device info unavailable

    """
    # Check registry first only if unique_id is provided
    if unique_id is not None:
        entity_registry = er.async_get(coordinator.hass)
        existing_entity_id = entity_registry.async_get_entity_id(platform, DOMAIN, unique_id)

        _LOGGER.debug(
            "Multi-circuit helper registry lookup (switches/selects) - unique_id=%s, found_entity_id=%s",
            unique_id,
            existing_entity_id,
        )

        if existing_entity_id:
            return existing_entity_id
        else:
            # During migration, unique_id lookup should always succeed
            raise ValueError(
                f"Registry lookup failed for unique_id '{unique_id}' during migration. Entity should exist in registry."
            )
    else:
        _LOGGER.debug(
            "Multi-circuit helper (switches/selects) - no unique_id provided, skipping registry lookup"
        )

    # Get device name from config entry data
    device_name = coordinator.config_entry.data.get("device_name", coordinator.config_entry.title)
    if not device_name:
        return None

    use_circuit_numbers = coordinator.config_entry.options.get(USE_CIRCUIT_NUMBERS, False)

    # If no unique_id provided, friendly_name is required when not using circuit numbers
    if unique_id is None and not use_circuit_numbers and not friendly_name:
        _LOGGER.error(
            "friendly_name is required when unique_id is None and not using circuit numbers for multi-circuit entity"
        )
        return None

    if use_circuit_numbers:
        # Use circuit number pattern: sensor.span_panel_circuit_30_32_power
        if circuit_numbers:
            sorted_circuits = sorted([num for num in circuit_numbers if num > 0])
        else:
            sorted_circuits = []
        if sorted_circuits:
            if len(sorted_circuits) == 1:
                circuit_part = f"circuit_{sorted_circuits[0]}"
            else:
                circuit_list = "_".join(str(num) for num in sorted_circuits)
                circuit_part = f"circuit_{circuit_list}"
        else:
            raise ValueError(
                f"Circuit-based naming is enabled but no valid circuit numbers provided. "
                f"Got circuit_numbers={circuit_numbers}. Multi-circuit entities require valid circuit numbers when USE_CIRCUIT_NUMBERS is True."
            )
    else:
        # Use friendly name pattern: sensor.span_panel_solar_inverter_power
        circuit_part = slugify(friendly_name)

    # Build the entity ID
    use_device_prefix = coordinator.config_entry.options.get(USE_DEVICE_PREFIX, False)
    parts = []

    if use_device_prefix:
        if device_name:
            # Sanitize device name for entity ID use
            sanitized_device_name = slugify(device_name)
            parts.append(sanitized_device_name)

    parts.append(circuit_part)

    # Add suffix if not already in circuit_part
    if suffix and not circuit_part.endswith(f"_{suffix}"):
        parts.append(suffix)

    return f"{platform}.{'_'.join(parts)}"


def construct_240v_synthetic_entity_id(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    platform: str,
    suffix: str,
    friendly_name: str,
    tab1: int = 0,
    tab2: int = 0,
    unique_id: str | None = None,
) -> str | None:
    """Construct entity ID for synthetic 240V circuits using tab numbers.

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        platform: Platform name ("sensor", "switch", "select")
        suffix: Entity-specific suffix ("power", "energy_produced", etc.)
        friendly_name: Descriptive name for this synthetic circuit
        tab1: First tab number (0 if not used)
        tab2: Second tab number (0 if not used)
        unique_id: The unique ID for this entity (None to skip registry lookup)

    Returns:
        Constructed entity ID string or None if device info unavailable

    """
    # Validate that we have exactly 2 tabs for 240V circuits
    if tab1 <= 0 or tab2 <= 0:
        raise ValueError(
            f"240V synthetic entity requires exactly 2 tabs, got tab1={tab1}, tab2={tab2}"
        )

    # Build tab numbers list
    tab_numbers = [tab1, tab2]

    # Use the multi-circuit helper
    return construct_multi_circuit_entity_id(
        coordinator=coordinator,
        span_panel=span_panel,
        platform=platform,
        suffix=suffix,
        circuit_numbers=tab_numbers,
        friendly_name=friendly_name,
        unique_id=unique_id,
    )


def construct_120v_synthetic_entity_id(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    platform: str,
    suffix: str,
    friendly_name: str,
    tab: int = 0,
    unique_id: str | None = None,
) -> str | None:
    """Construct entity ID for synthetic 120V circuits using tab number.

    Args:
        coordinator: The coordinator instance
        span_panel: The span panel data
        platform: Platform name ("sensor", "switch", "select")
        suffix: Entity-specific suffix ("power", "energy_produced", etc.)
        friendly_name: Descriptive name for this synthetic circuit
        tab: Tab number
        unique_id: The unique ID for this entity (None to skip registry lookup)

    Returns:
        Constructed entity ID string or None if device info unavailable

    """
    # Validate that we have exactly 1 tab for 120V circuits
    if tab <= 0:
        raise ValueError(f"120V synthetic entity requires exactly 1 tab, got tab={tab}")

    # Use the multi-circuit helper with only one tab
    return construct_multi_circuit_entity_id(
        coordinator=coordinator,
        span_panel=span_panel,
        platform=platform,
        suffix=suffix,
        circuit_numbers=[tab],
        friendly_name=friendly_name,
        unique_id=unique_id,
    )


def construct_unmapped_entity_id(
    span_panel: SpanPanel, circuit_id: str, suffix: str, device_name: str | None = None
) -> str:
    """Construct entity ID for unmapped tab with consistent modern naming.

    Args:
        span_panel: The span panel data
        circuit_id: Circuit ID (e.g., "unmapped_tab_32")
        suffix: Sensor suffix (e.g., "power", "energy_produced")
        device_name: The device name to use for entity ID construction

    Returns:
        Entity ID string like "sensor.span_panel_unmapped_tab_32_power"

    """
    # Always use device prefix for unmapped entities
    device_info = panel_to_device_info(span_panel, device_name)
    device_name_raw = device_info.get("name")
    _LOGGER.debug(
        "construct_unmapped_entity_id: circuit_id=%s, suffix=%s, device_name_raw=%s",
        circuit_id,
        suffix,
        device_name_raw,
    )
    if device_name_raw:
        # Sanitize device name for entity ID use
        sanitized_device_name = slugify(device_name_raw)
        result = f"sensor.{sanitized_device_name}_{circuit_id}_{suffix}"
        _LOGGER.debug("construct_unmapped_entity_id result with device: %s", result)
        return result
    else:
        result = f"sensor.{circuit_id}_{suffix}"
        _LOGGER.debug("construct_unmapped_entity_id result without device: %s", result)
        return result


def get_unmapped_circuit_entity_id(
    span_panel: SpanPanel, tab_number: int, suffix: str, device_name: str | None = None
) -> str | None:
    """Get entity ID for an unmapped circuit based on tab number.

    This helper function constructs the entity ID for native unmapped circuit sensors
    that should already exist in Home Assistant. It's useful for synthetic sensors
    that need to reference these native entities in formulas.

    Args:
        span_panel: The span panel data
        tab_number: The tab number (e.g., 30, 32)
        suffix: The sensor suffix (e.g., "power", "energy_produced", "energy_consumed")
        device_name: The device name to use for entity ID construction

    Returns:
        Entity ID string like "sensor.span_panel_unmapped_tab_30_power"
        or None if the circuit doesn't exist

    Examples:
        get_unmapped_circuit_entity_id(span_panel, 30, "power")
        # Returns: "sensor.span_panel_unmapped_tab_30_power"

        get_unmapped_circuit_entity_id(span_panel, 32, "energy_produced")
        # Returns: "sensor.span_panel_unmapped_tab_32_energy_produced"

    """
    circuit_id = f"unmapped_tab_{tab_number}"

    # Verify the circuit exists in the panel data
    if circuit_id not in span_panel.circuits:
        _LOGGER.debug("Unmapped circuit %s not found in circuits list", circuit_id)
        return None

    result_entity_id = construct_unmapped_entity_id(span_panel, circuit_id, suffix, device_name)
    _LOGGER.debug("Generated unmapped entity ID: %s", result_entity_id)
    return result_entity_id


def construct_unmapped_circuit_id(circuit_number: int | str) -> str:
    """Construct circuit ID for unmapped circuits.

    This returns just the circuit ID part (e.g., "unmapped_tab_30"), not a full entity ID.
    Used for API circuit references and internal circuit identification.

    Args:
        circuit_number: The tab number (e.g., 30, 32)

    Returns:
        Circuit ID string like "unmapped_tab_30"

    Examples:
        construct_unmapped_circuit_id(30) -> "unmapped_tab_30"
        construct_unmapped_circuit_id(32) -> "unmapped_tab_32"

    """
    return f"unmapped_tab_{circuit_number}"


__all__ = [
    # Core entity ID construction
    "construct_entity_id",
    "construct_panel_entity_id",
    "construct_panel_synthetic_entity_id",
    "construct_single_circuit_entity_id",
    "construct_multi_circuit_entity_id",
    # Voltage-specific constructors
    "construct_240v_synthetic_entity_id",
    "construct_120v_synthetic_entity_id",
    # Unmapped circuit helpers
    "construct_unmapped_entity_id",
    "get_unmapped_circuit_entity_id",
    "construct_unmapped_circuit_id",
    # Circuit helpers
    "get_circuit_number",
]
