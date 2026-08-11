from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.product_intelligence.candidate_generation import (
    CandidateGenerationRequest,
    DeterministicCandidateGenerationService,
)
from app.product_intelligence.catalog import (
    CatalogConflictError,
    CatalogValidationError,
    DeterministicCandidateCatalogSnapshotBuilder,
    FilesystemAuthoritativeCatalog,
)
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.product_intelligence.catalog.types import CatalogState
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
    IdentityStatus,
    ListingObservation,
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


def _measurement(amount: str, unit: str, dimension: QuantityDimension) -> Measurement:
    return Measurement(
        value=Decimal(amount),
        unit=unit,
        dimension=dimension,
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
            content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
            total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
            packaging_form="pouch",
            component_set=[],
            pack_configuration_status=pack_status,
        ),
        lifecycle_status=lifecycle_status,
        catalog_revision="rev-1",
    )


def _listing() -> PlatformListing:
    return PlatformListing(
        platform="blinkit",
        platform_listing_id="listing-1",
        raw_title="Amul Taaza Milk",
        raw_quantity_text="500 ml",
        raw_category_text="milk",
    )


def _observation() -> ListingObservation:
    return ListingObservation(
        platform_listing_id="listing-1",
        displayed_price="31",
        reference_price="35",
        offer_text=None,
        availability_signal="in_stock",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="parser-v1",
        source_artifact_reference="artifact-1",
        capture_context_reference="context-1",
    )


def _catalog(tmp_path) -> FilesystemAuthoritativeCatalog:
    return FilesystemAuthoritativeCatalog(
        store=CatalogFilesystemStore(root_dir=tmp_path / "catalog")
    )


def _run(coro):
    return asyncio.run(coro)


def test_product_registration_persistence_and_reload(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    product = _product()

    registered = catalog.register_product(product)

    assert registered == product
    assert catalog.get_product("product-1") == product

    reloaded = _catalog(tmp_path)
    assert reloaded.get_product("product-1") == product


def test_duplicate_product_is_idempotent_and_conflicting_product_fails_closed(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    product = _product()
    catalog.register_product(product)

    duplicate = catalog.register_product(product.model_copy(deep=True))
    assert duplicate == product

    with pytest.raises(CatalogConflictError):
        catalog.register_product(
            product.model_copy(update={"canonical_display_name": "Different"}, deep=True)
        )


def test_invalid_product_rejected(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    with pytest.raises(CatalogValidationError):
        catalog.register_product(_product(identity_status=IdentityStatus.provisional))

    with pytest.raises(CatalogValidationError):
        catalog.register_product(_product(review_state="unreviewed"))

    with pytest.raises(CatalogValidationError):
        catalog.register_product(_product(lifecycle_status=ProductLifecycleStatus.discontinued))


def test_variant_registration_persistence_and_reload(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    product = _product()
    variant = _variant()
    catalog.register_product(product)

    registered = catalog.register_variant(variant)

    assert registered == variant
    assert catalog.get_variant("variant-1") == variant

    reloaded = _catalog(tmp_path)
    assert reloaded.get_variant("variant-1") == variant


def test_variant_registration_requires_parent_and_fails_for_conflicts(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    with pytest.raises(CatalogValidationError):
        catalog.register_variant(_variant())

    catalog.register_product(_product())
    variant = _variant()
    catalog.register_variant(variant)

    with pytest.raises(CatalogConflictError):
        catalog.register_variant(
            variant.model_copy(update={"catalog_revision": "rev-2"}, deep=True)
        )


def test_invalid_variant_rejected(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    catalog.register_product(_product())
    with pytest.raises(CatalogValidationError):
        catalog.register_variant(_variant(identity_status=IdentityStatus.provisional))

    with pytest.raises(CatalogValidationError):
        catalog.register_variant(
            _variant(lifecycle_status=VariantLifecycleStatus.discontinued)
        )

    with pytest.raises(CatalogValidationError):
        catalog.register_variant(_variant(pack_status="partial"))


def test_snapshot_builder_filters_ineligible_entities_and_sorts_deterministically(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    eligible_product_a = _product("product-a")
    eligible_product_b = _product("product-b")
    unapproved_product = _product("product-unapproved", review_state="reviewed")
    inactive_product = _product(
        "product-inactive", lifecycle_status=ProductLifecycleStatus.discontinued
    )
    eligible_variant_a = _variant("variant-a", product_id="product-a")
    eligible_variant_b = _variant("variant-b", product_id="product-b")
    unapproved_variant = _variant(
        "variant-unapproved", product_id="product-a", identity_status=IdentityStatus.provisional
    )
    inactive_variant = _variant(
        "variant-inactive", product_id="product-b", lifecycle_status=VariantLifecycleStatus.discontinued
    )

    state = CatalogState(
        products=(
            eligible_product_b,
            unapproved_product,
            inactive_product,
            eligible_product_a,
        ),
        variants=(
            eligible_variant_b,
            inactive_variant,
            unapproved_variant,
            eligible_variant_a,
        ),
    )
    snapshot = DeterministicCandidateCatalogSnapshotBuilder().build(state)

    assert [product.canonical_product_id for product in snapshot.products] == [
        "product-a",
        "product-b",
    ]
    assert [variant.canonical_variant_id for variant in snapshot.variants] == [
        "variant-a",
        "variant-b",
    ]


def test_snapshot_builder_fail_closed_on_orphan_and_duplicate_conflict(tmp_path) -> None:
    state = CatalogState(products=(_product(),), variants=(_variant(),))

    orphan_state = state.__class__(
        products=state.products,
        variants=(_variant("variant-orphan", product_id="missing"),),
    )
    with pytest.raises(CatalogConflictError):
        DeterministicCandidateCatalogSnapshotBuilder().build(orphan_state)

    duplicate_state = state.__class__(
        products=(
            state.products[0],
            state.products[0].model_copy(
                update={"canonical_display_name": "Different"}, deep=True
            ),
        ),
        variants=state.variants,
    )
    with pytest.raises(CatalogConflictError):
        DeterministicCandidateCatalogSnapshotBuilder().build(duplicate_state)


def test_empty_catalog_produces_empty_snapshot(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    snapshot = DeterministicCandidateCatalogSnapshotBuilder().build(catalog.load_state())

    assert snapshot.products == ()
    assert snapshot.variants == ()


def test_snapshot_can_feed_existing_candidate_generation(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    catalog.register_product(_product())
    catalog.register_variant(_variant())

    snapshot = DeterministicCandidateCatalogSnapshotBuilder().build(catalog.load_state())
    generator = DeterministicCandidateGenerationService(snapshot)
    request = CandidateGenerationRequest(
        platform_listing=_listing(),
        listing_observation=_observation(),
        evidence_references=[],
    )

    response = _run(generator.generate(request))

    assert [candidate.canonical_product_id for candidate in response.product_candidates] == [
        "product-1"
    ]
    assert [candidate.canonical_variant_id for candidate in response.variant_candidates] == [
        "variant-1"
    ]
