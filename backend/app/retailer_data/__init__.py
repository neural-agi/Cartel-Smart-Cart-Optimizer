"""Provider-neutral retailer evidence acquisition and observation contracts.

The package exposes two related but distinct boundaries:

* acquisition contracts/providers from :mod:`app.retailer_data.contracts` and
  :mod:`app.retailer_data.providers`; and
* observation, association, persistence, and job boundaries from the
  observation-oriented modules.

Two names collide across those boundaries, so the observation-oriented
implementations are exported under explicit aliases. Production code imports
the concrete submodules directly; these aliases keep package-level imports
unambiguous.
"""

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
from app.retailer_data.association import GovernedRetailerAssociationService
from app.retailer_data.blinkit import (
    BlinkitRetailerDataProvider as ObservationBlinkitRetailerDataProvider,
)
from app.retailer_data.persistence import FilesystemRetailerObservationStore
from app.retailer_data.types import (
    AssociationStatus,
    RetailerObservation,
    RetailerObservationFreshness,
)
from app.retailer_data.jobs import (
    FilesystemRetailerAcquisitionSubmissionStore,
    RetailerAcquisitionIdempotencyConflict,
    RetailerAcquisitionRequest as RetailerAcquisitionJobRequest,
    build_retailer_acquisition_job,
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
    "AssociationStatus",
    "FilesystemRetailerObservationStore",
    "GovernedRetailerAssociationService",
    "ObservationBlinkitRetailerDataProvider",
    "RetailerAcquisitionIdempotencyConflict",
    "RetailerAcquisitionJobRequest",
    "RetailerObservation",
    "RetailerObservationFreshness",
    "FilesystemRetailerAcquisitionSubmissionStore",
    "build_retailer_acquisition_job",
]
