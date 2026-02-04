"""Constants package for Span Panel integration.

This package contains constant definitions and mappings used throughout the integration.
"""

from __future__ import annotations

from .suffix_mappings import (
    _REVERSE_SUFFIX_MAPPING,
    ALL_SUFFIX_MAPPINGS,
    CIRCUIT_SUFFIX_MAPPING,
    PANEL_ENTITY_SUFFIX_MAPPING,
    PANEL_SUFFIX_MAPPING,
)

__all__ = [
    "CIRCUIT_SUFFIX_MAPPING",
    "PANEL_SUFFIX_MAPPING",
    "PANEL_ENTITY_SUFFIX_MAPPING",
    "ALL_SUFFIX_MAPPINGS",
    "_REVERSE_SUFFIX_MAPPING",
]
