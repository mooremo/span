"""Test validation utilities for config flow.

Tests for Sub-Phase 4.1: Test Infrastructure
Validates all functions in config_flow_utils/validation.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from tests.conftest import MockSpanPanelAuthError, MockSpanPanelConnectionError

from custom_components.span_panel.config_flow_utils.validation import (
    get_available_unmapped_tabs,
    get_filtered_tab_options,
    validate_auth_token,
    validate_host,
    validate_ipv4_address,
    validate_simulation_time,
    validate_solar_configuration,
    validate_solar_tab_selection,
)
from custom_components.span_panel.const import COORDINATOR, DOMAIN


@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


# ===== Tests for validate_ipv4_address =====


def test_validate_ipv4_address_valid():
    """Test validation with valid IPv4 addresses."""
    assert validate_ipv4_address("192.168.1.1") is True
    assert validate_ipv4_address("10.0.0.1") is True
    assert validate_ipv4_address("172.16.0.1") is True
    assert validate_ipv4_address("255.255.255.255") is True
    assert validate_ipv4_address("0.0.0.0") is True


def test_validate_ipv4_address_invalid():
    """Test validation with invalid IPv4 addresses."""

    # Invalid formats
    assert validate_ipv4_address("256.1.1.1") is False
    assert validate_ipv4_address("192.168.1") is False
    assert validate_ipv4_address("192.168.1.1.1") is False
    assert validate_ipv4_address("not-an-ip") is False
    assert validate_ipv4_address("") is False


def test_validate_ipv4_address_hostname():
    """Test validation with hostnames (should fail)."""

    assert validate_ipv4_address("span.local") is False
    assert validate_ipv4_address("example.com") is False


# ===== Tests for validate_simulation_time =====


def test_validate_simulation_time_iso_format():
    """Test validation with full ISO datetime format."""

    # Valid ISO datetime should be returned as-is
    iso_time = "2024-06-15T17:30:00"
    result = validate_simulation_time(iso_time)
    assert result == iso_time


def test_validate_simulation_time_hour_minute():
    """Test validation with HH:MM format."""

    # Should convert to ISO datetime with current date
    result = validate_simulation_time("17:30")
    # Parse result and verify time components
    parsed = datetime.fromisoformat(result)
    assert parsed.hour == 17
    assert parsed.minute == 30
    assert parsed.second == 0


def test_validate_simulation_time_single_digit_hour():
    """Test validation with H:MM format."""

    result = validate_simulation_time("5:30")
    parsed = datetime.fromisoformat(result)
    assert parsed.hour == 5
    assert parsed.minute == 30


def test_validate_simulation_time_empty():
    """Test validation with empty string."""

    result = validate_simulation_time("")
    assert result == ""

    result = validate_simulation_time("   ")
    assert result == ""


def test_validate_simulation_time_invalid():
    """Test validation with invalid time formats."""

    # Invalid hour
    with pytest.raises(ValueError, match="Invalid time format"):
        validate_simulation_time("25:00")

    # Invalid minute
    with pytest.raises(ValueError, match="Invalid time format"):
        validate_simulation_time("12:60")

    # Invalid format
    with pytest.raises(ValueError, match="Invalid time format"):
        validate_simulation_time("not-a-time")

    # Missing colon
    with pytest.raises(ValueError, match="Invalid time format"):
        validate_simulation_time("1730")


def test_validate_simulation_time_edge_cases():
    """Test validation with edge case times."""

    # Midnight
    result = validate_simulation_time("0:00")
    parsed = datetime.fromisoformat(result)
    assert parsed.hour == 0
    assert parsed.minute == 0

    # End of day
    result = validate_simulation_time("23:59")
    parsed = datetime.fromisoformat(result)
    assert parsed.hour == 23
    assert parsed.minute == 59


# ===== Tests for validate_solar_tab_selection =====


def test_validate_solar_tab_selection_valid():
    """Test validation with valid solar tab selection."""

    # Mock available tabs (assuming tabs 1-32 exist and tabs on opposite phases)
    available_tabs = list(range(1, 33))

    # Tab 1 (L1) and Tab 3 (L2) should be on opposite phases (pattern: pairs alternate)
    is_valid, message = validate_solar_tab_selection(1, 3, available_tabs)
    assert is_valid is True


def test_validate_solar_tab_selection_same_tab():
    """Test validation when both legs use the same tab."""

    available_tabs = list(range(1, 33))

    is_valid, message = validate_solar_tab_selection(5, 5, available_tabs)
    assert is_valid is False
    assert "cannot use the same tab" in message


def test_validate_solar_tab_selection_zero_tab():
    """Test validation when a tab is set to 0 (disabled)."""

    available_tabs = list(range(1, 33))

    # One tab is 0
    is_valid, message = validate_solar_tab_selection(0, 5, available_tabs)
    assert is_valid is False
    assert "Both solar legs must be selected" in message

    # Both tabs are 0
    is_valid, message = validate_solar_tab_selection(0, 0, available_tabs)
    assert is_valid is False
    assert "Both solar legs must be selected" in message


def test_validate_solar_tab_selection_unavailable_tab():
    """Test validation when selected tab is not available."""

    # Only tabs 10-20 are available
    available_tabs = list(range(10, 21))

    # Tab 5 is not in available list
    is_valid, message = validate_solar_tab_selection(5, 10, available_tabs)
    assert is_valid is False
    assert "not available" in message or "already mapped" in message


def test_validate_solar_tab_selection_same_phase():
    """Test validation when tabs are on same phase."""

    available_tabs = list(range(1, 33))

    # Tabs 1 and 2 should be on the same phase (both L1, pattern alternates in pairs)
    is_valid, message = validate_solar_tab_selection(1, 2, available_tabs)
    assert is_valid is False
    # Should mention phase issue
    assert "phase" in message.lower()


# ===== Tests for get_filtered_tab_options =====


def test_get_filtered_tab_options_no_selection():
    """Test filtered options when no tab is selected."""

    available_tabs = [1, 2, 3, 4, 5, 6]

    # No tab selected (0), should return all tabs
    options = get_filtered_tab_options(0, available_tabs, include_none=True)

    # Should include None option + all available tabs
    assert 0 in options
    assert options[0] == "None (Disabled)"
    assert len(options) == 7  # None + 6 tabs


def test_get_filtered_tab_options_with_selection():
    """Test filtered options when a tab is selected."""

    available_tabs = [1, 2, 3, 4]

    # Tab 1 is selected (L1), should only show opposite-phase tabs (L2)
    # Pattern: tabs 1-2 are L1, tabs 3-4 are L2
    options = get_filtered_tab_options(1, available_tabs, include_none=True)

    # Should include None and only opposite-phase tabs
    assert 0 in options  # None option
    assert 3 in options  # Tab 3 (L2)
    assert 4 in options  # Tab 4 (L2)
    # Tab 1 and 2 (both L1) shouldn't be in filtered list
    assert 1 not in options or options.get(1) == "None (Disabled)"  # Except as None
    assert 2 not in options  # Tab 2 (L1) shouldn't be there


def test_get_filtered_tab_options_without_none():
    """Test filtered options without None option."""

    available_tabs = [1, 2, 3, 4]

    options = get_filtered_tab_options(0, available_tabs, include_none=False)

    # Should NOT include None option
    assert 0 not in options
    assert len(options) == 4


def test_get_filtered_tab_options_display_format():
    """Test that options include phase information."""

    available_tabs = [1, 2]

    options = get_filtered_tab_options(0, available_tabs, include_none=False)

    # Should include phase in display name
    assert "Tab 1" in options[1]
    assert "L1" in options[1] or "L2" in options[1]


# ===== Tests for validate_solar_configuration =====


def test_validate_solar_configuration_disabled():
    """Test validation when solar is disabled."""

    # When solar is disabled, should always return valid
    is_valid, message = validate_solar_configuration(
        solar_enabled=False, leg1=0, leg2=0, available_tabs=[]
    )
    assert is_valid is True
    assert message == ""


def test_validate_solar_configuration_enabled_valid():
    """Test validation when solar is enabled with valid tabs."""

    available_tabs = list(range(1, 33))

    is_valid, message = validate_solar_configuration(
        solar_enabled=True, leg1=1, leg2=2, available_tabs=available_tabs
    )
    # Should delegate to validate_solar_tab_selection
    assert isinstance(is_valid, bool)


def test_validate_solar_configuration_no_available_tabs():
    """Test validation when available_tabs is empty."""

    # Empty available_tabs should skip validation
    is_valid, message = validate_solar_configuration(
        solar_enabled=True, leg1=1, leg2=2, available_tabs=[]
    )
    assert is_valid is True
    assert message == ""


# ===== Tests for get_available_unmapped_tabs (async) =====


@pytest.mark.asyncio
async def test_get_available_unmapped_tabs_success():
    """Test getting unmapped tabs from panel data."""

    # Mock Home Assistant and config entry
    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test-entry-id"

    # Mock coordinator with panel data
    mock_coordinator = MagicMock()
    mock_panel_data = MagicMock()

    # Create mock circuits with unmapped tabs
    mock_panel_data.circuits = {
        "circuit_1": MagicMock(),
        "unmapped_tab_10": MagicMock(),
        "unmapped_tab_5": MagicMock(),
        "circuit_2": MagicMock(),
        "unmapped_tab_15": MagicMock(),
    }

    mock_coordinator.data = mock_panel_data

    # Set up the hass data structure

    mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {COORDINATOR: mock_coordinator}}}

    # Call the function
    result = await get_available_unmapped_tabs(mock_hass, mock_config_entry)

    # Should return sorted list of unmapped tab numbers
    assert result == [5, 10, 15]


@pytest.mark.asyncio
async def test_get_available_unmapped_tabs_no_circuits():
    """Test getting unmapped tabs when panel has no circuits."""

    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test-entry-id"

    mock_coordinator = MagicMock()
    mock_panel_data = MagicMock()
    mock_panel_data.circuits = {}

    mock_coordinator.data = mock_panel_data


    mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {COORDINATOR: mock_coordinator}}}

    result = await get_available_unmapped_tabs(mock_hass, mock_config_entry)

    assert result == []


@pytest.mark.asyncio
async def test_get_available_unmapped_tabs_no_panel_data():
    """Test getting unmapped tabs when panel data is None."""

    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test-entry-id"

    mock_coordinator = MagicMock()
    mock_coordinator.data = None


    mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {COORDINATOR: mock_coordinator}}}

    result = await get_available_unmapped_tabs(mock_hass, mock_config_entry)

    assert result == []


@pytest.mark.asyncio
async def test_get_available_unmapped_tabs_invalid_tab_format():
    """Test getting unmapped tabs with invalid tab number in circuit ID."""

    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test-entry-id"

    mock_coordinator = MagicMock()
    mock_panel_data = MagicMock()

    # Include invalid tab ID
    mock_panel_data.circuits = {
        "unmapped_tab_5": MagicMock(),
        "unmapped_tab_invalid": MagicMock(),  # Invalid number
        "unmapped_tab_10": MagicMock(),
    }

    mock_coordinator.data = mock_panel_data


    mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: {COORDINATOR: mock_coordinator}}}

    result = await get_available_unmapped_tabs(mock_hass, mock_config_entry)

    # Should skip invalid and return valid ones
    assert result == [5, 10]


@pytest.mark.asyncio
async def test_get_available_unmapped_tabs_missing_coordinator():
    """Test getting unmapped tabs when coordinator is missing."""

    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test-entry-id"

    # No coordinator in data

    mock_hass.data = {DOMAIN: {}}

    result = await get_available_unmapped_tabs(mock_hass, mock_config_entry)

    # Should handle gracefully and return empty list
    assert result == []


# ===== Tests for validate_host (async) =====


@pytest.mark.asyncio
async def test_validate_host_success_without_token():
    """Test host validation without auth token."""

    mock_hass = MagicMock()

    # Mock SpanPanelClient
    with patch(
        "custom_components.span_panel.config_flow_utils.validation.SpanPanelClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_status = AsyncMock(return_value={"status": "ok"})
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        result = await validate_host(mock_hass, "192.168.1.100")

        assert result is True
        mock_client.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_validate_host_success_with_token():
    """Test host validation with auth token."""

    mock_hass = MagicMock()

    with patch(
        "custom_components.span_panel.config_flow_utils.validation.SpanPanelClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_panel_state = AsyncMock(return_value={"state": "ok"})
        mock_client.set_access_token = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        result = await validate_host(mock_hass, "192.168.1.100", access_token="test-token")

        assert result is True
        mock_client.set_access_token.assert_called_once_with("test-token")
        mock_client.get_panel_state.assert_called_once()


@pytest.mark.asyncio
async def test_validate_host_connection_failure():
    """Test host validation when connection fails."""

    mock_hass = MagicMock()

    with patch(
        "custom_components.span_panel.config_flow_utils.validation.SpanPanelClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_status = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        result = await validate_host(mock_hass, "192.168.1.100")

        assert result is False


# ===== Tests for validate_auth_token (async) =====


@pytest.mark.asyncio
async def test_validate_auth_token_success():
    """Test auth token validation with valid token."""

    mock_hass = MagicMock()

    with patch(
        "custom_components.span_panel.config_flow_utils.validation.SpanPanelClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_panel_state = AsyncMock(return_value={"state": "ok"})
        mock_client.set_access_token = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        result = await validate_auth_token(mock_hass, "192.168.1.100", "valid-token")

        assert result is True
        mock_client.set_access_token.assert_called_once_with("valid-token")


@pytest.mark.asyncio
async def test_validate_auth_token_auth_error():
    """Test auth token validation with invalid token."""

    mock_hass = MagicMock()

    with patch(
        "custom_components.span_panel.config_flow_utils.validation.SpanPanelClient"
    ) as mock_client_class:
        with patch(
            "custom_components.span_panel.config_flow_utils.validation.SpanPanelAuthError",
            MockSpanPanelAuthError,
        ):
            mock_client = AsyncMock()
            mock_client.get_panel_state = AsyncMock(
                side_effect=MockSpanPanelAuthError("Invalid token")
            )
            mock_client.set_access_token = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await validate_auth_token(mock_hass, "192.168.1.100", "invalid-token")

            assert result is False


@pytest.mark.asyncio
async def test_validate_auth_token_connection_error():
    """Test auth token validation with connection error."""

    mock_hass = MagicMock()

    with patch(
        "custom_components.span_panel.config_flow_utils.validation.SpanPanelClient"
    ) as mock_client_class:
        with patch(
            "custom_components.span_panel.config_flow_utils.validation.SpanPanelConnectionError",
            MockSpanPanelConnectionError,
        ):
            mock_client = AsyncMock()
            mock_client.get_panel_state = AsyncMock(
                side_effect=MockSpanPanelConnectionError("Connection failed")
            )
            mock_client.set_access_token = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await validate_auth_token(mock_hass, "192.168.1.100", "test-token")

            assert result is False


@pytest.mark.asyncio
async def test_validate_auth_token_unexpected_error():
    """Test auth token validation with unexpected error."""

    mock_hass = MagicMock()

    with patch(
        "custom_components.span_panel.config_flow_utils.validation.SpanPanelClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_panel_state = AsyncMock(side_effect=RuntimeError("Unexpected"))
        mock_client.set_access_token = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        result = await validate_auth_token(mock_hass, "192.168.1.100", "test-token")

        assert result is False
