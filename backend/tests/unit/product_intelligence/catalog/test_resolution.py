from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.data_ingestion import (
    CaptureType,
    CompletenessState,
    NormalizedObservation,
    ObservationCompleteness,
    ObservationFieldReference,
    Platform,
    RawArtifactReference,
)
from app.product_intelligence.catalog import (
    CanonicalListingAssociation,
    CatalogConflictError,
    DeterministicCanonicalListingResolver,
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
    FilesystemAuthoritativeCatalog,
    ListingResolutionStatus,
)
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.product_intelligence.catalog.types import CatalogState
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


def _measurement(amount: str, unit: str) -> Measurement:
    return Measurement(
        value=Decimal(amount), unit=unit, dimension=QuantityDimension.volume,
        content_basis="net_content", assertion_status="asserted",
    )


def _product(product_id: str = "product-1", **updates) -> Product:
    return Product(
        canonical_product_id=product_id,
        product_identity_status=updates.get("identity_status", IdentityStatus.established),
        brand_reference=BrandReference(canonical_brand_name="Amul", display_label="Amul"),
        product_type="milk",
        canonical_display_name=updates.get("name", "Amul Taaza Milk"),
        identity_attributes=[AttributeAssertion(name="milk_type", value="toned", role="identity_critical")],
        canonical_category_reference=CategoryReference(
            category_id=updates.get("category", "dairy-milk"), review_state=updates.get("review_state", "approved")
        ),
        lifecycle_status=updates.get("lifecycle", ProductLifecycleStatus.active),
        catalog_revision="rev-1",
    )


def _variant(variant_id: str = "variant-1", product_id: str = "product-1", **updates) -> ProductVariant:
    measurement = _measurement(updates.get("amount", "500"), updates.get("unit", "ml"))
    return ProductVariant(
        canonical_variant_id=variant_id,
        canonical_product_id=product_id,
        variant_identity_status=updates.get("identity_status", IdentityStatus.established),
        variant_identity_attributes=[],
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.single_unit, consumer_unit_count=1,
            content_per_consumer_unit=measurement, total_declared_content=measurement,
            packaging_form="pouch", pack_configuration_status=updates.get("pack_status", "complete"),
        ),
        lifecycle_status=updates.get("lifecycle", VariantLifecycleStatus.active), catalog_revision="rev-1",
    )


def _observation(name: str = "Amul Taaza Milk", category: str = "dairy-milk", quantity: str = "500 ml") -> NormalizedObservation:
    evidence = {
        "source_type": "raw_artifact", "source_id": "artifact-1",
    }
    return NormalizedObservation(
        platform=Platform.BLINKIT, source_record_id="listing-1",
        raw_artifact_reference=RawArtifactReference(
            artifact_id="artifact-1", job_id="job-1", attempt_id="attempt-1", platform=Platform.BLINKIT,
            capture_type=CaptureType.SEARCH_RESULTS, content_digest="digest", storage_reference="opaque",
            content_type="text/html", capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            source_reference="https://example.test",
        ), normalized_name=name, normalized_quantity=quantity, normalized_category=category,
        evidence_references=(evidence,), field_references=(ObservationFieldReference(evidence_reference=evidence, locator="name"),),
        completeness=ObservationCompleteness(state=CompletenessState.COMPLETE, scope_reference="scope", basis="complete"),
        parser_version="parser-v1", normalization_version="normalizer-v1",
    )


def _resolver() -> DeterministicCanonicalListingResolver:
    return DeterministicCanonicalListingResolver(
        product_observation_key=lambda observation: (observation.normalized_name, observation.normalized_category),
        product_catalog_key=lambda product: (product.canonical_display_name, product.canonical_category_reference.category_id),
        variant_observation_key=lambda observation, product: tuple(observation.normalized_quantity.split(" ")),
        variant_catalog_key=lambda variant: (str(variant.pack_configuration.total_declared_content.value), variant.pack_configuration.total_declared_content.unit),
    )


