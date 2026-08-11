from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from app.data_ingestion import (
    CaptureType,
    CompletenessState,
    NormalizedObservation,
    ObservationCompleteness,
    ObservationFieldReference,
    Platform,
    RawArtifactReference,
)
from app.product_intelligence.assertions.types import AssertionUpdateResponse
from app.product_intelligence.candidate_generation import CandidateGenerationResponse
from app.product_intelligence.catalog import (
    CanonicalListingAssociation,
    DeterministicCandidateCatalogSnapshotBuilder,
    FilesystemAuthoritativeCatalog,
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
    ListingResolutionResult,
    ListingResolutionStatus,
)
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.product_intelligence.catalog.types import CatalogState
from app.product_intelligence.evidence import EvidenceFilesystemStore, FilesystemEvidenceRegistry
from app.product_intelligence.execution import (
    ProductIntelligenceExecutionStatus,
    ProductIntelligenceExecutionTrigger,
)
from app.product_intelligence.ingestion import (
    ProductIntelligenceEvidencePublisher,
    ProductIntelligenceIngestionAdapter,
)
from app.product_intelligence.matching import ProductMatchResponse, VariantMatchResponse
from app.product_intelligence.matching.types import MatchOutcome
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
    EvidenceReference,
    IdentityStatus,
    Measurement,
    PackConfiguration,
    PackKind,
    PlatformListing,
    Product,
    ProductLifecycleStatus,
    ProductVariant,
    QuantityDimension,
    VariantLifecycleStatus,
)
from app.product_intelligence.orchestrator.service import (
    PipelineOutcome,
    ProductIntelligencePipelineRequest,
    ProductIntelligencePipelineResult,
)


def _run(coro):
    return asyncio.run(coro)


def _measurement(amount: str, unit: str) -> Measurement:
    return Measurement(
        value=Decimal(amount),
        unit=unit,
        dimension=QuantityDimension.volume,
        content_basis="net_content",
        assertion_status="asserted",
    )


def _product(
    product_id: str = "product-1",
    *,
    lifecycle_status: ProductLifecycleStatus = ProductLifecycleStatus.active,
    identity_status: IdentityStatus = IdentityStatus.established,
    review_state: str = "approved",
) -> Product:
    return Product(
        canonical_product_id=product_id,
        product_identity_status=identity_status,
        brand_reference=BrandReference(
            canonical_brand_name="Amul",
            display_label="Amul",
            is_unknown=False,
        ),
        product_type="milk",
        canonical_display_name="Amul Taaza Milk",
        identity_attributes=[
            AttributeAssertion(
                name="milk_type",
                value="toned",
                role="identity_critical",
            )
        ],
        canonical_category_reference=CategoryReference(
            category_id="dairy-milk",
            category_path="dairy/milk",
            taxonomy_version="v1",
            review_state=review_state,
        ),
        lifecycle_status=lifecycle_status,
        catalog_revision="rev-1",
        evidence_references=[],
    )


def _variant(
    variant_id: str = "variant-1",
    *,
    product_id: str = "product-1",
    lifecycle_status: VariantLifecycleStatus = VariantLifecycleStatus.active,
    identity_status: IdentityStatus = IdentityStatus.established,
    pack_status: str = "complete",
) -> ProductVariant:
    return ProductVariant(
        canonical_variant_id=variant_id,
        canonical_product_id=product_id,
        variant_identity_status=identity_status,
        variant_identity_attributes=[],
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.single_unit,
            consumer_unit_count=1,
            content_per_consumer_unit=_measurement("500", "ml"),
            total_declared_content=_measurement("500", "ml"),
            packaging_form="pouch",
            component_set=[],
            pack_configuration_status=pack_status,
        ),
        lifecycle_status=lifecycle_status,
        catalog_revision="rev-1",
        evidence_references=[],
    )


def _observation(
    *,
    completeness: CompletenessState = CompletenessState.COMPLETE,
) -> NormalizedObservation:
    evidence = EvidenceReference(source_type="raw_artifact", source_id="artifact-1")
    observation_completeness = ObservationCompleteness(
        state=completeness,
        scope_reference="scope-1",
        basis="normalization-complete",
        missing_scope=("remaining-page",) if completeness is CompletenessState.PARTIAL else (),
    )
    return NormalizedObservation(
        platform=Platform.BLINKIT,
        source_record_id="listing-1",
        raw_artifact_reference=RawArtifactReference(
            artifact_id="artifact-1",
            job_id="job-1",
            attempt_id="attempt-1",
            platform=Platform.BLINKIT,
            capture_type=CaptureType.SEARCH_RESULTS,
            content_digest="digest",
            storage_reference="opaque",
            content_type="text/html",
            capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            source_reference="https://example.test",
        ),
        normalized_name="Amul Taaza Milk",
        normalized_quantity="500 ml",
        normalized_category="milk",
        evidence_references=(evidence,),
        field_references=(
            ObservationFieldReference(
                evidence_reference=evidence,
                locator="products[0].title",
            ),
        ),
        completeness=observation_completeness,
        parser_version="parser-v1",
        normalization_version="normalizer-v1",
    )


