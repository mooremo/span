"""Test authentication utilities.

Tests for Sub-Phase 4.3.3: Extract Authentication Flows
Validates the authentication.py module that extracts auth logic from config_flow.py.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.span_panel.config_flow_utils.authentication import (
    AuthResult,
    authenticate_via_proximity,
    authenticate_via_token,
)
from custom_components.span_panel.span_panel_hardware_status import SpanPanelHardwareStatus


@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_client():
    """Create a mock SpanPanelClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_status_response_new_firmware():
    """Create mock status response for new firmware (has proximity_proven field)."""
    response = MagicMock()
    response.to_dict.return_value = {
        "software": {
            "firmwareVersion": "r202342",
            "updateStatus": "idle",
            "env": "prod",
        },
        "system": {
            "manufacturer": "Span",
            "serial": "TEST123",
            "model": "Panel",
            "doorState": "CLOSED",
            "uptime": 12345,
            "proximityProven": True,
        },
        "network": {
            "eth0Link": True,
            "wlanLink": False,
            "wwanLink": False,
        },
    }
    return response


@pytest.fixture
def mock_status_response_old_firmware():
    """Create mock status response for old firmware (no proximity_proven field)."""
    response = MagicMock()
    response.to_dict.return_value = {
        "software": {
            "firmwareVersion": "r202300",
            "updateStatus": "idle",
            "env": "prod",
        },
        "system": {
            "manufacturer": "Span",
            "serial": "TEST123",
            "model": "Panel",
            "doorState": "CLOSED",
            "uptime": 12345,
            "remainingAuthUnlockButtonPresses": 0,
        },
        "network": {
            "eth0Link": True,
            "wlanLink": False,
            "wwanLink": False,
        },
    }
    return response


@pytest.fixture
def mock_auth_response():
    """Create mock authentication response."""
    response = MagicMock()
    response.access_token = "test_token_12345"
    return response


# ===== Tests for AuthResult dataclass =====


def test_auth_result_success():
    """Test AuthResult with successful authentication."""
    result = AuthResult(success=True, access_token="test_token")

    assert result.success is True
    assert result.access_token == "test_token"
    assert result.error_reason is None
    assert result.requires_retry is False


def test_auth_result_failure():
    """Test AuthResult with failed authentication."""
    result = AuthResult(success=False, error_reason="invalid_token")

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "invalid_token"
    assert result.requires_retry is False


def test_auth_result_requires_retry():
    """Test AuthResult when retry is needed."""
    result = AuthResult(
        success=False,
        requires_retry=True,
        error_reason="button_not_pressed"
    )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "button_not_pressed"
    assert result.requires_retry is True


# ===== Tests for authenticate_via_proximity =====


@pytest.mark.asyncio
async def test_proximity_auth_success_new_firmware(
    mock_hass, mock_client, mock_status_response_new_firmware, mock_auth_response
):
    """Test successful proximity authentication with new firmware."""
    mock_client.get_status.return_value = mock_status_response_new_firmware
    mock_client.authenticate.return_value = mock_auth_response

    with patch(
        "custom_components.span_panel.config_flow_utils.authentication.validate_auth_token",
        return_value=True
    ):
        result = await authenticate_via_proximity(
            hass=mock_hass,
            client=mock_client,
            host="192.168.1.100",
            use_ssl=True,
        )

    assert result.success is True
    assert result.access_token == "test_token_12345"
    assert result.error_reason is None
    assert result.requires_retry is False

    # Verify client methods called
    mock_client.get_status.assert_called_once()
    mock_client.authenticate.assert_called_once()


