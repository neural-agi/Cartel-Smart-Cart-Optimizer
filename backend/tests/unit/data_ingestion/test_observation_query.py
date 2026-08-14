from app.data_ingestion.observation_registry import FilesystemObservationRegistry
from app.data_ingestion.observation_registry.query import RetailObservationQueryService
from app.product_intelligence.catalog import (
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from tests.unit.data_ingestion.test_observation_registry import _observation


def _association(observation) -> CanonicalListingAssociation:
    return CanonicalListingAssociation(
        observation_id=observation.observation_id,
        platform=observation.platform.value,
        platform_listing_id=observation.source_record_id,
        canonical_product_id="product-1",
        canonical_variant_id="variant-1",
    )


def _service(tmp_path) -> tuple[RetailObservationQueryService, FilesystemObservationRegistry]:
    observations = FilesystemObservationRegistry(tmp_path / "observations")
    associations = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "catalog")
    )
    return RetailObservationQueryService(
        observation_registry=observations,
        association_registry=associations,
    ), observations


def test_lists_observations_deterministically_and_preserves_missing_association(tmp_path) -> None:
    service, registry = _service(tmp_path)
    first = _observation("Bread")
    second = _observation("Milk")
    registry.register(second)
    registry.register(first)

    records = service.list_observations()

    assert tuple(record.observation.observation_id for record in records) == tuple(
        sorted((first.observation_id, second.observation_id))
    )
    assert all(record.association is None for record in records)


def test_exact_lookup_and_association_filter_survive_restart(tmp_path) -> None:
    service, registry = _service(tmp_path)
    observation = _observation()
    registry.register(observation)
    association = _association(observation)
    service.association_registry.register(association)

    reloaded_service, _ = _service(tmp_path)

    assert reloaded_service.get_observation(observation.observation_id).association == association
    assert reloaded_service.list_observations(canonical_product_id="product-1")[0].observation == observation
    assert reloaded_service.list_observations(canonical_variant_id="missing") == ()


def test_empty_query_returns_empty_results(tmp_path) -> None:
    service, _ = _service(tmp_path)
    assert service.list_observations() == ()
    assert service.get_observation("missing") is None
