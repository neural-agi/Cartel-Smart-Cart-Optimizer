from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.data_ingestion.enums import CompletenessState
from app.data_ingestion.types import NormalizedObservation, ObservationFieldReference, RawArtifactReference
from app.product_intelligence.catalog import (
    DeterministicCandidateCatalogSnapshotBuilder,
    FilesystemAuthoritativeCatalog,
    FilesystemCanonicalListingAssociationRegistry,
)
from app.product_intelligence.catalog.resolution import (
    CanonicalListingAssociation,
    ListingResolutionResult,
    ListingResolutionStatus,
)
from app.product_intelligence.candidate_generation.service import CandidateCatalogSnapshot
from app.product_intelligence.ingestion import (
    ProductIntelligenceEvidencePublisher,
    ProductIntelligenceIngestionAdapter,
)
from app.product_intelligence.models import (
    EvidenceReference,
)
from app.product_intelligence.orchestrator.service import (
    DeterministicProductIntelligenceOrchestrator,
    ProductIntelligencePipelineRequest,
    ProductIntelligencePipelineResult,
)


class ProductIntelligenceExecutionStatus(StrEnum):
    executed = "executed"
    empty_observation = "empty_observation"
    association_unresolved = "association_unresolved"
    evidence_publication_failed = "evidence_publication_failed"
    catalog_snapshot_failed = "catalog_snapshot_failed"
    orchestrator_failed = "orchestrator_failed"


class ProductIntelligenceExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ProductIntelligenceExecutionStatus
    observation_id: str
    raw_artifact_reference: RawArtifactReference
    evidence_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)
    field_references: tuple[ObservationFieldReference, ...] = Field(default_factory=tuple)
    parser_version: str
    normalization_version: str
    platform: str
    platform_listing_id: str
    resolution_status: ListingResolutionStatus | None = None
    resolution_rationale: tuple[str, ...] = Field(default_factory=tuple)
    association: CanonicalListingAssociation | None = None
    pipeline_request: ProductIntelligencePipelineRequest | None = None
    pipeline_result: ProductIntelligencePipelineResult | None = None
    candidate_catalog_snapshot: CandidateCatalogSnapshot | None = None
    rationale: tuple[str, ...] = Field(default_factory=tuple)


