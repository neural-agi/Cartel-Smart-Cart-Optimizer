"""Cartel Demo synthetic catalog identity and provenance.

``CARTEL_DEMO`` is a retailer-independent synthetic source.  It exists only so
the explicitly gated demo lane can exercise discovery, list persistence, and
optimization without live retailer evidence.

This module deliberately contains no acquisition, connection, credential,
cart-preparation, or checkout capability.  Every record produced for this
source is marked with the provenance constants below and is rejected by the
live-evidence gates.
"""

from __future__ import annotations

from app.data_ingestion.enums import Platform

SYNTHETIC_PLATFORM = Platform.CARTEL_DEMO
SYNTHETIC_PARSER_VERSION = "synthetic-v1"
SYNTHETIC_NORMALIZATION_VERSION = "synthetic-v1"
SYNTHETIC_PROVENANCE_BASIS = "synthetic-demo-catalog-v1"
SYNTHETIC_SOURCE_SCHEME = "synthetic"
SYNTHETIC_DISPLAY_BRAND = "Cartel Demo"
SYNTHETIC_DATASET_REVISION = "cartel-demo-v1"


def is_synthetic_demo_platform(value: object) -> bool:
    """Return whether a platform identity is the synthetic Cartel Demo source."""

    return getattr(value, "value", value) == SYNTHETIC_PLATFORM.value


def synthetic_source_reference(listing_id: str) -> str:
    return f"{SYNTHETIC_SOURCE_SCHEME}://cartel-demo/{listing_id}"


__all__ = [
    "SYNTHETIC_DATASET_REVISION",
    "SYNTHETIC_DISPLAY_BRAND",
    "SYNTHETIC_NORMALIZATION_VERSION",
    "SYNTHETIC_PARSER_VERSION",
    "SYNTHETIC_PLATFORM",
    "SYNTHETIC_PROVENANCE_BASIS",
    "SYNTHETIC_SOURCE_SCHEME",
    "is_synthetic_demo_platform",
    "synthetic_source_reference",
]
