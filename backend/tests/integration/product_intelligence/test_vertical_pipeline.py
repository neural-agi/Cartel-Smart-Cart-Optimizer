from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.data_ingestion import (
    AcquisitionResult,
    CaptureContext,
    CaptureCoverage,
    CaptureType,
    DownstreamMode,
    InMemoryObservationRegistry,
    Platform,
    RequestParameters,
    ScrapeJob,
)
from app.data_ingestion.artifact_store import LocalFilesystemArtifactStore
from app.normalization.ingestion import DeterministicIngestionNormalizer
from app.product_intelligence.assertions import DeterministicAssertionManager
from app.product_intelligence.candidate_generation import (
    DeterministicCandidateGenerationService,
)
from app.product_intelligence.catalog import (
    DeterministicCandidateCatalogSnapshotBuilder,
    DeterministicCanonicalListingResolver,
    FilesystemAuthoritativeCatalog,
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.product_intelligence.evidence import EvidenceFilesystemStore, FilesystemEvidenceRegistry
from app.product_intelligence.execution import (
    ProductIntelligenceExecutionStatus,
    ProductIntelligenceExecutionTrigger,
)
from app.product_intelligence.ingestion import ProductIntelligenceEvidencePublisher
from app.product_intelligence.matching import (
    DeterministicProductMatcher,
    DeterministicVariantMatcher,
)
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
    IdentityStatus,
    Measurement,
    PackConfiguration,
    PackKind,
    Product,
    ProductLifecycleStatus,
    ProductVariant,
    QuantityDimension,
    VariantLifecycleStatus,
)
from app.product_intelligence.orchestrator.service import (
    DeterministicProductIntelligenceOrchestrator,
)
from app.product_intelligence.review import DeterministicReviewQueueManager
from app.scrapers.blinkit.bridge import BlinkitParserBridge
from app.workers.local_ingestion import LocalIngestionWorker
from app.workers.product_intelligence_runtime import ProductIntelligenceRuntime


FIXTURE_HTML = b'''<!doctype html>
<html><body>
  <div role="button"><span>Amul</span><span>500 ml</span><span>Rs 100</span><span>ADD</span></div>
</body></html>'''


class FixtureAcquisition:
    async def acquire_search(self, *, query: str, evaluation_scope: str) -> AcquisitionResult:
        coverage = CaptureCoverage(
            evaluation_scope=evaluation_scope,
            pages_evaluated=1,
            pagination_complete=True,
            termination_reason="fixture_complete",
        )
        return AcquisitionResult(
            payload=FIXTURE_HTML,
            source_reference="https://fixture.invalid/blinkit/search?q=milk",
            content_type="text/html",
            capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_scope=evaluation_scope,
            pages_evaluated=1,
            pagination_complete=True,
            termination_reason="fixture_complete",
            capture_type=CaptureType.SEARCH_RESULTS,
            warnings=tuple(),
            capture_coverage=coverage,
        )


def _job() -> ScrapeJob:
    return ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "milk"),)),
        capture_context=CaptureContext(
            country_code="IN",
            currency_code="INR",
            locale="en-IN",
            location_scope="fixture",
            session_scope="e2e",
        ),
        parser_policy_version="blinkit-parser-v1",
        normalization_policy_version="normalizer-v1",
        downstream_mode=DownstreamMode.NONE,
        job_contract_version="fixture-v1",
    )


def _measurement() -> Measurement:
    return Measurement(
        value=Decimal("500"),
        unit="ml",
        dimension=QuantityDimension.volume,
        content_basis="net_content",
        assertion_status="asserted",
    )


def _product() -> Product:
    return Product(
        canonical_product_id="product-amul-taaza",
        product_identity_status=IdentityStatus.established,
        brand_reference=BrandReference(
            canonical_brand_name="Amul",
            display_label="Amul",
            is_unknown=False,
        ),
        product_type="milk",
        canonical_display_name="Amul",
        identity_attributes=[
            AttributeAssertion(name="milk_type", value="toned", role="identity_critical")
        ],
        canonical_category_reference=CategoryReference(
            category_id="dairy-milk",
            category_path="dairy/milk",
            taxonomy_version="v1",
            review_state="approved",
        ),
        lifecycle_status=ProductLifecycleStatus.active,
        catalog_revision="rev-1",
        evidence_references=[],
    )