@pytest.mark.asyncio
async def test_proximity_auth_success_old_firmware(
    mock_hass, mock_client, mock_status_response_old_firmware, mock_auth_response
):
    """Test successful proximity authentication with old firmware."""
    mock_client.get_status.return_value = mock_status_response_old_firmware
    mock_client.authenticate.return_value = mock_auth_response

    with patch(
        "custom_components.span_panel.config_flow_utils.authentication.validate_auth_token",
        return_value=True
    ):
        result = await authenticate_via_proximity(
            hass=mock_hass,
            client=mock_client,
            host="192.168.1.100",
            use_ssl=False,
        )

    assert result.success is True
    assert result.access_token == "test_token_12345"
    assert result.error_reason is None
    assert result.requires_retry is False


@pytest.mark.asyncio
async def test_proximity_auth_button_not_pressed_new_firmware(
    mock_hass, mock_client
):
    """Test proximity auth when button not pressed (new firmware)."""
    response = MagicMock()
    response.to_dict.return_value = {
        "software": {
            "firmwareVersion": "r202342",
            "updateStatus": "idle",
            "env": "prod",
        },
        "system": {
            "manufacturer": "Span",
            "serial": "TEST123",
            "model": "Panel",
            "doorState": "CLOSED",
            "uptime": 12345,
            "proximityProven": False,
        },
        "network": {
            "eth0Link": True,
            "wlanLink": False,
            "wwanLink": False,
        },
    }
    mock_client.get_status.return_value = response

    result = await authenticate_via_proximity(
        hass=mock_hass,
        client=mock_client,
        host="192.168.1.100",
        use_ssl=True,
    )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "proximity_not_proven"
    assert result.requires_retry is True

    # Should not attempt authentication
    mock_client.authenticate.assert_not_called()


@pytest.mark.asyncio
async def test_proximity_auth_button_not_pressed_old_firmware(
    mock_hass, mock_client
):
    """Test proximity auth when button not pressed (old firmware)."""
    response = MagicMock()
    response.to_dict.return_value = {
        "software": {
            "firmwareVersion": "r202300",
            "updateStatus": "idle",
            "env": "prod",
        },
        "system": {
            "manufacturer": "Span",
            "serial": "TEST123",
            "model": "Panel",
            "doorState": "CLOSED",
            "uptime": 12345,
            "remainingAuthUnlockButtonPresses": 3,
        },
        "network": {
            "eth0Link": True,
            "wlanLink": False,
            "wwanLink": False,
        },
    }
    mock_client.get_status.return_value = response

    result = await authenticate_via_proximity(
        hass=mock_hass,
        client=mock_client,
        host="192.168.1.100",
        use_ssl=True,
    )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "button_not_pressed"
    assert result.requires_retry is True

    # Should not attempt authentication
    mock_client.authenticate.assert_not_called()


@pytest.mark.asyncio
async def test_proximity_auth_host_not_set(
    mock_hass, mock_client, mock_status_response_new_firmware
):
    """Test proximity auth with missing host."""
    mock_client.get_status.return_value = mock_status_response_new_firmware

    result = await authenticate_via_proximity(
        hass=mock_hass,
        client=mock_client,
        host="",  # Empty host
        use_ssl=True,
    )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "host_not_set"
    assert result.requires_retry is False

    # Should not attempt authentication
    mock_client.authenticate.assert_not_called()


@pytest.mark.asyncio
async def test_proximity_auth_token_validation_fails(
    mock_hass, mock_client, mock_status_response_new_firmware, mock_auth_response
):
    """Test proximity auth when token validation fails."""
    mock_client.get_status.return_value = mock_status_response_new_firmware
    mock_client.authenticate.return_value = mock_auth_response

    with patch(
        "custom_components.span_panel.config_flow_utils.authentication.validate_auth_token",
        return_value=False  # Validation fails
    ):
        result = await authenticate_via_proximity(
            hass=mock_hass,
            client=mock_client,
            host="192.168.1.100",
            use_ssl=True,
        )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "invalid_access_token"
    assert result.requires_retry is False


@pytest.mark.asyncio
async def test_proximity_auth_exception_handling(mock_hass, mock_client):
    """Test proximity auth exception handling."""
    mock_client.get_status.side_effect = Exception("Connection error")

    result = await authenticate_via_proximity(
        hass=mock_hass,
        client=mock_client,
        host="192.168.1.100",
        use_ssl=True,
    )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "auth_failed"
    assert result.requires_retry is False


