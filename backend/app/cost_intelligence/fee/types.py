from __future__ import annotations

from enum import StrEnum


class FeeType(StrEnum):
    """Supported deterministic fee interpretations."""

    DELIVERY = "delivery"
    PLATFORM = "platform"
    HANDLING = "handling"
    PACKAGING = "packaging"
    SMALL_CART = "small_cart"
    SURGE = "surge"
    UNKNOWN = "unknown"