def _variant() -> ProductVariant:
    measurement = _measurement()
    return ProductVariant(
        canonical_variant_id="variant-amul-taaza-500ml",
        canonical_product_id="product-amul-taaza",
        variant_identity_status=IdentityStatus.established,
        variant_identity_attributes=[],
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.single_unit,
            consumer_unit_count=1,
            content_per_consumer_unit=measurement,
            total_declared_content=measurement,
            packaging_form="pouch",
            component_set=[],
            pack_configuration_status="complete",
        ),
        lifecycle_status=VariantLifecycleStatus.active,
        catalog_revision="rev-1",
        evidence_references=[],
    )


def _orchestrator(evidence_registry, snapshot):
    return DeterministicProductIntelligenceOrchestrator(
        evidence_registry=evidence_registry,
        candidate_generator=DeterministicCandidateGenerationService(snapshot),
        product_matcher=DeterministicProductMatcher(),
        variant_matcher=DeterministicVariantMatcher(),
        review_queue_manager=DeterministicReviewQueueManager(),
        assertion_manager=DeterministicAssertionManager(),
    )


def _runtime(tmp_path, *, resolver):
    catalog = FilesystemAuthoritativeCatalog(
        store=CatalogFilesystemStore(root_dir=tmp_path / "catalog")
    )
    catalog.register_product(_product())
    catalog.register_variant(_variant())
    association_registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "associations")
    )
    evidence_registry = FilesystemEvidenceRegistry(
        store=EvidenceFilesystemStore(root_dir=tmp_path / "evidence")
    )
    snapshot_builder = DeterministicCandidateCatalogSnapshotBuilder()
    trigger = ProductIntelligenceExecutionTrigger(
        evidence_publisher=ProductIntelligenceEvidencePublisher(evidence_registry),
        association_registry=association_registry,
        catalog=catalog,
        snapshot_builder=snapshot_builder,
        orchestrator_factory=lambda snapshot: _orchestrator(evidence_registry, snapshot),
    )
    runtime = ProductIntelligenceRuntime(
        ingestion_worker=LocalIngestionWorker(
            acquisition=FixtureAcquisition(),
            artifact_store=LocalFilesystemArtifactStore(
                root=tmp_path / "artifacts",
                store_namespace="runtime",
            ),
            bridge=BlinkitParserBridge(),
        ),
        normalizer=DeterministicIngestionNormalizer(),
        observation_registry=InMemoryObservationRegistry(),
        catalog=catalog,
        resolver=resolver,
        association_registry=association_registry,
        execution_trigger=trigger,
    )
    return runtime, catalog, association_registry


def _resolver(*, missing_product: bool = False):
    return DeterministicCanonicalListingResolver(
        product_observation_key=lambda item: (
            item.normalized_name + "-missing" if missing_product else item.normalized_name
        ),
        product_catalog_key=lambda item: item.canonical_display_name,
        variant_observation_key=lambda item, _product: item.normalized_quantity,
        variant_catalog_key=lambda item: (
            f"{item.pack_configuration.content_per_consumer_unit.value:g} "
            f"{item.pack_configuration.content_per_consumer_unit.unit}"
        ),
    )


