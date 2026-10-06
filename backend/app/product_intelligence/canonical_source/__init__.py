"""Source-isolated canonical evidence ingestion contracts."""

from app.product_intelligence.canonical_source.providers import (
    CanonicalSourceUnavailable,
    OpenFoodFactsProvider,
)
from app.product_intelligence.canonical_source.service import CanonicalEvidenceIngestionService
from app.product_intelligence.canonical_source.types import (
    CanonicalEvidenceCandidate,
    CanonicalEvidenceClaim,
    CanonicalEvidenceArtifact,
    CanonicalEvidenceAdmission,
    CanonicalEvidenceReview,
)

__all__ = [
    "CanonicalEvidenceAdmission",
    "CanonicalEvidenceArtifact",
    "CanonicalEvidenceCandidate",
    "CanonicalEvidenceClaim",
    "CanonicalEvidenceIngestionService",
    "CanonicalEvidenceReview",
    "CanonicalSourceUnavailable",
    "OpenFoodFactsProvider",
]