class ProductIntelligenceExecutionTrigger:
    """Prepare and execute one resolved normalized observation."""

    def __init__(
        self,
        *,
        evidence_publisher: ProductIntelligenceEvidencePublisher,
        association_registry: FilesystemCanonicalListingAssociationRegistry,
        catalog: FilesystemAuthoritativeCatalog,
        orchestrator_factory: Callable[
            [CandidateCatalogSnapshot], DeterministicProductIntelligenceOrchestrator
        ],
        snapshot_builder: DeterministicCandidateCatalogSnapshotBuilder | None = None,
        ingestion_adapter: ProductIntelligenceIngestionAdapter | None = None,
    ) -> None:
        self.evidence_publisher = evidence_publisher
        self.association_registry = association_registry
        self.catalog = catalog
        self.orchestrator_factory = orchestrator_factory
        self.snapshot_builder = snapshot_builder or DeterministicCandidateCatalogSnapshotBuilder()
        self.ingestion_adapter = ingestion_adapter or ProductIntelligenceIngestionAdapter()

    async def execute(
        self,
        observation: NormalizedObservation,
        association: CanonicalListingAssociation,
    ) -> ProductIntelligenceExecutionResult:
        return await self._execute_internal(
            observation=observation,
            association=association,
            resolution_status=ListingResolutionStatus.mapped,
            resolution_rationale=("resolved association provided directly",),
        )

    async def execute_resolution(
        self,
        observation: NormalizedObservation,
        resolution: ListingResolutionResult,
    ) -> ProductIntelligenceExecutionResult:
        if resolution.status is not ListingResolutionStatus.mapped or resolution.association is None:
            return self._result(
                ProductIntelligenceExecutionStatus.association_unresolved,
                observation,
                association=None,
                rationale="resolution did not produce an executable association",
                resolution_status=resolution.status,
                resolution_rationale=resolution.rationale,
            )
        return await self._execute_internal(
            observation=observation,
            association=resolution.association,
            resolution_status=resolution.status,
            resolution_rationale=resolution.rationale,
        )

    async def _execute_internal(
        self,
        *,
        observation: NormalizedObservation,
        association: CanonicalListingAssociation,
        resolution_status: ListingResolutionStatus | None,
        resolution_rationale: tuple[str, ...],
    ) -> ProductIntelligenceExecutionResult:
        if observation.completeness.state is CompletenessState.EMPTY:
            return self._result(
                ProductIntelligenceExecutionStatus.empty_observation,
                observation,
                association=association,
                rationale="EMPTY observations do not produce executable Product Intelligence listings",
                resolution_status=resolution_status,
                resolution_rationale=resolution_rationale,
            )

        association_error = self._validate_association(observation, association)
        if association_error is not None:
            return self._result(
                ProductIntelligenceExecutionStatus.association_unresolved,
                observation,
                association=association,
                rationale=association_error,
                resolution_status=resolution_status,
                resolution_rationale=resolution_rationale,
            )

        try:
            stored_associations = self.association_registry.list_for_listing(
                association.platform, association.platform_listing_id
            )
            if association not in stored_associations:
                raise ValueError("association is not registered for this observation")
        except Exception as exc:
            return self._result(
                ProductIntelligenceExecutionStatus.association_unresolved,
                observation,
                association=association,
                rationale=f"association is not durably registered: {exc}",
                resolution_status=resolution_status,
                resolution_rationale=resolution_rationale,
            )

        handoff = self.ingestion_adapter.build_handoff(observation)
        try:
            publication = await self.evidence_publisher.publish(handoff)
        except Exception as exc:
            return self._result(
                ProductIntelligenceExecutionStatus.evidence_publication_failed,
                observation,
                association=association,
                rationale=str(exc),
                resolution_status=resolution_status,
                resolution_rationale=resolution_rationale,
            )
        if publication.evidence_bundle is None:
            return self._result(
                ProductIntelligenceExecutionStatus.evidence_publication_failed,
                observation,
                association=association,
                rationale="registered evidence did not produce an assemblable bundle",
                resolution_status=resolution_status,
                resolution_rationale=resolution_rationale,
            )

        try:
            snapshot = self.snapshot_builder.build_from_catalog(self.catalog)
            self._require_association_entities(snapshot, association)
        except Exception as exc:
            return self._result(
                ProductIntelligenceExecutionStatus.catalog_snapshot_failed,
                observation,
                association=association,
                rationale=str(exc),
                resolution_status=resolution_status,
                resolution_rationale=resolution_rationale,
            )

        if handoff.pipeline_request is None:
            return self._result(
                ProductIntelligenceExecutionStatus.orchestrator_failed,
                observation,
                association=association,
                rationale="non-empty handoff did not contain a Product Intelligence pipeline request",
                resolution_status=resolution_status,
                resolution_rationale=resolution_rationale,
                snapshot=snapshot,
            )
        request = handoff.pipeline_request.model_copy(
            update={"evidence_bundles": [publication.evidence_bundle]}, deep=True
        )
        try:
            result = await self.orchestrator_factory(snapshot).execute(request)
        except Exception as exc:
            return self._result(
                ProductIntelligenceExecutionStatus.orchestrator_failed,
                observation,
                association=association,
                rationale=str(exc),
                resolution_status=resolution_status,
                resolution_rationale=resolution_rationale,
                request=request,
                snapshot=snapshot,
            )
        return ProductIntelligenceExecutionResult(
            status=ProductIntelligenceExecutionStatus.executed,
            observation_id=observation.observation_id,
            raw_artifact_reference=observation.raw_artifact_reference,
            evidence_references=observation.evidence_references,
            field_references=observation.field_references,
            parser_version=observation.parser_version,
            normalization_version=observation.normalization_version,
            platform=observation.platform.value,
            platform_listing_id=observation.source_record_id,
            resolution_status=resolution_status,
            resolution_rationale=resolution_rationale,
            association=association,
            pipeline_request=request,
            pipeline_result=result,
            candidate_catalog_snapshot=snapshot,
            rationale=("registered association, assembled evidence, and executed orchestrator",),
        )

    @staticmethod
    def _validate_association(
        observation: NormalizedObservation,
        association: CanonicalListingAssociation,
    ) -> str | None:
        if association.observation_id != observation.observation_id:
            return "association observation_id does not match the normalized observation"
        if association.platform != observation.platform.value:
            return "association platform does not match the normalized observation"
        if association.platform_listing_id != observation.source_record_id:
            return "association platform_listing_id does not match the normalized observation"
        if not association.canonical_product_id or not association.canonical_variant_id:
            return "association requires both canonical Product and Variant IDs"
        return None

    @staticmethod
    def _require_association_entities(
        snapshot: CandidateCatalogSnapshot,
        association: CanonicalListingAssociation,
    ) -> None:
        product_ids = {product.canonical_product_id for product in snapshot.products}
        variants = {variant.canonical_variant_id: variant for variant in snapshot.variants}
        if association.canonical_product_id not in product_ids:
            raise ValueError("association Product is not eligible in the catalog snapshot")
        variant = variants.get(association.canonical_variant_id)
        if variant is None:
            raise ValueError("association Variant is not eligible in the catalog snapshot")
        if variant.canonical_product_id != association.canonical_product_id:
            raise ValueError("association Variant parent conflicts with Product")

    @staticmethod
    def _result(
        status: ProductIntelligenceExecutionStatus,
        observation: NormalizedObservation,
        *,
        association: CanonicalListingAssociation | None,
        rationale: str,
        resolution_status: ListingResolutionStatus | None = None,
        resolution_rationale: tuple[str, ...] = (),
        request: ProductIntelligencePipelineRequest | None = None,
        snapshot: CandidateCatalogSnapshot | None = None,
    ) -> ProductIntelligenceExecutionResult:
        return ProductIntelligenceExecutionResult(
            status=status,
            observation_id=observation.observation_id,
            raw_artifact_reference=observation.raw_artifact_reference,
            evidence_references=observation.evidence_references,
            field_references=observation.field_references,
            parser_version=observation.parser_version,
            normalization_version=observation.normalization_version,
            platform=observation.platform.value,
            platform_listing_id=observation.source_record_id,
            resolution_status=resolution_status,
            resolution_rationale=resolution_rationale,
            association=association,
            pipeline_request=request,
            candidate_catalog_snapshot=snapshot,
            rationale=(rationale,),
        )
