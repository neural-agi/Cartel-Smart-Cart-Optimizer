"""Provider-neutral retailer evidence acquisition contracts."""

from app.retailer_data.contracts import (
    AcquisitionMethod,
    EvidenceQuality,
    LocationScope,
    RetailerAcquisitionOutcome,
    RetailerAcquisitionRequest,
    RetailerAcquisitionResult,
)
from app.retailer_data.providers import (
    BlinkitRetailerDataProvider,
    ProviderAcquisitionAdapter,
    UnavailableRetailerDataProvider,
)

__all__ = [
    "AcquisitionMethod",
    "EvidenceQuality",
    "LocationScope",
    "RetailerAcquisitionOutcome",
    "RetailerAcquisitionRequest",
    "RetailerAcquisitionResult",
    "BlinkitRetailerDataProvider",
    "ProviderAcquisitionAdapter",
    "UnavailableRetailerDataProvider",
]
