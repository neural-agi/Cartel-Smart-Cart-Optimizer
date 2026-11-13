"""Unit coverage for the deterministic ``CARTEL_DEMO`` synthetic catalog.

These tests pin the non-negotiable properties of the demo lane:

* generation is byte-for-byte deterministic;
* every record carries explicit synthetic provenance;
* the live-evidence gate and the Blinkit policy both reject the source;
* the source has no retailer adapter, connection, or acquisition capability;
* search and candidate discovery expose it only through the demo gate; and
* unknown/unavailable availability is preserved rather than invented.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.data_ingestion import (
    CaptureContext,
    CaptureType,
    DownstreamMode,
    Platform,
    RequestParameters,
    ScrapeJob,
)
from app.data_ingestion.observation_registry.filesystem import (
    FilesystemObservationRegistry,
)
from app.demo_catalog import (
    SYNTHETIC_NORMALIZATION_VERSION,
    SYNTHETIC_PARSER_VERSION,
    SYNTHETIC_PLATFORM,
    SYNTHETIC_PROVENANCE_BASIS,
)
from app.dev.seed_synthetic_demo_cart import (
    SYNTHETIC_CATALOG,
    listing_id,
    product_id,
    seed_synthetic_demo_catalog,
    variant_id,
)
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.retailer_adapters.registry import build_default_registry
from app.retailer_connections.lifecycle import SUPPORTED_RETAILER_IDS
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItemRequest,
    CartCandidateDiscoveryRequest,
    CartCandidateDiscoveryService,
    CartCandidateDiscoveryStatus,
    PersistedCandidateReadiness,
)
from app.services.product_search import (
    ProductSearchRequest,
    ProductSearchService,
    has_supported_retailer_evidence,
    is_synthetic_demo_observation,
)
from app.workers.local_ingestion import LocalIngestionWorker
from app.workers.product_intelligence_runtime import ProductIntelligenceRuntime


def _digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _runtime(root: Path):
    catalog = FilesystemAuthoritativeCatalog(
        store=CatalogFilesystemStore(root_dir=root / "product_intelligence" / "catalog")
    )
    associations = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(
            root_dir=root / "product_intelligence" / "catalog"
        )
    )
    observations = FilesystemObservationRegistry(
        root_dir=root / "product_intelligence" / "observations"
    )
    return catalog, associations, observations


def _search(root: Path, *, include_fixtures: bool) -> ProductSearchService:
    catalog, associations, observations = _runtime(root)
    return ProductSearchService(
        catalog=catalog,
        association_registry=associations,
        observation_registry=observations,
        include_fixtures=include_fixtures,
    )


def _discovery(root: Path, *, include_synthetic: bool) -> CartCandidateDiscoveryService:
    catalog, associations, observations = _runtime(root)
    return CartCandidateDiscoveryService(
        catalog=catalog,
        association_registry=associations,
        observation_registry=observations,
        include_synthetic=include_synthetic,
    )


@pytest.fixture()
def synthetic_root(tmp_path: Path) -> Path:
    root = tmp_path / "synthetic"
    seed_synthetic_demo_catalog(root)
    return root


def test_generator_is_byte_for_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    seed_synthetic_demo_catalog(first)
    seed_synthetic_demo_catalog(second)

    assert _digest(first) == _digest(second)


def test_every_record_carries_explicit_synthetic_provenance(
    synthetic_root: Path,
) -> None:
    _, _, observations = _runtime(synthetic_root)
    records = observations.list_all()

    assert len(records) == 16
    for observation in records:
        assert observation.platform is SYNTHETIC_PLATFORM
        assert observation.parser_version == SYNTHETIC_PARSER_VERSION
        assert observation.normalization_version == SYNTHETIC_NORMALIZATION_VERSION
        assert observation.completeness.basis == SYNTHETIC_PROVENANCE_BASIS
        assert observation.raw_artifact_reference.source_reference.startswith(
            "synthetic://cartel-demo/"
        )
        assert is_synthetic_demo_observation(observation) is True
        # The live-evidence gate must reject the synthetic source.
        assert has_supported_retailer_evidence("CARTEL_DEMO", observation) is False
        assert has_supported_retailer_evidence("BLINKIT", observation) is False


def test_synthetic_source_is_not_a_connectable_retailer() -> None:
    assert "CARTEL_DEMO" not in SUPPORTED_RETAILER_IDS
    assert "CARTEL_DEMO" not in build_default_registry().retailer_ids


def test_search_requires_the_demo_gate(tmp_path: Path) -> None:
    root = tmp_path / "gated"
    seed_synthetic_demo_catalog(root)

    assert _search(root, include_fixtures=False).search(
        ProductSearchRequest(query="Cartel Demo")
    ).items == ()

    enabled = _search(root, include_fixtures=True).search(
        ProductSearchRequest(query="Cartel Demo")
    )
    assert len(enabled.items) == 16
    assert all(item.evidence_state == "synthetic_demo" for item in enabled.items)
    assert all(item.synthetic is True for item in enabled.items)
    assert all(item.platform == "CARTEL_DEMO" for item in enabled.items)
    assert all(
        item.parser_version == SYNTHETIC_PARSER_VERSION for item in enabled.items
    )
    assert all(
        item.source_reference.startswith("synthetic://cartel-demo/")
        for item in enabled.items
    )


def test_search_never_returns_blinkit_labelled_rows(synthetic_root: Path) -> None:
    result = _search(synthetic_root, include_fixtures=True).search(
        ProductSearchRequest(query="Cartel Demo")
    )

    assert result.items
    assert all(item.platform != "BLINKIT" for item in result.items)


def test_exact_pack_size_variants_remain_distinct(synthetic_root: Path) -> None:
    result = _search(synthetic_root, include_fixtures=True).search(
        ProductSearchRequest(query="Cartel Demo Toned Milk")
    )

    variants = {item.canonical_variant_id for item in result.items}
    packs = {item.pack for item in result.items}
    assert variants == {
        "cartel-demo-variant-milk-500ml",
        "cartel-demo-variant-milk-1l",
    }
    assert packs == {"500 ml", "1 l"}


def test_unknown_and_unavailable_availability_is_preserved(
    synthetic_root: Path,
) -> None:
    result = _search(synthetic_root, include_fixtures=True).search(
        ProductSearchRequest(query="Cartel Demo")
    )
    by_listing = {item.platform_listing_id: item for item in result.items}

    assert by_listing["cartel-demo-listing-rice-1kg-a"].availability_signal == "unavailable"
    assert by_listing["cartel-demo-listing-atta-1kg-b"].availability_signal is None
    assert by_listing["cartel-demo-listing-oil-2l-b"].availability_signal is None


def test_discovery_requires_the_synthetic_gate(synthetic_root: Path) -> None:
    request = CartCandidateDiscoveryRequest(
        items=(
            CartCandidateDiscoveryItemRequest(
                item_id="milk",
                quantity=2,
                canonical_product_id=product_id("milk"),
                canonical_variant_id=variant_id("milk-500ml"),
            ),
        )
    )

    disabled = _discovery(synthetic_root, include_synthetic=False).discover(request)
    assert disabled.items[0].status is CartCandidateDiscoveryStatus.candidates_not_ready
    assert all(
        candidate.readiness is PersistedCandidateReadiness.not_ready_for_allocation
        for candidate in disabled.items[0].candidates
    )
    assert all(
        candidate.readiness_reason == "synthetic demo evidence is not enabled"
        for candidate in disabled.items[0].candidates
    )

    enabled = _discovery(synthetic_root, include_synthetic=True).discover(request)
    assert enabled.items[0].status is CartCandidateDiscoveryStatus.candidates_available
    assert all(
        candidate.evidence_class == "synthetic_demo"
        for candidate in enabled.items[0].candidates
    )
    assert all(
        candidate.readiness is PersistedCandidateReadiness.ready_for_allocation
        for candidate in enabled.items[0].candidates
    )


def test_discovery_keeps_unknown_availability_not_ready(synthetic_root: Path) -> None:
    request = CartCandidateDiscoveryRequest(
        items=(
            CartCandidateDiscoveryItemRequest(
                item_id="atta",
                quantity=1,
                canonical_product_id=product_id("atta"),
                canonical_variant_id=variant_id("atta-1kg"),
            ),
        )
    )

    result = _discovery(synthetic_root, include_synthetic=True).discover(request)
    states = {
        candidate.platform_listing_id: (
            candidate.readiness,
            candidate.readiness_reason,
        )
        for candidate in result.items[0].candidates
    }
    assert states["cartel-demo-listing-atta-1kg-a"] == (
        PersistedCandidateReadiness.ready_for_allocation,
        None,
    )
    assert states["cartel-demo-listing-atta-1kg-b"][0] is PersistedCandidateReadiness.not_ready_for_allocation

def _synthetic_job() -> ScrapeJob:
    return ScrapeJob(
        platform=Platform.CARTEL_DEMO,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "milk"),)),
        capture_context=CaptureContext(
            country_code="IN",
            currency_code="INR",
            locale="en-IN",
            location_scope="demo",
            session_scope="demo",
        ),
        parser_policy_version="synthetic-v1",
        normalization_policy_version="synthetic-v1",
        downstream_mode=DownstreamMode.NONE,
        job_contract_version="synthetic-v1",
    )


class _UnreachableAcquisition:
    def __init__(self) -> None:
        self.called = False

    async def acquire_search(self, *, query: str | None, evaluation_scope: str):
        self.called = True
        raise AssertionError("synthetic source must never invoke acquisition")


class _UnusedStore:
    def store(self, request, payload):  # pragma: no cover - never reached
        raise AssertionError("synthetic source must never publish artifacts")


@pytest.mark.asyncio
async def test_ingestion_worker_blocks_synthetic_acquisition() -> None:
    acquisition = _UnreachableAcquisition()
    worker = LocalIngestionWorker(
        acquisition=acquisition,  # type: ignore[arg-type]
        artifact_store=_UnusedStore(),  # type: ignore[arg-type]
    )

    result = await worker.execute(_synthetic_job())

    assert result.failed_stage == "synthetic_no_acquisition"
    assert result.attempt.outcome.value == "BLOCKED"
    assert result.attempt.failure.category.value == "POLICY_BLOCKED"
    assert acquisition.called is False


@pytest.mark.asyncio
async def test_product_intelligence_runtime_blocks_synthetic_jobs() -> None:
    worker = LocalIngestionWorker(
        acquisition=_UnreachableAcquisition(),  # type: ignore[arg-type]
        artifact_store=_UnusedStore(),  # type: ignore[arg-type]
    )
    job = _synthetic_job()
    worker_result = await worker.execute(job)
    runtime = ProductIntelligenceRuntime(
        ingestion_worker=worker,
        normalizer=None,  # type: ignore[arg-type]
        observation_registry=None,  # type: ignore[arg-type]
        catalog=None,  # type: ignore[arg-type]
        resolver=None,  # type: ignore[arg-type]
        association_registry=None,  # type: ignore[arg-type]
        execution_trigger=None,  # type: ignore[arg-type]
    )

    result = await runtime.execute_worker_result(job, worker_result)

    assert result.status == "policy_blocked"
    assert result.rationale == ("synthetic_catalog_has_no_acquisition_capability",)


def test_generator_exposes_only_declared_catalog(tmp_path: Path) -> None:
    root = tmp_path / "declared"
    seed_synthetic_demo_catalog(root)

    expected_products = {product_id(product.slug) for product in SYNTHETIC_CATALOG}
    expected_variants = {
        variant_id(variant.slug)
        for product in SYNTHETIC_CATALOG
        for variant in product.variants
    }
    expected_listings = {
        listing_id(variant.slug, listing.suffix)
        for product in SYNTHETIC_CATALOG
        for variant in product.variants
        for listing in variant.listings
    }

    catalog, associations, observations = _runtime(root)
    state = catalog.load_state()
    assert {product.canonical_product_id for product in state.products} == expected_products
    assert {variant.canonical_variant_id for variant in state.variants} == expected_variants
    assert {association.platform_listing_id for association in associations.all()} == expected_listings
    assert len(observations.list_all()) == len(expected_listings)


def test_synthetic_capture_timestamp_is_fixed(synthetic_root: Path) -> None:
    _, _, observations = _runtime(synthetic_root)
    timestamps = {
        observation.raw_artifact_reference.capture_timestamp
        for observation in observations.list_all()
    }
    assert timestamps == {datetime(2026, 1, 1, tzinfo=timezone.utc)}
