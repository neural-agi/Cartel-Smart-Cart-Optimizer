from app.cost_intelligence.shared.money import Money
from app.data_ingestion import TaxStatus
from app.data_ingestion.observation_registry.comparison import (
    RetailPriceComparisonQueryService,
    RetailPriceComparisonStatus,
)
from app.data_ingestion.observation_registry import FilesystemObservationRegistry
from app.data_ingestion.observation_registry.query import RetailObservationQueryService
from app.product_intelligence.catalog import (
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from tests.unit.data_ingestion.test_observation_registry import _observation


def _query(tmp_path, observations):
    registry = FilesystemObservationRegistry(tmp_path / "observations")
    associations = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "catalog")
    )
    for observation, variant_id in observations:
        registry.register(observation)
        associations.register(CanonicalListingAssociation(
            observation_id=observation.observation_id,
            platform=observation.platform.value,
            platform_listing_id=observation.source_record_id,
            canonical_product_id="product-1",
            canonical_variant_id=variant_id,
        ))
    return RetailPriceComparisonQueryService(RetailObservationQueryService(
        observation_registry=registry,
        association_registry=associations,
    ))


def _priced(source_id: str, amount: int, *, currency: str = "INR", tax=TaxStatus.INCLUDED):
    return _observation(source_id).model_copy(update={
        "source_record_id": source_id,
        "observed_selling_price": Money(currency=currency, minor_units=amount),
        "tax_status": tax,
    })


def test_same_variant_observations_are_sorted_deterministically(tmp_path) -> None:
    query = _query(tmp_path, [
        (_priced("higher", 12000), "variant-1"),
        (_priced("lower", 10000), "variant-1"),
    ])

    result = query.compare("variant-1")

    assert result.status is RetailPriceComparisonStatus.COMPLETED
    assert [item.observed_selling_price.minor_units for item in result.observations] == [10000, 12000]


def test_missing_price_unknown_tax_unresolved_and_legacy_observations_are_excluded(tmp_path) -> None:
    query = _query(tmp_path, [
        (_observation("missing-price"), "variant-1"),
        (_priced("unknown-tax", 10000, tax=TaxStatus.UNKNOWN), "variant-1"),
        (_priced("other-variant", 9000), "variant-2"),
    ])

    result = query.compare("variant-1")

    assert result.status is RetailPriceComparisonStatus.NO_COMPARABLE_OBSERVATIONS
    assert result.observations == ()


def test_unsupported_currency_is_excluded(tmp_path) -> None:
    query = _query(tmp_path, [(_priced("usd", 1000, currency="USD"), "variant-1")])

    result = query.compare("variant-1")

    assert result.status is RetailPriceComparisonStatus.NO_COMPARABLE_OBSERVATIONS


def test_currency_mismatch_is_rejected_when_both_are_configured(tmp_path) -> None:
    query = _query(tmp_path, [
        (_priced("inr", 1000), "variant-1"),
        (_priced("usd", 1000, currency="USD"), "variant-1"),
    ])
    query.supported_currencies = frozenset({"INR", "USD"})

    result = query.compare("variant-1")

    assert result.status is RetailPriceComparisonStatus.CURRENCY_MISMATCH
