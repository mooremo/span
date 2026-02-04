"""Test base service registration utilities.

Tests for Sub-Phase 4.2: Service Registration Consolidation
Validates the register_span_service() function that eliminates duplicate boilerplate.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch
import pytest
import voluptuous as vol

from homeassistant.core import SupportsResponse

from custom_components.span_panel.services.base import register_span_service

@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    return hass


@pytest.fixture
def sample_schema():
    """Create a sample voluptuous schema."""
    return vol.Schema({vol.Required("test_param"): str})


@pytest.fixture
async def sample_handler():
    """Create a sample async handler."""

    async def handler(call):
        return {"result": "success", "param": call.data.get("test_param")}

    return handler


# ===== Tests for register_span_service =====


@pytest.mark.asyncio
async def test_register_span_service_success(mock_hass, sample_schema, sample_handler):
    """Test successful service registration."""
    await register_span_service(
        hass=mock_hass,
        service_name="test_service",
        handler=sample_handler,
        schema=sample_schema,
        domain="span_panel",
    )

    # Verify service was registered
    mock_hass.services.async_register.assert_called_once_with(
        "span_panel",
        "test_service",
        sample_handler,
        schema=sample_schema,
        supports_response=SupportsResponse.OPTIONAL,
    )

    # Verify flag was set
    assert mock_hass.data["span_panel_test_service_registered"] is True


@pytest.mark.asyncio
async def test_register_span_service_already_registered(
    mock_hass, sample_schema, sample_handler
):
    """Test that duplicate registration is skipped."""
    # Set flag to indicate already registered
    mock_hass.data["span_panel_test_service_registered"] = True

    await register_span_service(
        hass=mock_hass,
        service_name="test_service",
        handler=sample_handler,
        schema=sample_schema,
        domain="span_panel",
    )

    # Verify service was NOT registered again
    mock_hass.services.async_register.assert_not_called()


@pytest.mark.asyncio
async def test_register_span_service_with_supports_response(
    mock_hass, sample_schema, sample_handler
):
    """Test registration with custom supports_response."""
    await register_span_service(
        hass=mock_hass,
        service_name="test_service",
        handler=sample_handler,
        schema=sample_schema,
        domain="span_panel",
        supports_response=SupportsResponse.ONLY,
    )

    # Verify supports_response was passed correctly
    mock_hass.services.async_register.assert_called_once()
    call_args = mock_hass.services.async_register.call_args
    assert call_args.kwargs["supports_response"] == SupportsResponse.ONLY


@pytest.mark.asyncio
async def test_register_span_service_registration_error(
    mock_hass, sample_schema, sample_handler
):
    """Test handling of registration errors."""
    # Make registration raise an exception
    mock_hass.services.async_register.side_effect = ValueError("Registration failed")

    # Should raise the exception
    with pytest.raises(ValueError, match="Registration failed"):
        await register_span_service(
            hass=mock_hass,
            service_name="test_service",
            handler=sample_handler,
            schema=sample_schema,
            domain="span_panel",
        )

    # Flag should NOT be set when registration fails
    assert "span_panel_test_service_registered" not in mock_hass.data


@pytest.mark.asyncio
async def test_register_span_service_concurrent_calls(mock_hass, sample_schema):
    """Test thread-safe registration with concurrent calls."""
    async def handler1(call):
        return {"handler": "1"}

    async def handler2(call):
        return {"handler": "2"}

    # Track registration calls
    registration_count = 0

    def track_registration(*args, **kwargs):
        nonlocal registration_count
        registration_count += 1

    mock_hass.services.async_register = MagicMock(side_effect=track_registration)

    # Call registration concurrently
    await asyncio.gather(
        register_span_service(
            hass=mock_hass,
            service_name="test_service",
            handler=handler1,
            schema=sample_schema,
            domain="span_panel",
        ),
        register_span_service(
            hass=mock_hass,
            service_name="test_service",
            handler=handler2,
            schema=sample_schema,
            domain="span_panel",
        ),
    )

    # Should only register once due to lock
    assert registration_count == 1
    assert mock_hass.data["span_panel_test_service_registered"] is True


@pytest.mark.asyncio
async def test_register_span_service_different_services(
    mock_hass, sample_schema, sample_handler
):
    """Test registering multiple different services."""
    # Register first service
    await register_span_service(
        hass=mock_hass,
        service_name="service_one",
        handler=sample_handler,
        schema=sample_schema,
        domain="span_panel",
    )

    # Register second service
    await register_span_service(
        hass=mock_hass,
        service_name="service_two",
        handler=sample_handler,
        schema=sample_schema,
        domain="span_panel",
    )

    # Both should be registered
    assert mock_hass.services.async_register.call_count == 2
    assert mock_hass.data["span_panel_service_one_registered"] is True
    assert mock_hass.data["span_panel_service_two_registered"] is True


@pytest.mark.asyncio
async def test_register_span_service_different_domains(
    mock_hass, sample_schema, sample_handler
):
    """Test registering services in different domains."""
    # Register in span_panel domain
    await register_span_service(
        hass=mock_hass,
        service_name="test_service",
        handler=sample_handler,
        schema=sample_schema,
        domain="span_panel",
    )

    # Register same service name in different domain
    await register_span_service(
        hass=mock_hass,
        service_name="test_service",
        handler=sample_handler,
        schema=sample_schema,
        domain="other_domain",
    )

    # Both should be registered (different domains)
    assert mock_hass.services.async_register.call_count == 2
    assert mock_hass.data["span_panel_test_service_registered"] is True
    assert mock_hass.data["other_domain_test_service_registered"] is True