def _listing() -> PlatformListing:
    return PlatformListing(
        platform="blinkit",
        platform_listing_id="listing-1",
        raw_title="Amul Taaza Milk",
        raw_quantity_text="500 ml",
        raw_category_text="milk",
        listing_url="https://example.invalid/listing",
    )


def _catalog(tmp_path) -> FilesystemAuthoritativeCatalog:
    return FilesystemAuthoritativeCatalog(
        store=CatalogFilesystemStore(root_dir=tmp_path / "catalog")
    )


def _bundle(tmp_path, observation: NormalizedObservation):
    publisher = ProductIntelligenceEvidencePublisher(
        FilesystemEvidenceRegistry(store=EvidenceFilesystemStore(tmp_path / "evidence"))
    )
    handoff = ProductIntelligenceIngestionAdapter().build_handoff(observation)
    result = _run(publisher.publish(handoff))
    assert result.evidence_bundle is not None
    return result.evidence_bundle


def _association() -> CanonicalListingAssociation:
    return CanonicalListingAssociation(
        observation_id=_observation().observation_id,
        platform="BLINKIT",
        platform_listing_id="listing-1",
        canonical_product_id="product-1",
        canonical_variant_id="variant-1",
    )


def _pipeline_result(product: Product, variant: ProductVariant, bundle) -> ProductIntelligencePipelineResult:
    return ProductIntelligencePipelineResult(
        evidence_result=[bundle.model_copy(deep=True)],
        candidate_generation_result=CandidateGenerationResponse(
            product_candidates=[product.model_copy(deep=True)],
            variant_candidates=[variant.model_copy(deep=True)],
            rationale=["candidate generation matched the canonical catalog"],
        ),
        product_match_result=ProductMatchResponse(
            outcome=MatchOutcome.mapped,
            selected_product=product.model_copy(deep=True),
            rationale=["product matched"],
        ),
        variant_match_result=VariantMatchResponse(
            outcome=MatchOutcome.mapped,
            selected_variant=variant.model_copy(deep=True),
            rationale=["variant matched"],
        ),
        review_result=None,
        assertion_result=AssertionUpdateResponse(
            product=product.model_copy(deep=True),
            variant=variant.model_copy(deep=True),
        ),
        final_pipeline_outcome=PipelineOutcome.asserted,
    )


class _RecordingOrchestrator:
    def __init__(self, result: ProductIntelligencePipelineResult) -> None:
        self.result = result
        self.requests: list[ProductIntelligencePipelineRequest] = []

    async def execute(self, request: ProductIntelligencePipelineRequest):
        self.requests.append(request.model_copy(deep=True))
        return self.result


def _trigger(tmp_path, catalog, association_registry, orchestrator):
    return ProductIntelligenceExecutionTrigger(
        evidence_publisher=ProductIntelligenceEvidencePublisher(
            FilesystemEvidenceRegistry(store=EvidenceFilesystemStore(tmp_path / "evidence"))
        ),
        association_registry=association_registry,
        catalog=catalog,
        orchestrator_factory=lambda snapshot: orchestrator,
        snapshot_builder=DeterministicCandidateCatalogSnapshotBuilder(),
        ingestion_adapter=ProductIntelligenceIngestionAdapter(),
    )


def test_mapped_association_reaches_orchestrator_with_preserved_provenance(tmp_path) -> None:
    observation = _observation()
    catalog = _catalog(tmp_path)
    product = _product()
    variant = _variant()
    catalog.register_product(product)
    catalog.register_variant(variant)
    association_registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "catalog")
    )
    association = association_registry.register(_association())
    bundle = _bundle(tmp_path, observation)
    orchestrator = _RecordingOrchestrator(_pipeline_result(product, variant, bundle))
    trigger = _trigger(tmp_path, catalog, association_registry, orchestrator)

    result = _run(
        trigger.execute_resolution(
            observation,
            ListingResolutionResult(
                status=ListingResolutionStatus.mapped,
                association=association,
                rationale=("exact governed Product and Variant keys matched",),
            ),
        )
    )

    assert result.status is ProductIntelligenceExecutionStatus.executed
    assert result.observation_id == observation.observation_id
    assert result.raw_artifact_reference == observation.raw_artifact_reference
    assert result.evidence_references == observation.evidence_references
    assert result.field_references == observation.field_references
    assert result.parser_version == observation.parser_version
    assert result.normalization_version == observation.normalization_version
    assert result.platform == observation.platform.value
    assert result.platform_listing_id == observation.source_record_id
    assert result.association == association
    assert result.candidate_catalog_snapshot is not None
    assert result.pipeline_request is not None
    assert result.pipeline_result is not None
    assert orchestrator.requests == [result.pipeline_request]
    assert result.pipeline_request.evidence_bundles[0] == bundle
    assert [product.canonical_product_id for product in result.candidate_catalog_snapshot.products] == [
        "product-1"
    ]
    assert [variant.canonical_variant_id for variant in result.candidate_catalog_snapshot.variants] == [
        "variant-1"
    ]


