from types import SimpleNamespace

import pytest

from app.cost_intelligence.shared.money import Money
from app.data_ingestion import (
    AttemptOutcome,
    CaptureContext,
    CaptureType,
    DownstreamMode,
    FailureCategory,
    FilesystemObservationRegistry,
    JobState,
    Platform,
    RequestParameters,
    ScrapeJob,
    TaxStatus,
)
from app.data_ingestion.lifecycle_store import FilesystemScrapeJobLifecycleStore
from app.data_ingestion.observation_registry.comparison import (
    RetailPriceComparisonQueryService,
    RetailPriceComparisonStatus,
)
from app.data_ingestion.observation_registry.query import RetailObservationQueryService
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.retailer_policy import (
    RetailerPolicyBlocked,
    blinkit_consumer_eligible,
    ensure_retailer_allowed,
)
from app.scrapers.blinkit.acquisition import BlinkitAcquisitionAdapter
from app.scrapers.blinkit.scraper import BlinkitScraper
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryRequest,
    CartCandidateDiscoveryService,
)
from app.services.product_search import has_supported_retailer_evidence
from app.workers.job_execution_coordinator import JobExecutionCoordinator
from app.workers.local_ingestion import LocalIngestionWorker
from app.workers.product_intelligence_runtime import ProductIntelligenceRuntime
from tests.integration.test_persisted_observation_to_cart_planning import (
    _product,
    _variant,
)
from tests.unit.data_ingestion.test_observation_registry import _observation


def test_blinkit_policy_is_not_configuration_overridable():
    with pytest.raises(RetailerPolicyBlocked) as error:
        ensure_retailer_allowed("blinkit", "product discovery")
    assert error.value.reason_code == "blinkit_commercial_authorization_required"
    assert not blinkit_consumer_eligible()


@pytest.mark.asyncio
async def test_legacy_blinkit_adapter_denies_before_scraper_call():
    class ExplodingScraper:
        async def acquire_search(self, query):
            raise AssertionError("network boundary reached")

    with pytest.raises(RetailerPolicyBlocked):
        await BlinkitAcquisitionAdapter(ExplodingScraper()).acquire_search(
            query="milk", evaluation_scope="test"
        )


@pytest.mark.asyncio
async def test_blinkit_scraper_denies_before_http_or_browser():
    scraper = BlinkitScraper()
    with pytest.raises(RetailerPolicyBlocked):
        await scraper.acquire_search("milk")


def test_real_blinkit_observation_is_not_consumer_eligible():
    observation = SimpleNamespace(
        raw_artifact_reference=SimpleNamespace(
            source_reference="https://api.quickcommerceapi.com/v1/search",
            artifact_id="real-artifact",
            content_digest="real-digest",
            storage_reference="raw/real",
            platform="BLINKIT",
            provider_id="quickcommerce",
        ),
        platform_identifiers=(("retailer_product_id", "19512"),),
        parser_version="provider-v1",
        normalization_version="normalizer-v1",
        completeness=SimpleNamespace(basis="provider-capture"),
        platform=SimpleNamespace(value="BLINKIT"),
    )
    assert not has_supported_retailer_evidence("BLINKIT", observation)


def test_other_retailer_policy_is_not_blocked():
    ensure_retailer_allowed("ZEpto", "product discovery")


@pytest.mark.parametrize(
    "identifier",
    (
        "BLINKIT",
        "blinkit",
        "blinkit.com",
        "www.blinkit.com",
        "https://blinkit.com/s/?q=milk",
        "blinkit-gurugram",
        "blinkit_provider",
    ),
)
def test_blinkit_identifiers_are_blocked(identifier):
    with pytest.raises(RetailerPolicyBlocked):
        ensure_retailer_allowed(identifier, "test")


@pytest.mark.parametrize(
    "identifier",
    ("ZEPTO", "zepto", "INSTAMART", "BIGBASKET", "FLIPKART_MINUTES", "blinkit.test"),
)
def test_unrelated_identifiers_are_not_blocked(identifier):
    ensure_retailer_allowed(identifier, "test")


def _blinkit_job() -> ScrapeJob:
    return ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "milk"),)),
        capture_context=CaptureContext(
            country_code="IN",
            currency_code="INR",
            locale="en-IN",
            location_scope="blr",
            session_scope="s",
        ),
        parser_policy_version="blinkit-parser-v1",
        normalization_policy_version="normalizer-v1",
        downstream_mode=DownstreamMode.NONE,
        job_contract_version="j1",
    )


class _ExplodingAcquisition:
    async def acquire_search(self, **kwargs):
        raise AssertionError("acquisition boundary must not be reached")


class _ExplodingStore:
    def store(self, *args, **kwargs):
        raise AssertionError("artifact storage must not be reached")


@pytest.mark.asyncio
async def test_local_ingestion_worker_blocks_blinkit_before_acquisition():
    worker = LocalIngestionWorker(
        acquisition=_ExplodingAcquisition(),
        artifact_store=_ExplodingStore(),
    )

    result = await worker.execute(_blinkit_job())

    assert result.parsed_batch is None
    assert result.artifact_reference is None
    assert result.failed_stage == "policy_blocked"
    assert result.attempt.outcome is AttemptOutcome.BLOCKED
    assert result.attempt.failure is not None
    assert result.attempt.failure.category is FailureCategory.POLICY_BLOCKED
    assert result.attempt.failure.retryable is False


