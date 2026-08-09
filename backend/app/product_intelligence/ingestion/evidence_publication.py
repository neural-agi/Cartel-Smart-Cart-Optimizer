from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.data_ingestion.enums import CompletenessState
from app.data_ingestion.types import (
    NormalizedObservation,
    ObservationCompleteness,
    ObservationFieldReference,
    RawArtifactReference,
)
from app.product_intelligence.evidence.interfaces import EvidenceRegistry
from app.product_intelligence.evidence.types import (
    EvidenceBundle,
    EvidenceRegistrationRequest,
)
from app.product_intelligence.ingestion.types import ProductIntelligenceIngestionHandoff
from app.product_intelligence.models import EvidenceReference


class EvidencePublicationResult(BaseModel):
    """Published evidence and preserved ingestion provenance."""

    model_config = ConfigDict(frozen=True)

    observation_id: str
    raw_artifact_reference: RawArtifactReference
    evidence_references: tuple[EvidenceReference, ...]
    field_references: tuple[ObservationFieldReference, ...]
    completeness: ObservationCompleteness
    normalization_version: str
    parser_version: str
    evidence_bundle: EvidenceBundle | None = None


class ProductIntelligenceEvidencePublisher:
    """Publish 6B evidence through the existing EvidenceRegistry only."""

    def __init__(self, registry: EvidenceRegistry) -> None:
        self.registry = registry

    async def publish(
        self,
        handoff: ProductIntelligenceIngestionHandoff,
    ) -> EvidencePublicationResult:
        if handoff.completeness.state is CompletenessState.EMPTY:
            bundle = None
        else:
            request = EvidenceRegistrationRequest(
                platform=handoff.platform_listing.platform if handoff.platform_listing else "",
                source_artifact_reference=handoff.raw_artifact_reference.artifact_id,
                parser_version=handoff.parser_version,
                capture_timestamp=handoff.raw_artifact_reference.capture_timestamp,
            )
            registration = await self.registry.register(request)
            bundle = await self.registry.assemble(registration.evidence_bundle)

        return EvidencePublicationResult(
            observation_id=handoff.observation_id,
            raw_artifact_reference=handoff.raw_artifact_reference,
            evidence_references=handoff.evidence_references,
            field_references=handoff.field_references,
            completeness=handoff.completeness,
            normalization_version=handoff.normalization_version,
            parser_version=handoff.parser_version,
            evidence_bundle=bundle,
        )