def test_unresolved_ambiguous_and_conflicting_resolution_do_not_execute(tmp_path) -> None:
    observation = _observation()
    orchestrator = _RecordingOrchestrator(
        _pipeline_result(_product(), _variant(), _bundle(tmp_path, observation))
    )
    trigger = _trigger(
        tmp_path,
        _catalog(tmp_path),
        FilesystemCanonicalListingAssociationRegistry(
            store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "catalog")
        ),
        orchestrator,
    )

    unresolved = _run(
        trigger.execute_resolution(
            observation,
            ListingResolutionResult(
                status=ListingResolutionStatus.unresolved,
                rationale=("no match",),
            ),
        )
    )
    ambiguous = _run(
        trigger.execute_resolution(
            observation,
            ListingResolutionResult(
                status=ListingResolutionStatus.ambiguous,
                rationale=("multiple matches",),
            ),
        )
    )
    conflicting = _run(
        trigger.execute_resolution(
            observation,
            ListingResolutionResult(
                status=ListingResolutionStatus.conflicting,
                rationale=("conflict",),
            ),
        )
    )

    assert unresolved.status is ProductIntelligenceExecutionStatus.association_unresolved
    assert ambiguous.status is ProductIntelligenceExecutionStatus.association_unresolved
    assert conflicting.status is ProductIntelligenceExecutionStatus.association_unresolved
    assert orchestrator.requests == []


def test_inactive_unapproved_and_orphan_associations_fail_closed(tmp_path) -> None:
    observation = _observation()
    association_registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "catalog")
    )
    association = association_registry.register(_association())

    class _StaticCatalog:
        def __init__(self, state: CatalogState) -> None:
            self._state = state

        def load_state(self) -> CatalogState:
            return self._state

    invalid_orchestrator = _RecordingOrchestrator(
        _pipeline_result(_product(), _variant(), _bundle(tmp_path, observation))
    )

    inactive_trigger = _trigger(
        tmp_path,
        _StaticCatalog(
            CatalogState(
                products=(
                    _product(lifecycle_status=ProductLifecycleStatus.discontinued),
                ),
                variants=(_variant(),),
            )
        ),
        association_registry,
        invalid_orchestrator,
    )
    unapproved_trigger = _trigger(
        tmp_path,
        _StaticCatalog(
            CatalogState(
                products=(_product(review_state="reviewed"),),
                variants=(_variant(),),
            )
        ),
        association_registry,
        invalid_orchestrator,
    )
    orphan_trigger = _trigger(
        tmp_path,
        _StaticCatalog(
            CatalogState(
                products=(_product(),),
                variants=(_variant(product_id="missing"),),
            )
        ),
        association_registry,
        invalid_orchestrator,
    )

    inactive_result = _run(inactive_trigger.execute(observation, association))
    unapproved_result = _run(unapproved_trigger.execute(observation, association))
    orphan_result = _run(orphan_trigger.execute(observation, association))

    assert inactive_result.status is ProductIntelligenceExecutionStatus.catalog_snapshot_failed
    assert unapproved_result.status is ProductIntelligenceExecutionStatus.catalog_snapshot_failed
    assert orphan_result.status is ProductIntelligenceExecutionStatus.catalog_snapshot_failed
    assert invalid_orchestrator.requests == []


def test_replay_is_deterministic_and_persisted_catalog_can_execute(tmp_path) -> None:
    observation = _observation()
    catalog = _catalog(tmp_path)
    product = _product()
    variant = _variant()
    catalog.register_product(product)
    catalog.register_variant(variant)
    association_registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "catalog")
    )
    association = association_registry.register(_association())
    bundle = _bundle(tmp_path, observation)
    orchestrator = _RecordingOrchestrator(_pipeline_result(product, variant, bundle))
    trigger = _trigger(tmp_path, catalog, association_registry, orchestrator)

    first = _run(trigger.execute(observation, association))
    second = _run(trigger.execute(observation, association))

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert len(orchestrator.requests) == 2
    assert orchestrator.requests[0].model_dump(mode="json") == orchestrator.requests[1].model_dump(mode="json")


def test_evidence_publication_failure_prevents_orchestrator_execution(tmp_path) -> None:
    observation = _observation()
    catalog = _catalog(tmp_path)
    catalog.register_product(_product())
    catalog.register_variant(_variant())
    association_registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "catalog")
    )
    association = association_registry.register(_association())
    orchestrator = _RecordingOrchestrator(
        _pipeline_result(_product(), _variant(), _bundle(tmp_path, observation))
    )

    class _FailingPublisher:
        async def publish(self, handoff):
            raise RuntimeError("evidence publication failed")

    trigger = ProductIntelligenceExecutionTrigger(
        evidence_publisher=_FailingPublisher(),
        association_registry=association_registry,
        catalog=catalog,
        orchestrator_factory=lambda snapshot: orchestrator,
    )

    result = _run(trigger.execute(observation, association))

    assert result.status is ProductIntelligenceExecutionStatus.evidence_publication_failed
    assert orchestrator.requests == []