@pytest.mark.asyncio
async def test_runtime_blocks_blinkit_before_normalization():
    runtime = ProductIntelligenceRuntime.__new__(ProductIntelligenceRuntime)
    worker_result = SimpleNamespace(job_id=_blinkit_job().job_id)

    result = await runtime.execute_worker_result(_blinkit_job(), worker_result)

    assert result.status == "policy_blocked"
    assert result.rationale == ("blinkit_commercial_authorization_required",)


@pytest.mark.asyncio
async def test_coordinator_persists_blocked_lifecycle_for_blinkit(tmp_path):
    lifecycle_store = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path / "lifecycle")
    worker = LocalIngestionWorker(
        acquisition=_ExplodingAcquisition(),
        artifact_store=_ExplodingStore(),
    )
    coordinator = JobExecutionCoordinator(
        ingestion_worker=worker,
        product_intelligence_runtime=ProductIntelligenceRuntime.__new__(
            ProductIntelligenceRuntime
        ),
        lifecycle_store=lifecycle_store,
    )

    result = await coordinator.execute(_blinkit_job())

    assert result.status == "policy_blocked"
    assert lifecycle_store.get_current_state(_blinkit_job().job_id) is JobState.BLOCKED
    attempt = lifecycle_store.get_attempt(
        _blinkit_job().job_id, result.worker_result.attempt.attempt_id
    )
    assert attempt is not None
    assert attempt.outcome is AttemptOutcome.BLOCKED
    assert attempt.failure is not None
    assert attempt.failure.category is FailureCategory.POLICY_BLOCKED


def _platform_observation(
    platform: Platform,
    source_id: str,
    *,
    price_minor: int = 10000,
):
    base = _observation(source_id)
    artifact = base.raw_artifact_reference.model_copy(update={"platform": platform})
    return base.model_copy(
        update={
            "platform": platform,
            "source_record_id": source_id,
            "raw_artifact_reference": artifact,
            "observed_selling_price": Money(currency="INR", minor_units=price_minor),
            "tax_status": TaxStatus.INCLUDED,
        }
    )


def _serving_registries(tmp_path, observations):
    observation_registry = FilesystemObservationRegistry(tmp_path / "observations")
    association_registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(
            root_dir=tmp_path / "associations"
        )
    )
    for observation in observations:
        observation_registry.register(observation)
        association_registry.register(
            CanonicalListingAssociation(
                observation_id=observation.observation_id,
                platform=observation.platform.value,
                platform_listing_id=observation.source_record_id,
                canonical_product_id="product-1",
                canonical_variant_id="variant-1",
            )
        )
    return observation_registry, association_registry


def test_historical_blinkit_observation_is_preserved_but_not_served(tmp_path):
    blinkit = _platform_observation(Platform.BLINKIT, "blinkit-listing")
    observation_registry, association_registry = _serving_registries(
        tmp_path, [blinkit]
    )
    query = RetailObservationQueryService(
        observation_registry=observation_registry,
        association_registry=association_registry,
    )

    # The durable record remains available for audit.
    assert observation_registry.get(blinkit.observation_id) == blinkit

    # It is not exposed as a usable observation or price comparison.
    assert query.list_observations() == ()
    assert query.get_observation(blinkit.observation_id) is None
    comparison = RetailPriceComparisonQueryService(query).compare("variant-1")
    assert comparison.status is RetailPriceComparisonStatus.NO_COMPARABLE_OBSERVATIONS
    assert comparison.observations == ()


def test_unrelated_retailer_observations_are_still_served(tmp_path):
    blinkit = _platform_observation(Platform.BLINKIT, "blinkit-listing")
    zepto = _platform_observation(Platform.ZEPTO, "zepto-listing")
    observation_registry, association_registry = _serving_registries(
        tmp_path, [blinkit, zepto]
    )
    query = RetailObservationQueryService(
        observation_registry=observation_registry,
        association_registry=association_registry,
    )

    records = query.list_observations()

    assert tuple(record.observation.platform for record in records) == (Platform.ZEPTO,)
    comparison = RetailPriceComparisonQueryService(query).compare("variant-1")
    assert comparison.status is RetailPriceComparisonStatus.COMPLETED
    assert tuple(item.platform for item in comparison.observations) == ("ZEPTO",)


def test_blinkit_listing_is_excluded_from_cart_candidate_discovery(tmp_path):
    catalog = FilesystemAuthoritativeCatalog(
        store=CatalogFilesystemStore(root_dir=tmp_path / "catalog")
    )
    catalog.register_product(_product())
    catalog.register_variant(_variant())
    blinkit = _platform_observation(Platform.BLINKIT, "blinkit-listing")
    observation_registry, association_registry = _serving_registries(
        tmp_path, [blinkit]
    )
    discovery = CartCandidateDiscoveryService(
        catalog=catalog,
        association_registry=association_registry,
        observation_registry=observation_registry,
    )

    result = discovery.discover(
        CartCandidateDiscoveryRequest(
            items=(
                {
                    "item_id": "item-1",
                    "quantity": 1,
                    "canonical_product_id": "product-amul-taaza",
                    "canonical_variant_id": "variant-amul-taaza-500ml",
                },
            )
        )
    )

    assert result.items[0].candidates == ()
    assert result.items[0].status.value == "no_candidates"
    # Historical evidence is retained for audit.
    assert observation_registry.get(blinkit.observation_id) is not None
