"""Test migration retry logic and edge cases.

Tests for Phase 1.5: Fix Migration Flag Clearing
Verifies that migration retry logic works correctly with attempt counting,
flag management, and proper error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from custom_components.span_panel.const import USE_CIRCUIT_NUMBERS, USE_DEVICE_PREFIX


@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


def create_mock_coordinator(hass: Any, config_entry: Any) -> Any:
    """Create a mock coordinator for testing."""
    from custom_components.span_panel.coordinator import SpanPanelCoordinator

    mock_span_panel = MagicMock()
    mock_span_panel.status.serial_number = "TEST123"

    coordinator = SpanPanelCoordinator(hass, mock_span_panel, config_entry)
    return coordinator


@pytest.mark.asyncio
async def test_legacy_migration_success_clears_flags(hass: Any):
    """Test successful legacy migration clears all flags and schedules reload."""
    # Create config entry with migration flag
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.options = {
        "pending_legacy_migration": True,
        USE_CIRCUIT_NUMBERS: True,
        USE_DEVICE_PREFIX: True,
    }

    coordinator = create_mock_coordinator(hass, mock_config_entry)

    # Mock successful migration
    coordinator.migrate_entity_ids = AsyncMock(return_value=True)

    # Track config entry updates
    updates = []

    def track_update(entry, **kwargs):
        if "options" in kwargs:
            updates.append(dict(kwargs["options"]))

    hass.config_entries.async_update_entry = track_update
    hass.config_entries.async_reload = AsyncMock()

    # Execute migration
    await coordinator._handle_pending_legacy_migration()

    # Verify flags were cleared
    assert len(updates) == 1
    assert "pending_legacy_migration" not in updates[0]
    assert "legacy_migration_attempts" not in updates[0]

    # Verify reload was scheduled
    assert hass.config_entries.async_reload.called


@pytest.mark.asyncio
async def test_legacy_migration_failure_preserves_flag(hass: Any):
    """Test failed migration preserves flag and increments attempt counter."""
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.options = {
        "pending_legacy_migration": True,
        USE_CIRCUIT_NUMBERS: True,
        USE_DEVICE_PREFIX: True,
    }

    coordinator = create_mock_coordinator(hass, mock_config_entry)

    # Mock failed migration
    coordinator.migrate_entity_ids = AsyncMock(return_value=False)

    # Track config entry updates
    updates = []

    def track_update(entry, **kwargs):
        if "options" in kwargs:
            updates.append(dict(kwargs["options"]))

    hass.config_entries.async_update_entry = track_update

    # Execute migration
    await coordinator._handle_pending_legacy_migration()

    # Verify flag was NOT cleared
    assert len(updates) == 1
    assert "pending_legacy_migration" in updates[0]
    assert updates[0]["pending_legacy_migration"] is True

    # Verify attempt counter was incremented
    assert updates[0]["legacy_migration_attempts"] == 1


@pytest.mark.asyncio
async def test_legacy_migration_max_attempts_gives_up(hass: Any):
    """Test migration gives up after 3 failed attempts."""
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.options = {
        "pending_legacy_migration": True,
        "legacy_migration_attempts": 3,  # Already at max
        USE_CIRCUIT_NUMBERS: True,
        USE_DEVICE_PREFIX: True,
    }

    coordinator = create_mock_coordinator(hass, mock_config_entry)

    # Mock failed migration (shouldn't be called)
    coordinator.migrate_entity_ids = AsyncMock(return_value=False)

    # Track config entry updates
    updates = []

    def track_update(entry, **kwargs):
        if "options" in kwargs:
            updates.append(dict(kwargs["options"]))

    hass.config_entries.async_update_entry = track_update

    # Execute migration
    await coordinator._handle_pending_legacy_migration()

    # Verify migration was NOT attempted
    assert not coordinator.migrate_entity_ids.called

    # Verify flags were cleared (giving up)
    assert len(updates) == 1
    assert "pending_legacy_migration" not in updates[0]
    assert "legacy_migration_attempts" not in updates[0]


@pytest.mark.asyncio
async def test_legacy_migration_exception_increments_counter(hass: Any):
    """Test migration exception increments attempt counter."""
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.options = {
        "pending_legacy_migration": True,
        USE_CIRCUIT_NUMBERS: True,
        USE_DEVICE_PREFIX: True,
    }

    coordinator = create_mock_coordinator(hass, mock_config_entry)

    # Mock migration exception
    coordinator.migrate_entity_ids = AsyncMock(
        side_effect=Exception("Test migration error")
    )

    # Track config entry updates
    updates = []

    def track_update(entry, **kwargs):
        if "options" in kwargs:
            updates.append(dict(kwargs["options"]))

    hass.config_entries.async_update_entry = track_update

    # Execute migration (should not raise)
    await coordinator._handle_pending_legacy_migration()

    # Verify flag was preserved
    assert len(updates) == 1
    assert "pending_legacy_migration" in updates[0]

    # Verify attempt counter was incremented
    assert updates[0]["legacy_migration_attempts"] == 1


@pytest.mark.asyncio
async def test_naming_migration_success_clears_all_flags(hass: Any):
    """Test successful naming migration clears all flags including old flags."""
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.options = {
        "pending_naming_migration": True,
        "old_use_circuit_numbers": False,
        "old_use_device_prefix": False,
        USE_CIRCUIT_NUMBERS: True,
        USE_DEVICE_PREFIX: True,
    }

    coordinator = create_mock_coordinator(hass, mock_config_entry)

    # Mock successful migration
    coordinator._migration_manager = MagicMock()
    coordinator._migration_manager.migrate_entity_ids = AsyncMock(return_value=True)

    # Track config entry updates
    updates = []

    def track_update(entry, **kwargs):
        if "options" in kwargs:
            updates.append(dict(kwargs["options"]))

    hass.config_entries.async_update_entry = track_update
    hass.config_entries.async_reload = AsyncMock()

    # Execute migration
    await coordinator._handle_pending_naming_migration()

    # Verify all flags were cleared
    assert len(updates) == 1
    assert "pending_naming_migration" not in updates[0]
    assert "naming_migration_attempts" not in updates[0]
    assert "old_use_circuit_numbers" not in updates[0]
    assert "old_use_device_prefix" not in updates[0]

    # Verify reload was scheduled
    assert hass.config_entries.async_reload.called


@pytest.mark.asyncio
async def test_naming_migration_retry_increments_attempt(hass: Any):
    """Test failed naming migration increments attempt counter."""
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.options = {
        "pending_naming_migration": True,
        "old_use_circuit_numbers": False,
        "old_use_device_prefix": False,
        "naming_migration_attempts": 1,  # Second attempt
        USE_CIRCUIT_NUMBERS: True,
        USE_DEVICE_PREFIX: True,
    }

    coordinator = create_mock_coordinator(hass, mock_config_entry)

    # Mock failed migration
    coordinator._migration_manager = MagicMock()
    coordinator._migration_manager.migrate_entity_ids = AsyncMock(return_value=False)

    # Track config entry updates
    updates = []

    def track_update(entry, **kwargs):
        if "options" in kwargs:
            updates.append(dict(kwargs["options"]))

    hass.config_entries.async_update_entry = track_update

    # Execute migration
    await coordinator._handle_pending_naming_migration()

    # Verify flag preserved
    assert len(updates) == 1
    assert "pending_naming_migration" in updates[0]

    # Verify attempt counter incremented from 1 to 2
    assert updates[0]["naming_migration_attempts"] == 2


@pytest.mark.asyncio
async def test_naming_migration_max_attempts_clears_old_flags(hass: Any):
    """Test naming migration clears old flags after max attempts."""
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.options = {
        "pending_naming_migration": True,
        "old_use_circuit_numbers": False,
        "old_use_device_prefix": False,
        "naming_migration_attempts": 3,  # At max
        USE_CIRCUIT_NUMBERS: True,
        USE_DEVICE_PREFIX: True,
    }

    coordinator = create_mock_coordinator(hass, mock_config_entry)

    # Mock migration (shouldn't be called)
    coordinator._migration_manager = MagicMock()
    coordinator._migration_manager.migrate_entity_ids = AsyncMock(return_value=False)

    # Track config entry updates
    updates = []

    def track_update(entry, **kwargs):
        if "options" in kwargs:
            updates.append(dict(kwargs["options"]))

    hass.config_entries.async_update_entry = track_update

    # Execute migration
    await coordinator._handle_pending_naming_migration()

    # Verify migration was NOT attempted
    assert not coordinator._migration_manager.migrate_entity_ids.called

    # Verify all flags cleared including old flags
    assert len(updates) == 1
    assert "pending_naming_migration" not in updates[0]
    assert "naming_migration_attempts" not in updates[0]
    assert "old_use_circuit_numbers" not in updates[0]
    assert "old_use_device_prefix" not in updates[0]


@pytest.mark.asyncio
async def test_migration_attempt_counter_starts_at_zero(hass: Any):
    """Test migration starts with attempt counter at 0."""
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.options = {
        "pending_legacy_migration": True,
        # No attempt counter - should default to 0
        USE_CIRCUIT_NUMBERS: True,
        USE_DEVICE_PREFIX: True,
    }

    coordinator = create_mock_coordinator(hass, mock_config_entry)

    # Mock failed migration
    coordinator.migrate_entity_ids = AsyncMock(return_value=False)

    # Track config entry updates
    updates = []

    def track_update(entry, **kwargs):
        if "options" in kwargs:
            updates.append(dict(kwargs["options"]))

    hass.config_entries.async_update_entry = track_update

    # Execute migration
    await coordinator._handle_pending_legacy_migration()

    # Verify attempt counter set to 1 (first attempt)
    assert len(updates) == 1
    assert updates[0]["legacy_migration_attempts"] == 1