@pytest.mark.asyncio
async def test_proximity_auth_none_access_token(
    mock_hass, mock_client, mock_status_response_new_firmware
):
    """Test proximity auth when authenticate returns None access_token."""
    mock_client.get_status.return_value = mock_status_response_new_firmware

    response = MagicMock()
    response.access_token = None
    mock_client.authenticate.return_value = response

    result = await authenticate_via_proximity(
        hass=mock_hass,
        client=mock_client,
        host="192.168.1.100",
        use_ssl=True,
    )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "invalid_access_token"
    assert result.requires_retry is False


# ===== Tests for authenticate_via_token =====


@pytest.mark.asyncio
async def test_token_auth_success(mock_hass):
    """Test successful token authentication."""
    with patch(
        "custom_components.span_panel.config_flow_utils.authentication.validate_auth_token",
        return_value=True
    ):
        result = await authenticate_via_token(
            hass=mock_hass,
            host="192.168.1.100",
            access_token="valid_token_123",
            use_ssl=True,
        )

    assert result.success is True
    assert result.access_token == "valid_token_123"
    assert result.error_reason is None
    assert result.requires_retry is False


@pytest.mark.asyncio
async def test_token_auth_with_whitespace(mock_hass):
    """Test token authentication with whitespace in token."""
    with patch(
        "custom_components.span_panel.config_flow_utils.authentication.validate_auth_token",
        return_value=True
    ):
        result = await authenticate_via_token(
            hass=mock_hass,
            host="192.168.1.100",
            access_token="  valid_token_123  ",
            use_ssl=False,
        )

    assert result.success is True
    assert result.access_token == "valid_token_123"  # Whitespace stripped
    assert result.error_reason is None
    assert result.requires_retry is False


@pytest.mark.asyncio
async def test_token_auth_host_not_set(mock_hass):
    """Test token auth with missing host."""
    result = await authenticate_via_token(
        hass=mock_hass,
        host="",  # Empty host
        access_token="token_123",
        use_ssl=True,
    )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "host_not_set"
    assert result.requires_retry is False


@pytest.mark.asyncio
async def test_token_auth_missing_token(mock_hass):
    """Test token auth with missing token."""
    result = await authenticate_via_token(
        hass=mock_hass,
        host="192.168.1.100",
        access_token="",  # Empty token
        use_ssl=True,
    )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "missing_access_token"
    assert result.requires_retry is False


@pytest.mark.asyncio
async def test_token_auth_whitespace_only_token(mock_hass):
    """Test token auth with whitespace-only token."""
    result = await authenticate_via_token(
        hass=mock_hass,
        host="192.168.1.100",
        access_token="   ",  # Whitespace only
        use_ssl=True,
    )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "missing_access_token"
    assert result.requires_retry is False


@pytest.mark.asyncio
async def test_token_auth_invalid_token(mock_hass):
    """Test token auth with invalid token."""
    with patch(
        "custom_components.span_panel.config_flow_utils.authentication.validate_auth_token",
        return_value=False  # Invalid token
    ):
        result = await authenticate_via_token(
            hass=mock_hass,
            host="192.168.1.100",
            access_token="invalid_token",
            use_ssl=True,
        )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "invalid_access_token"
    assert result.requires_retry is False


@pytest.mark.asyncio
async def test_token_auth_exception_handling(mock_hass):
    """Test token auth exception handling."""
    with patch(
        "custom_components.span_panel.config_flow_utils.authentication.validate_auth_token",
        side_effect=Exception("Validation error")
    ):
        result = await authenticate_via_token(
            hass=mock_hass,
            host="192.168.1.100",
            access_token="token_123",
            use_ssl=True,
        )

    assert result.success is False
    assert result.access_token is None
    assert result.error_reason == "auth_failed"
    assert result.requires_retry is False
