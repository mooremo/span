"""Authentication utilities for Span Panel config flow.

This module provides authentication methods for the Span Panel integration,
including proximity-based authentication and token-based authentication.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import uuid

from homeassistant.core import HomeAssistant
from span_panel_api import SpanPanelClient

from ..span_panel_hardware_status import SpanPanelHardwareStatus
from .validation import validate_auth_token

_LOGGER = logging.getLogger(__name__)


@dataclass
class AuthResult:
    """Result of authentication attempt.

    Attributes:
        success: Whether authentication was successful
        access_token: The access token if successful, None otherwise
        error_reason: Error reason code if failed, None otherwise
        requires_retry: Whether the user should retry (e.g., button not pressed yet)

    """

    success: bool
    access_token: str | None = None
    error_reason: str | None = None
    requires_retry: bool = False


async def authenticate_via_proximity(
    hass: HomeAssistant,
    client: SpanPanelClient,
    host: str,
    use_ssl: bool,
) -> AuthResult:
    """Authenticate using proof of proximity method.

    Guides user through physical button press authentication. The user must press
    the button on the physical panel to prove proximity before authentication
    can complete.

    Args:
        hass: Home Assistant instance
        client: SpanPanelClient instance (must be connected)
        host: Panel hostname or IP address
        use_ssl: Whether to use SSL for validation

    Returns:
        AuthResult with token on success or error reason on failure

    """
    try:
        # Get status to check proximity state
        status_response = await client.get_status()
        status_dict = status_response.to_dict()  # type: ignore[attr-defined]
        panel_status = SpanPanelHardwareStatus.from_dict(status_dict)

        # Check if running firmware newer or older than r202342
        if panel_status.proximity_proven is not None:
            # New firmware: check proximity_proven flag
            proximity_verified: bool = panel_status.proximity_proven
            if not proximity_verified:
                _LOGGER.debug("Proximity not yet proven (new firmware), user needs to press button")
                return AuthResult(
                    success=False,
                    requires_retry=True,
                    error_reason="proximity_not_proven",
                )
        else:
            # Old firmware: check remaining button presses
            remaining_presses: int = panel_status.remaining_auth_unlock_button_presses
            if remaining_presses != 0:
                _LOGGER.debug(
                    "Proximity not yet proven (old firmware), %d presses remaining",
                    remaining_presses,
                )
                return AuthResult(
                    success=False,
                    requires_retry=True,
                    error_reason="button_not_pressed",
                )

        # Proximity proven, request authentication token
        if not host:
            return AuthResult(success=False, error_reason="host_not_set")

        client_name = f"home-assistant-{uuid.uuid4()}"
        auth_response = await client.authenticate(
            client_name, "Home Assistant Local Span Integration"
        )
        access_token = auth_response.access_token

        # Validate the received token
        if access_token and await validate_auth_token(hass, host, access_token, use_ssl):
            _LOGGER.info("Proximity authentication successful")
            return AuthResult(success=True, access_token=access_token)
        else:
            _LOGGER.error("Proximity auth completed but token validation failed")
            return AuthResult(success=False, error_reason="invalid_access_token")

    except Exception as e:
        _LOGGER.error("Error during proximity authentication: %s", e, exc_info=True)
        return AuthResult(success=False, error_reason="auth_failed")


async def authenticate_via_token(
    hass: HomeAssistant,
    host: str,
    access_token: str,
    use_ssl: bool,
) -> AuthResult:
    """Authenticate using existing access token.

    Validates provided token against the panel by attempting to use it.

    Args:
        hass: Home Assistant instance
        host: Panel hostname or IP address
        access_token: Token to validate
        use_ssl: Whether to use SSL

    Returns:
        AuthResult with success status or error reason

    """
    if not host:
        return AuthResult(success=False, error_reason="host_not_set")

    if not access_token or not access_token.strip():
        return AuthResult(success=False, error_reason="missing_access_token")

    token = access_token.strip()

    try:
        # Validate the provided token
        if await validate_auth_token(hass, host, token, use_ssl):
            _LOGGER.info("Token authentication successful")
            return AuthResult(success=True, access_token=token)
        else:
            _LOGGER.warning("Token authentication failed - invalid token")
            return AuthResult(success=False, error_reason="invalid_access_token")

    except Exception as e:
        _LOGGER.error("Error during token authentication: %s", e, exc_info=True)
        return AuthResult(success=False, error_reason="auth_failed")
