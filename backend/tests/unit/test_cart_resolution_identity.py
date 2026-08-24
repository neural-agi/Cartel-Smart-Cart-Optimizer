from types import SimpleNamespace

from app.services.cart_resolution import (
    CartItemResolutionRequest,
    CartItemResolutionStatus,
    CartResolutionService,
)
from app.data_ingestion.types import NormalizedObservation


class _Catalog:
    def get_variant(self, variant_id):
        return SimpleNamespace(
            canonical_variant_id=variant_id,
            canonical_product_id="product-1",
        )

    def get_product(self, product_id):
        return SimpleNamespace(canonical_product_id=product_id)


class _Associations:
    def __init__(self, variant_id):
        self.variant_id = variant_id

    def get(self, platform, listing_id):
        return SimpleNamespace(
            canonical_product_id="product-1",
            canonical_variant_id=self.variant_id,
            platform=platform,
            platform_listing_id=listing_id,
            observation_id="observation-1",
        )


class _Observations:
    def __init__(self, observation=None):
        self.observation = observation

    def get(self, observation_id):
        return self.observation


def _service(association_variant_id, observation=None):
    return CartResolutionService(
        catalog=_Catalog(),
        association_registry=_Associations(association_variant_id),
        observation_registry=_Observations(observation),
    )


def _request():
    return CartItemResolutionRequest(
        item_id="item-1",
        quantity=1,
        canonical_variant_id="variant-1",
        platform="platform-1",
        platform_listing_id="listing-1",
    )


def test_matching_dual_identity_resolves_without_reassignment() -> None:
    result = _service("variant-1")._resolve_item(_request())

    assert result.status is CartItemResolutionStatus.unresolved
    assert result.reason == "listing association references a missing observation"


def test_mismatching_dual_identity_fails_closed_deterministically() -> None:
    service = _service("variant-2")
    first = service._resolve_item(_request())
    second = service._resolve_item(_request())

    assert first.status is CartItemResolutionStatus.unresolved
    assert first.reason == "canonical Variant identity conflicts with listing association"
    assert first == second


def test_single_canonical_identity_path_remains_unchanged() -> None:
    request = CartItemResolutionRequest(
        item_id="item-1", quantity=1, canonical_variant_id="variant-1"
    )

    result = _service("variant-2")._resolve_item(request)

    assert result.status is CartItemResolutionStatus.resolved
    assert result.canonical_variant_id == "variant-1"


def test_persisted_association_only_resolution_preserves_association_identity() -> None:
    request = CartItemResolutionRequest(
        item_id="item-1", quantity=2, platform="platform-1", platform_listing_id="listing-1"
    )
    observation = NormalizedObservation.model_construct(observation_id="observation-1")
    result = _service("variant-1", observation)._resolve_item(request)

    assert result.status is CartItemResolutionStatus.resolved
    assert result.quantity == 2
    assert result.canonical_variant_id == "variant-1"
    assert result.platform_listing_id == "listing-1"
    assert result.observation_id == "observation-1"


def test_matching_dual_identity_resolves_with_valid_observation() -> None:
    result = _service(
        "variant-1", NormalizedObservation.model_construct(observation_id="observation-1")
    )._resolve_item(_request())

    assert result.status is CartItemResolutionStatus.resolved
    assert result.canonical_variant_id == "variant-1"
    assert result.observation_id == "observation-1"
