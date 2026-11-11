"""Explicitly non-functional placeholder adapters.

Every controlled retailer ID has a placeholder so the registry can answer
capability queries deterministically. A placeholder declares every capability
``UNSUPPORTED``. It must never be presented as a working retailer integration.
"""

from __future__ import annotations

from app.retailer_adapters.base import RetailerAdapter
from app.retailer_adapters.capabilities import AdapterCapabilities
from app.retailer_connections.lifecycle import SUPPORTED_RETAILER_IDS
from app.retailer_data.contracts import AcquisitionMethod

PLACEHOLDER_REASON = "placeholder_not_implemented"


class PlaceholderRetailerAdapter(RetailerAdapter):
    """A registered retailer with no implemented operation."""

    acquisition_method = AcquisitionMethod.AUTHORIZED_THIRD_PARTY
    execution_policy = None

    def __init__(self, retailer_id: str) -> None:
        if retailer_id not in SUPPORTED_RETAILER_IDS:
            raise ValueError("unsupported retailer identifier")
        self.retailer_id = retailer_id
        self.adapter_id = f"{retailer_id.lower()}-placeholder"
        self.capabilities = AdapterCapabilities.all_unsupported(PLACEHOLDER_REASON)


def build_placeholder_adapters() -> tuple[PlaceholderRetailerAdapter, ...]:
    return tuple(
        PlaceholderRetailerAdapter(retailer_id)
        for retailer_id in sorted(SUPPORTED_RETAILER_IDS)
    )


__all__ = [
    "PLACEHOLDER_REASON",
    "PlaceholderRetailerAdapter",
    "build_placeholder_adapters",
]
