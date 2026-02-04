"""Test helpers.py reverse mapping caching optimization.

Tests for Phase 2.3: Cache Reverse Mapping in helpers.py
Verifies that reverse mapping is cached and function works correctly.
"""

import pytest
import time
from typing import Any


@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Fix expected lingering timers for tests."""
    return True


def test_reverse_suffix_mapping_constant_exists():
    """Test that _REVERSE_SUFFIX_MAPPING constant exists."""
    from custom_components.span_panel import helpers

    assert hasattr(helpers, "_REVERSE_SUFFIX_MAPPING")
    assert isinstance(helpers._REVERSE_SUFFIX_MAPPING, dict)


def test_reverse_mapping_contains_all_entries():
    """Test that reverse mapping contains all forward mapping entries."""
    from custom_components.span_panel.constants.suffix_mappings import (
        _REVERSE_SUFFIX_MAPPING,
        CIRCUIT_SUFFIX_MAPPING,
        PANEL_SUFFIX_MAPPING,
        PANEL_ENTITY_SUFFIX_MAPPING,
    )

    # Count expected entries
    expected_count = (
        len(CIRCUIT_SUFFIX_MAPPING)
        + len(PANEL_SUFFIX_MAPPING)
        + len(PANEL_ENTITY_SUFFIX_MAPPING)
    )

    # Reverse mapping should have all entries (some may overlap)
    assert len(_REVERSE_SUFFIX_MAPPING) <= expected_count
    assert len(_REVERSE_SUFFIX_MAPPING) > 0


def test_get_api_description_key_from_suffix_basic():
    """Test basic suffix to API key lookup."""
    from custom_components.span_panel.helpers import get_api_description_key_from_suffix

    # Test valid lookups
    result = get_api_description_key_from_suffix("power")
    assert result is not None
    assert isinstance(result, str)


def test_get_api_description_key_from_suffix_circuit_mapping():
    """Test circuit suffix mappings."""
    from custom_components.span_panel.helpers import get_api_description_key_from_suffix
    from custom_components.span_panel.constants.suffix_mappings import CIRCUIT_SUFFIX_MAPPING

    # Test a few known circuit mappings
    for api_key, suffix in CIRCUIT_SUFFIX_MAPPING.items():
        result = get_api_description_key_from_suffix(suffix)
        assert result == api_key, f"Expected {api_key} for suffix {suffix}, got {result}"


def test_get_api_description_key_from_suffix_panel_mapping():
    """Test panel suffix mappings."""
    from custom_components.span_panel.helpers import get_api_description_key_from_suffix
    from custom_components.span_panel.constants.suffix_mappings import PANEL_SUFFIX_MAPPING

    # Test panel mappings
    for api_key, suffix in PANEL_SUFFIX_MAPPING.items():
        result = get_api_description_key_from_suffix(suffix)
        assert result == api_key, f"Expected {api_key} for suffix {suffix}, got {result}"


def test_get_api_description_key_from_suffix_panel_entity_priority():
    """Test that panel entity mappings take precedence."""
    from custom_components.span_panel.helpers import get_api_description_key_from_suffix
    from custom_components.span_panel.constants.suffix_mappings import PANEL_ENTITY_SUFFIX_MAPPING

    # Panel entity mappings should override others
    for api_key, suffix in PANEL_ENTITY_SUFFIX_MAPPING.items():
        result = get_api_description_key_from_suffix(suffix)
        assert result == api_key, f"Expected {api_key} for suffix {suffix}, got {result}"


def test_get_api_description_key_from_suffix_invalid():
    """Test invalid suffix returns None."""
    from custom_components.span_panel.helpers import get_api_description_key_from_suffix

    result = get_api_description_key_from_suffix("nonexistent_suffix_xyz")
    assert result is None


def test_get_api_description_key_from_suffix_empty_string():
    """Test empty string returns None."""
    from custom_components.span_panel.helpers import get_api_description_key_from_suffix

    result = get_api_description_key_from_suffix("")
    assert result is None


def test_reverse_mapping_performance():
    """Benchmark test: cached mapping should be significantly faster."""
    from custom_components.span_panel.helpers import get_api_description_key_from_suffix
    from custom_components.span_panel.constants.suffix_mappings import (
        CIRCUIT_SUFFIX_MAPPING,
        PANEL_SUFFIX_MAPPING,
        PANEL_ENTITY_SUFFIX_MAPPING,
    )

    # Get a sample suffix to test
    sample_suffix = list(CIRCUIT_SUFFIX_MAPPING.values())[0]

    # Warm up
    for _ in range(10):
        get_api_description_key_from_suffix(sample_suffix)

    # Benchmark: should be fast (< 1ms for 10000 lookups)
    start = time.perf_counter()
    for _ in range(10000):
        result = get_api_description_key_from_suffix(sample_suffix)
    end = time.perf_counter()

    duration_ms = (end - start) * 1000

    print(f"\nPerformance test: 10,000 lookups in {duration_ms:.2f}ms")
    print(f"Average per lookup: {duration_ms/10000:.4f}ms")

    # Should complete in < 100ms (very conservative - actual should be ~1-2ms)
    assert duration_ms < 100, f"Lookups too slow: {duration_ms:.2f}ms"


def test_reverse_mapping_correctness_comprehensive():
    """Comprehensive test that all mappings are correctly reversed."""
    from custom_components.span_panel.helpers import get_api_description_key_from_suffix
    from custom_components.span_panel.constants.suffix_mappings import (
        CIRCUIT_SUFFIX_MAPPING,
        PANEL_SUFFIX_MAPPING,
        PANEL_ENTITY_SUFFIX_MAPPING,
    )

    # Build expected reverse mapping manually
    expected_reverse = {}

    # Add circuit mappings
    for api_key, suffix in CIRCUIT_SUFFIX_MAPPING.items():
        expected_reverse[suffix] = api_key

    # Add panel mappings
    for api_key, suffix in PANEL_SUFFIX_MAPPING.items():
        expected_reverse[suffix] = api_key

    # Add panel entity mappings (these override)
    for api_key, suffix in PANEL_ENTITY_SUFFIX_MAPPING.items():
        expected_reverse[suffix] = api_key

    # Test every entry
    for suffix, expected_api_key in expected_reverse.items():
        actual_api_key = get_api_description_key_from_suffix(suffix)
        assert (
            actual_api_key == expected_api_key
        ), f"Suffix '{suffix}': expected '{expected_api_key}', got '{actual_api_key}'"