def test_exact_product_variant_association_from_persisted_catalog(tmp_path) -> None:
    catalog = FilesystemAuthoritativeCatalog(store=CatalogFilesystemStore(root_dir=tmp_path / "catalog"))
    catalog.register_product(_product())
    catalog.register_variant(_variant())

    result = _resolver().resolve(_observation(), catalog.load_state())

    assert result.status is ListingResolutionStatus.mapped
    assert result.association is not None
    assert result.association.canonical_product_id == "product-1"
    assert result.association.canonical_variant_id == "variant-1"


def test_unresolved_and_ambiguous_are_explicit() -> None:
    resolver = _resolver()
    state = CatalogState(products=(_product("product-1"), _product("product-2")), variants=(_variant(),))
    assert resolver.resolve(_observation(category="missing"), state).status is ListingResolutionStatus.unresolved
    assert resolver.resolve(_observation(), state).status is ListingResolutionStatus.ambiguous


def test_variant_wrong_parent_is_conflicting() -> None:
    state = CatalogState(products=(_product(), _product("product-2", name="Different Milk")), variants=(_variant(product_id="product-2"),))
    result = _resolver().resolve(_observation(), state)
    assert result.status is ListingResolutionStatus.conflicting


def test_ineligible_or_provisional_entities_are_not_resolved() -> None:
    resolver = _resolver()
    assert resolver.resolve(_observation(), CatalogState(products=(_product(identity_status=IdentityStatus.provisional),), variants=())).status is ListingResolutionStatus.unresolved
    assert resolver.resolve(_observation(), CatalogState(products=(_product(),), variants=(_variant(identity_status=IdentityStatus.provisional),))).status is ListingResolutionStatus.unresolved
    assert resolver.resolve(_observation(), CatalogState(products=(_product(lifecycle=ProductLifecycleStatus.discontinued),), variants=())).status is ListingResolutionStatus.unresolved


def test_no_name_only_or_quantity_equivalence_inference() -> None:
    resolver = _resolver()
    assert resolver.resolve(_observation(category="other"), CatalogState(products=(_product(),), variants=(_variant(),))).status is ListingResolutionStatus.unresolved
    assert resolver.resolve(_observation(quantity="0.5 L"), CatalogState(products=(_product(),), variants=(_variant(),))).status is ListingResolutionStatus.unresolved


def test_resolution_is_deterministic_and_does_not_mutate_catalog() -> None:
    product = _product()
    variant = _variant()
    state = CatalogState(products=(product,), variants=(variant,))
    resolver = _resolver()
    first = resolver.resolve(_observation(), state)
    second = resolver.resolve(_observation().model_copy(deep=True), state)
    assert first == second
    assert state.products == (product,)
    assert state.variants == (variant,)


def test_resolved_association_persists_and_reloads_with_history(tmp_path) -> None:
    registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "catalog")
    )
    first = CanonicalListingAssociation(
        observation_id="observation-1", platform="BLINKIT", platform_listing_id="listing-1",
        canonical_product_id="product-1", canonical_variant_id="variant-1",
    )
    second = first.model_copy(update={"observation_id": "observation-2"})
    assert registry.register(first) == first
    assert registry.register(first) == first
    assert registry.register(second) == second

    reloaded = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "catalog")
    )
    assert reloaded.get("BLINKIT", "listing-1") == first
    assert reloaded.list_for_listing("BLINKIT", "listing-1") == (first, second)


def test_conflicting_association_fails_closed_without_reassignment(tmp_path) -> None:
    registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "catalog")
    )
    first = CanonicalListingAssociation(
        observation_id="observation-1", platform="BLINKIT", platform_listing_id="listing-1",
        canonical_product_id="product-1", canonical_variant_id="variant-1",
    )
    conflicting = first.model_copy(
        update={"observation_id": "observation-2", "canonical_product_id": "product-2"}
    )
    registry.register(first)
    with pytest.raises(CatalogConflictError, match="reassignment"):
        registry.register(conflicting)