@pytest.mark.asyncio
async def test_blinkit_observation_reaches_product_intelligence_end_to_end(tmp_path) -> None:
    catalog = FilesystemAuthoritativeCatalog(
        store=CatalogFilesystemStore(root_dir=tmp_path / "catalog")
    )
    product = _product()
    variant = _variant()
    catalog.register_product(product)
    catalog.register_variant(variant)
    catalog_before = catalog.load_state()

    worker = LocalIngestionWorker(
        acquisition=FixtureAcquisition(),
        artifact_store=LocalFilesystemArtifactStore(
            root=tmp_path / "artifacts",
            store_namespace="e2e",
        ),
        parser=None,
        bridge=BlinkitParserBridge(),
    )
    ingestion_result = await worker.execute(_job())
    assert ingestion_result.parsed_batch is not None
    assert ingestion_result.artifact_reference is not None
    assert len(ingestion_result.parsed_batch.observations) == 1
    parsed = ingestion_result.parsed_batch.observations[0]
    assert parsed.raw_title == "Amul"
    assert parsed.raw_quantity == "500 ml"

    observation = DeterministicIngestionNormalizer().normalize(ingestion_result.parsed_batch)[0]
    observation_registry = InMemoryObservationRegistry()
    registered_observation = observation_registry.register(observation)
    assert registered_observation == observation

    resolver = DeterministicCanonicalListingResolver(
        product_observation_key=lambda item: item.normalized_name,
        product_catalog_key=lambda item: item.canonical_display_name,
        variant_observation_key=lambda item, _product: item.normalized_quantity,
        variant_catalog_key=lambda item: (
            f"{item.pack_configuration.content_per_consumer_unit.value:g} "
            f"{item.pack_configuration.content_per_consumer_unit.unit}"
        ),
    )
    resolution = resolver.resolve(
        registered_observation,
        catalog.load_state(),
    )
    assert resolution.status.value == "mapped"
    assert resolution.association is not None
    assert resolution.association.canonical_product_id == product.canonical_product_id
    assert resolution.association.canonical_variant_id == variant.canonical_variant_id
    assert variant.canonical_product_id == resolution.association.canonical_product_id

    association_registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "associations")
    )
    persisted_association = association_registry.register(resolution.association)
    assert association_registry.get(
        persisted_association.platform,
        persisted_association.platform_listing_id,
    ) == persisted_association

    evidence_registry = FilesystemEvidenceRegistry(
        store=EvidenceFilesystemStore(root_dir=tmp_path / "evidence")
    )
    publisher = ProductIntelligenceEvidencePublisher(evidence_registry)
    snapshot_builder = DeterministicCandidateCatalogSnapshotBuilder()
    snapshot = snapshot_builder.build_from_catalog(catalog)
    trigger = ProductIntelligenceExecutionTrigger(
        evidence_publisher=publisher,
        association_registry=association_registry,
        catalog=catalog,
        snapshot_builder=snapshot_builder,
        orchestrator_factory=lambda built_snapshot: _orchestrator(
            evidence_registry, built_snapshot
        ),
    )

    result = await trigger.execute_resolution(registered_observation, resolution)
    assert result.status is ProductIntelligenceExecutionStatus.executed
    assert result.pipeline_result is not None
    assert result.pipeline_result.product_match_result.selected_product is not None
    assert result.pipeline_result.variant_match_result is not None
    assert result.pipeline_result.product_match_result.selected_product.canonical_product_id == product.canonical_product_id
    assert result.pipeline_result.variant_match_result.outcome.value == "unresolved"
    assert result.pipeline_request is not None
    assert result.pipeline_request.platform_listing.platform.lower() == "blinkit"
    assert result.pipeline_request.platform_listing.platform_listing_id == observation.source_record_id
    assert result.pipeline_request.listing_observation.source_artifact_reference == observation.raw_artifact_reference.artifact_id
    assert result.pipeline_request.evidence_bundles
    assert result.pipeline_request.evidence_bundles[0].parser_version == observation.parser_version
    assert result.candidate_catalog_snapshot == snapshot
    assert catalog.load_state() == catalog_before
    assert result.pipeline_result.final_pipeline_outcome.value == "review_queued"

    replay = await trigger.execute_resolution(registered_observation, resolution)
    assert replay.model_dump(mode="json") == result.model_dump(mode="json")


@pytest.mark.asyncio
async def test_scrape_job_runtime_entrypoint_returns_product_intelligence_result(tmp_path) -> None:
    runtime, catalog, association_registry = _runtime(tmp_path, resolver=_resolver())

    result = await runtime.execute(_job())

    assert result.status == "completed"
    assert len(result.observations) == 1
    record = result.observations[0]
    assert record.status.value == "resolved"
    assert record.execution is not None
    assert record.execution.status is ProductIntelligenceExecutionStatus.executed
    assert record.execution.pipeline_result is not None
    assert record.execution.pipeline_request is not None
    assert record.execution.pipeline_request.platform_listing.platform_listing_id == "1"
    assert record.execution.association is not None
    assert record.execution.association.canonical_product_id == "product-amul-taaza"
    assert record.execution.association.canonical_variant_id == "variant-amul-taaza-500ml"
    assert association_registry.get("BLINKIT", "1") is not None
    assert len(catalog.load_state().products) == 1


@pytest.mark.asyncio
async def test_runtime_unresolved_association_does_not_execute_product_intelligence(tmp_path) -> None:
    runtime, _catalog, association_registry = _runtime(
        tmp_path,
        resolver=_resolver(missing_product=True),
    )

    result = await runtime.execute(_job())

    assert result.status == "completed_with_failures"
    record = result.observations[0]
    assert record.status.value == "association_unresolved"
    assert record.execution is not None
    assert record.execution.status is ProductIntelligenceExecutionStatus.association_unresolved
    assert record.execution.pipeline_result is None
    assert association_registry.list_for_listing("BLINKIT", "1") == tuple()
