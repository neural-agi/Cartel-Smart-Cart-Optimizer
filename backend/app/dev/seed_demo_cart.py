"""Seed explicit local demo catalog data for development execution only."""

from datetime import datetime, timezone

from app.core.config import get_settings
from app.data_ingestion.enums import CaptureType, CompletenessState, Platform, TaxStatus
from app.data_ingestion.observation_registry.filesystem import FilesystemObservationRegistry
from app.data_ingestion.types import NormalizedObservation, ObservationCompleteness, RawArtifactReference
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.product_intelligence.catalog.types import AuthoritativeCatalogRecord
from app.product_intelligence.models import (
    BrandReference, CategoryReference, IdentityStatus, PackConfiguration, PackKind,
    Product, ProductLifecycleStatus, ProductVariant, VariantLifecycleStatus,
)


def main() -> None:
    settings = get_settings()
    if settings.app_env == "production":
        raise RuntimeError("demo seed is disabled in production")
    now = datetime.now(timezone.utc)
    products = []
    variants = []
    observations = FilesystemObservationRegistry(
        root_dir=settings.data_dir / "product_intelligence" / "observations"
    )
    associations = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(
            root_dir=settings.data_dir / "product_intelligence" / "catalog"
        )
    )
    for item in ("a", "b"):
        product_id = f"demo-product-{item}"
        variant_id = f"demo-variant-{item}"
        products.append(Product(
            canonical_product_id=product_id,
            product_identity_status=IdentityStatus.established,
            brand_reference=BrandReference(display_label="Demo Brand"),
            product_type="grocery",
            canonical_display_name=f"Demo Item {item.upper()}",
            canonical_category_reference=CategoryReference(
                category_id="demo-category", review_state="approved"
            ),
            lifecycle_status=ProductLifecycleStatus.active,
            catalog_revision="demo-v1",
        ))
        variants.append(ProductVariant(
            canonical_variant_id=variant_id,
            canonical_product_id=product_id,
            variant_identity_status=IdentityStatus.established,
            pack_configuration=PackConfiguration(
                pack_kind=PackKind.single_unit,
                consumer_unit_count=1,
                pack_configuration_status="complete",
            ),
            lifecycle_status=VariantLifecycleStatus.active,
            catalog_revision="demo-v1",
        ))
        for index, price in ((1, 100), (2, 110)):
            listing = f"demo-{item}-{index}"
            observation = NormalizedObservation.model_construct(
                platform=Platform.BLINKIT,
                source_record_id=listing,
                raw_artifact_reference=RawArtifactReference.model_construct(
                    artifact_id=f"demo-artifact-{item}-{index}", job_id="demo-job",
                    attempt_id="demo-attempt", platform=Platform.BLINKIT,
                    capture_type=CaptureType.SEARCH_RESULTS, content_digest="demo-digest",
                    storage_reference="development-seed", content_type="application/json",
                    capture_timestamp=now, source_reference=listing,
                ),
                normalized_name=f"Demo Item {item.upper()}",
                observed_selling_price=Money(currency="INR", minor_units=price),
                tax_status=TaxStatus.UNKNOWN,
                evidence_references=(), field_references=(),
                completeness=ObservationCompleteness(
                    state=CompletenessState.COMPLETE, scope_reference=listing,
                    basis="development-seed",
                ), parser_version="demo-v1", normalization_version="demo-v1",
            )
            observation = observations.register(observation)
            associations.register(CanonicalListingAssociation(
                observation_id=observation.observation_id,
                platform="blinkit", platform_listing_id=listing,
                canonical_product_id=product_id, canonical_variant_id=variant_id,
            ))
    CatalogFilesystemStore(
        root_dir=settings.data_dir / "product_intelligence" / "catalog"
    ).save(AuthoritativeCatalogRecord(products=products, variants=variants))
    print("seeded development demo cart: demo-product-a, demo-product-b")


if __name__ == "__main__":
    main()
