from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.product_intelligence.catalog.types import CatalogValidationError
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
from app.retailer_data.association import GovernedRetailerAssociationService
from app.retailer_data.blinkit import BlinkitRetailerDataProvider
from app.retailer_data.persistence import FilesystemRetailerObservationStore
from app.retailer_data.types import AssociationStatus
from app.schemas.extraction import ProductAvailability, RawExtractedProduct, RawExtractionResult
from app.services.product_search import ProductSearchRequest, ProductSearchService


def _result(*, source_reference: str | None = "artifact-1") -> RawExtractionResult:
    from app.data_ingestion.types import CaptureCoverage

    return RawExtractionResult(
        platform="blinkit", parser_version="blinkit-parser-v1", source_reference=source_reference,
        extracted_at=datetime(2026, 10, 1, tzinfo=timezone.utc), product_count=1,
        evaluation_scope="query:milk", pages_evaluated=1, pagination_complete=True,
        termination_reason="complete", capture_coverage=CaptureCoverage(
            evaluation_scope="query:milk", pages_evaluated=1, pagination_complete=True,
            termination_reason="complete"
        ), products=[RawExtractedProduct(
            source_index=1, platform="blinkit", retailer_product_id="listing-1",
            product_url="https://blinkit.com/prn/milk/prid/listing-1", product_name="Milk",
            displayed_price="₹25", quantity="500 ml", stock_availability="in_stock",
            availability_status=ProductAvailability.AVAILABLE, raw_text="Milk 500 ml ₹25"
        )]
    )


def _canonical(tmp_path):
    catalog = FilesystemAuthoritativeCatalog(CatalogFilesystemStore(tmp_path / "catalog"))
    product = Product(
        canonical_product_id="product-1", product_identity_status=IdentityStatus.established,
        brand_reference=BrandReference(display_label="Brand"), product_type="milk",
        canonical_display_name="Milk", identity_attributes=[AttributeAssertion(name="brand", value="Brand", role="identity_critical")],
        canonical_category_reference=CategoryReference(category_id="dairy", review_state="approved"),
        lifecycle_status=ProductLifecycleStatus.active, catalog_revision="rev-1"
    )
    measurement = Measurement(value=Decimal("500"), unit="ml", dimension=QuantityDimension.volume, content_basis="net_content")
    variant = ProductVariant(
        canonical_variant_id="variant-1", canonical_product_id="product-1", variant_identity_status=IdentityStatus.established,
        pack_configuration=PackConfiguration(pack_kind=PackKind.single_unit, consumer_unit_count=1,
            content_per_consumer_unit=measurement, total_declared_content=measurement, pack_configuration_status="complete"),
        lifecycle_status=VariantLifecycleStatus.active, catalog_revision="rev-1"
    )
    catalog.register_product(product)
    catalog.register_variant(variant)
    registry = FilesystemCanonicalListingAssociationRegistry(FilesystemCanonicalListingAssociationStore(tmp_path / "catalog"))
    return catalog, registry


def test_blinkit_adapter_emits_provider_neutral_observation_without_canonical_identity():
    observation = BlinkitRetailerDataProvider().normalize(_result())[0]
    assert observation.provider == "blinkit"
    assert observation.retailer_listing_id == "listing-1"
    assert observation.source_artifact_reference == "artifact-1"
    assert not hasattr(observation, "canonical_variant_id")
    assert observation.listed_price is not None


def test_blinkit_adapter_uses_durable_artifact_reference_and_preserves_source_evidence():
    result = _result()
    observation = BlinkitRetailerDataProvider().normalize(
        result,
        source_artifact_reference="artifact-store://search/abc",
    )[0]

    assert observation.source_artifact_reference == "artifact-store://search/abc"
    assert observation.source_reference == result.source_reference
    assert observation.evidence_references == (
        ("retailer_artifact", "artifact-store://search/abc"),
        ("retailer_source", result.source_reference),
    )


def test_missing_source_artifact_fails_closed():
    with pytest.raises(ValueError, match="source artifact"):
        BlinkitRetailerDataProvider().normalize(_result(source_reference=None))


def test_observation_history_and_conflicts_are_preserved(tmp_path):
    observation = BlinkitRetailerDataProvider().normalize(_result())[0]
    store = FilesystemRetailerObservationStore(tmp_path / "observations")
    assert store.register(observation) == observation
    assert store.register(observation) == observation
    assert len(store.list_for_listing("blinkit", "listing-1")) == 1
    changed = observation.model_copy(update={"payload_digest": "different"})
    with pytest.raises(ValueError, match="conflicting"):
        store.register(changed)


def test_association_requires_existing_canonical_variant(tmp_path):
    catalog, registry = _canonical(tmp_path)
    observation = BlinkitRetailerDataProvider().normalize(_result())[0]
    service = GovernedRetailerAssociationService(catalog=catalog, registry=registry)
    association = service.associate(observation, canonical_variant_id="variant-1")
    assert association.canonical_variant_id == "variant-1"
    assert association.association_status == AssociationStatus.associated.value
    with pytest.raises(CatalogValidationError):
        service.associate(observation, canonical_variant_id="missing")


def test_associated_retailer_observation_reaches_governed_search(tmp_path):
    catalog, registry = _canonical(tmp_path)
    observation = BlinkitRetailerDataProvider().normalize(_result())[0]
    FilesystemRetailerObservationStore(tmp_path / "observations").register(observation)
    association = GovernedRetailerAssociationService(catalog=catalog, registry=registry).associate(
        observation, canonical_variant_id="variant-1"
    )

    class EmptyObservationRegistry:
        def get(self, observation_id):
            return None

    result = ProductSearchService(
        catalog=catalog,
        association_registry=registry,
        observation_registry=EmptyObservationRegistry(),
        retailer_observation_store=FilesystemRetailerObservationStore(tmp_path / "observations"),
    ).search(ProductSearchRequest(query="milk"))

    assert association.association_status == AssociationStatus.associated.value
    assert len(result.items) == 1
    assert result.items[0].canonical_variant_id == "variant-1"
    assert result.items[0].platform_listing_id == "listing-1"
