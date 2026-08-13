from __future__ import annotations

from app.core.config import Settings
from app.data_ingestion.artifact_store import LocalFilesystemArtifactStore
from app.data_ingestion.lifecycle_store import FilesystemScrapeJobLifecycleStore
from app.data_ingestion.observation_registry import FilesystemObservationRegistry
from app.normalization.ingestion import DeterministicIngestionNormalizer
from app.product_intelligence.assertions import DeterministicAssertionManager
from app.product_intelligence.candidate_generation import DeterministicCandidateGenerationService
from app.product_intelligence.catalog import (
    DeterministicCandidateCatalogSnapshotBuilder,
    DeterministicCanonicalListingResolver,
    FilesystemAuthoritativeCatalog,
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.identity import (
    product_catalog_key,
    product_observation_key,
    variant_catalog_key,
    variant_observation_key,
)
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.product_intelligence.evidence import EvidenceFilesystemStore, FilesystemEvidenceRegistry
from app.product_intelligence.execution import ProductIntelligenceExecutionTrigger
from app.product_intelligence.ingestion import ProductIntelligenceEvidencePublisher
from app.product_intelligence.matching import DeterministicProductMatcher, DeterministicVariantMatcher
from app.product_intelligence.orchestrator import DeterministicProductIntelligenceOrchestrator
from app.product_intelligence.review import DeterministicReviewQueueManager
from app.workers.local_ingestion import LocalIngestionWorker
from app.workers.product_intelligence_runtime import ProductIntelligenceRuntime
from app.workers.job_execution_coordinator import JobExecutionCoordinator


def build_product_intelligence_runtime(settings: Settings) -> JobExecutionCoordinator:
    catalog_root = settings.data_dir / "product_intelligence" / "catalog"
    evidence_root = settings.data_dir / "product_intelligence" / "evidence"
    lifecycle_root = settings.data_dir / "data_ingestion" / "lifecycle"
    catalog = FilesystemAuthoritativeCatalog(
        store=CatalogFilesystemStore(root_dir=catalog_root)
    )
    association_registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=catalog_root)
    )
    evidence_registry = FilesystemEvidenceRegistry(
        store=EvidenceFilesystemStore(root_dir=evidence_root)
    )
    snapshot_builder = DeterministicCandidateCatalogSnapshotBuilder()
    resolver = DeterministicCanonicalListingResolver(
        product_observation_key=product_observation_key,
        product_catalog_key=product_catalog_key,
        variant_observation_key=variant_observation_key,
        variant_catalog_key=variant_catalog_key,
    )
    trigger = ProductIntelligenceExecutionTrigger(
        evidence_publisher=ProductIntelligenceEvidencePublisher(evidence_registry),
        association_registry=association_registry,
        catalog=catalog,
        snapshot_builder=snapshot_builder,
        orchestrator_factory=lambda snapshot: DeterministicProductIntelligenceOrchestrator(
            evidence_registry=evidence_registry,
            candidate_generator=DeterministicCandidateGenerationService(snapshot),
            product_matcher=DeterministicProductMatcher(),
            variant_matcher=DeterministicVariantMatcher(),
            review_queue_manager=DeterministicReviewQueueManager(),
            assertion_manager=DeterministicAssertionManager(),
        ),
    )
    runtime = ProductIntelligenceRuntime(
        ingestion_worker=LocalIngestionWorker(
            artifact_store=LocalFilesystemArtifactStore(
                root=settings.raw_data_dir,
                store_namespace="product-intelligence",
            ),
        ),
        normalizer=DeterministicIngestionNormalizer(),
        observation_registry=FilesystemObservationRegistry(
            root_dir=settings.data_dir / "product_intelligence" / "observations"
        ),
        catalog=catalog,
        resolver=resolver,
        association_registry=association_registry,
        execution_trigger=trigger,
    )
    return JobExecutionCoordinator(
        ingestion_worker=runtime.ingestion_worker,
        product_intelligence_runtime=runtime,
        lifecycle_store=FilesystemScrapeJobLifecycleStore(root_dir=lifecycle_root),
    )
