from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.data_ingestion.types import (
    NormalizedObservation,
    ObservationCompleteness,
    ObservationFieldReference,
    RawArtifactReference,
)
from app.product_intelligence.evidence.types import EvidenceBundle
from app.product_intelligence.models import ListingObservation, PlatformListing, EvidenceReference
from app.product_intelligence.orchestrator.service import ProductIntelligencePipelineRequest


class ProductIntelligenceIngestionHandoff(BaseModel):
    """Immutable Product Intelligence projection of one normalized observation."""

    model_config = ConfigDict(frozen=True)

    observation_id: str
    raw_artifact_reference: RawArtifactReference
    evidence_references: tuple[EvidenceReference, ...]
    field_references: tuple[ObservationFieldReference, ...]
    completeness: ObservationCompleteness
    normalization_version: str
    parser_version: str
    platform_listing: PlatformListing | None = None
    listing_observation: ListingObservation | None = None
    evidence_bundle: EvidenceBundle | None = None
    pipeline_request: ProductIntelligencePipelineRequest | None = None
