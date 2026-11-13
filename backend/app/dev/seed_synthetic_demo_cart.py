"""Generate the deterministic, retailer-independent Cartel Demo catalog.

The generator writes only into the dedicated synthetic dataset root supplied by
the caller.  It never contacts a retailer, never invokes a retailer adapter, and
never creates checkout, fee, tax, serviceability, or payment evidence.

Every observation is marked with ``synthetic-`` provenance and a
``synthetic://`` source reference, so the live-evidence gates reject it.  Only an
application started with ``DEMO_FIXTURES_ENABLED=true`` exposes it, and it does
so with an explicit ``synthetic_demo`` evidence class.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.core.config import get_settings
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.enums import (
    CaptureType,
    CompletenessState,
    TaxStatus,
)
from app.data_ingestion.observation_registry.filesystem import (
    FilesystemObservationRegistry,
)
from app.data_ingestion.types import (
    NormalizedObservation,
    ObservationCompleteness,
    RawArtifactReference,
)
from app.demo_catalog import (
    SYNTHETIC_DATASET_REVISION,
    SYNTHETIC_DISPLAY_BRAND,
    SYNTHETIC_NORMALIZATION_VERSION,
    SYNTHETIC_PARSER_VERSION,
    SYNTHETIC_PLATFORM,
    SYNTHETIC_PROVENANCE_BASIS,
    synthetic_source_reference,
)
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.product_intelligence.catalog.types import AuthoritativeCatalogRecord
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
    EvidenceReference,
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

SYNTHETIC_CAPTURE_TIMESTAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)
DEFAULT_DEMO_DATA_DIR = Path("data") / "demo_catalog"


@dataclass(frozen=True)
class SyntheticListing:
    suffix: str
    minor_units: int
    availability: str | None


@dataclass(frozen=True)
class SyntheticVariant:
    slug: str
    product_slug: str
    pack_label: str
    amount: str
    unit: str
    dimension: QuantityDimension
    packaging_form: str
    listings: tuple[SyntheticListing, ...]


@dataclass(frozen=True)
class SyntheticProduct:
    slug: str
    display_name: str
    product_type: str
    category_id: str
    category_path: str
    identity_attribute: tuple[str, str]
    variants: tuple[SyntheticVariant, ...]


SYNTHETIC_CATALOG: tuple[SyntheticProduct, ...] = (
    SyntheticProduct(
        slug="milk",
        display_name="Cartel Demo Toned Milk",
        product_type="milk",
        category_id="cartel-demo-dairy",
        category_path="Cartel Demo > Dairy",
        identity_attribute=("milk_type", "toned"),
        variants=(
            SyntheticVariant(
                slug="milk-500ml",
                product_slug="milk",
                pack_label="500 ml",
                amount="500",
                unit="ml",
                dimension=QuantityDimension.volume,
                packaging_form="pouch",
                listings=(
                    SyntheticListing("a", 2800, "available"),
                    SyntheticListing("b", 2950, "available"),
                ),
            ),
            SyntheticVariant(
                slug="milk-1l",
                product_slug="milk",
                pack_label="1 l",
                amount="1",
                unit="l",
                dimension=QuantityDimension.volume,
                packaging_form="pouch",
                listings=(
                    SyntheticListing("a", 5400, "available"),
                    SyntheticListing("b", 5600, "unavailable"),
                ),
            ),
        ),
    ),
    SyntheticProduct(
        slug="atta",
        display_name="Cartel Demo Whole Wheat Atta",
        product_type="flour",
        category_id="cartel-demo-staples",
        category_path="Cartel Demo > Staples",
        identity_attribute=("grain", "whole wheat"),
        variants=(
            SyntheticVariant(
                slug="atta-1kg",
                product_slug="atta",
                pack_label="1 kg",
                amount="1",
                unit="kg",
                dimension=QuantityDimension.mass,
                packaging_form="bag",
                listings=(
                    SyntheticListing("a", 6500, "available"),
                    SyntheticListing("b", 6800, None),
                ),
            ),
            SyntheticVariant(
                slug="atta-5kg",
                product_slug="atta",
                pack_label="5 kg",
                amount="5",
                unit="kg",
                dimension=QuantityDimension.mass,
                packaging_form="bag",
                listings=(
                    SyntheticListing("a", 29500, "available"),
                    SyntheticListing("b", 30500, "available"),
                ),
            ),
        ),
    ),
    SyntheticProduct(
        slug="rice",
        display_name="Cartel Demo Basmati Rice",
        product_type="rice",
        category_id="cartel-demo-staples",
        category_path="Cartel Demo > Staples",
        identity_attribute=("grain", "basmati"),
        variants=(
            SyntheticVariant(
                slug="rice-1kg",
                product_slug="rice",
                pack_label="1 kg",
                amount="1",
                unit="kg",
                dimension=QuantityDimension.mass,
                packaging_form="bag",
                listings=(
                    SyntheticListing("a", 12000, "unavailable"),
                    SyntheticListing("b", 12500, "available"),
                ),
            ),
            SyntheticVariant(
                slug="rice-5kg",
                product_slug="rice",
                pack_label="5 kg",
                amount="5",
                unit="kg",
                dimension=QuantityDimension.mass,
                packaging_form="bag",
                listings=(
                    SyntheticListing("a", 55000, "available"),
                    SyntheticListing("b", 57000, "available"),
                ),
            ),
        ),
    ),
    SyntheticProduct(
        slug="oil",
        display_name="Cartel Demo Sunflower Oil",
        product_type="oil",
        category_id="cartel-demo-staples",
        category_path="Cartel Demo > Staples",
        identity_attribute=("oil_type", "sunflower"),
        variants=(
            SyntheticVariant(
                slug="oil-1l",
                product_slug="oil",
                pack_label="1 l",
                amount="1",
                unit="l",
                dimension=QuantityDimension.volume,
                packaging_form="bottle",
                listings=(
                    SyntheticListing("a", 14000, "available"),
                    SyntheticListing("b", 14500, "available"),
                ),
            ),
            SyntheticVariant(
                slug="oil-2l",
                product_slug="oil",
                pack_label="2 l",
                amount="2",
                unit="l",
                dimension=QuantityDimension.volume,
                packaging_form="bottle",
                listings=(
                    SyntheticListing("a", 27000, "available"),
                    SyntheticListing("b", 28000, None),
                ),
            ),
        ),
    ),
)


def product_id(slug: str) -> str:
    return f"cartel-demo-product-{slug}"


def variant_id(slug: str) -> str:
    return f"cartel-demo-variant-{slug}"


def listing_id(variant_slug: str, suffix: str) -> str:
    return f"cartel-demo-listing-{variant_slug}-{suffix}"


def _pack_configuration(variant: SyntheticVariant) -> PackConfiguration:
    return PackConfiguration(
        pack_kind=PackKind.single_unit,
        consumer_unit_count=1,
        content_per_consumer_unit=Measurement(
            value=Decimal(variant.amount),
            unit=variant.unit,
            dimension=variant.dimension,
            content_basis="net_content",
            assertion_status="asserted",
        ),
        total_declared_content=Measurement(
            value=Decimal(variant.amount),
            unit=variant.unit,
            dimension=variant.dimension,
            content_basis="net_content",
            assertion_status="asserted",
        ),
        packaging_form=variant.packaging_form,
        pack_configuration_status="complete",
    )


def _observation(
    *,
    variant: SyntheticVariant,
    product: SyntheticProduct,
    listing: SyntheticListing,
) -> NormalizedObservation:
    record_id = listing_id(variant.slug, listing.suffix)
    price_text = f"INR {listing.minor_units // 100}.{listing.minor_units % 100:02d}"
    return NormalizedObservation(
        platform=SYNTHETIC_PLATFORM,
        source_record_id=record_id,
        raw_artifact_reference=RawArtifactReference(
            artifact_id=f"synthetic-artifact-{record_id}",
            job_id="synthetic-demo-job",
            attempt_id="synthetic-demo-attempt",
            platform=SYNTHETIC_PLATFORM,
            capture_type=CaptureType.PRODUCT_DETAIL,
            content_digest=f"synthetic-digest-{record_id}",
            storage_reference="synthetic-demo-catalog",
            content_type="application/json",
            capture_timestamp=SYNTHETIC_CAPTURE_TIMESTAMP,
            source_reference=synthetic_source_reference(record_id),
        ),
        normalized_name=f"{product.display_name} {variant.pack_label}",
        normalized_quantity=variant.pack_label,
        normalized_category=product.category_path,
        platform_identifiers=(("synthetic_listing_id", record_id),),
        observed_price_text=price_text,
        availability_signal=listing.availability,
        observed_selling_price=Money(
            currency="INR", minor_units=listing.minor_units
        ),
        tax_status=TaxStatus.UNKNOWN,
        evidence_references=(
            EvidenceReference(
                source_type="synthetic_catalog",
                source_id=record_id,
                note="Cartel Demo deterministic synthetic catalog entry",
            ),
        ),
        field_references=(),
        completeness=ObservationCompleteness(
            state=CompletenessState.COMPLETE,
            scope_reference=record_id,
            basis=SYNTHETIC_PROVENANCE_BASIS,
        ),
        parser_version=SYNTHETIC_PARSER_VERSION,
        normalization_version=SYNTHETIC_NORMALIZATION_VERSION,
    )


def seed_synthetic_demo_catalog(
    root: Path,
    *,
    reset: bool = True,
) -> tuple[Product, ...]:
    """Write the synthetic catalog, associations, and observations under ``root``.

    ``root`` is the application ``data_dir``.  The generated tree therefore lives
    at ``<root>/product_intelligence/...`` and can be selected with ``DATA_DIR``.
    """

    product_intelligence_root = root / "product_intelligence"
    if reset:
        shutil.rmtree(product_intelligence_root, ignore_errors=True)

    observations = FilesystemObservationRegistry(
        root_dir=product_intelligence_root / "observations"
    )
    associations = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(
            root_dir=product_intelligence_root / "catalog"
        )
    )
    products: list[Product] = []
    variants: list[ProductVariant] = []

    for product in SYNTHETIC_CATALOG:
        canonical_product_id = product_id(product.slug)
        products.append(
            Product(
                canonical_product_id=canonical_product_id,
                product_identity_status=IdentityStatus.established,
                brand_reference=BrandReference(
                    canonical_brand_name=SYNTHETIC_DISPLAY_BRAND,
                    display_label=SYNTHETIC_DISPLAY_BRAND,
                    is_unknown=False,
                ),
                product_type=product.product_type,
                canonical_display_name=product.display_name,
                identity_attributes=[
                    AttributeAssertion(
                        name=product.identity_attribute[0],
                        value=product.identity_attribute[1],
                        role="identity_critical",
                        assertion_status="asserted",
                    )
                ],
                canonical_category_reference=CategoryReference(
                    category_id=product.category_id,
                    category_path=product.category_path,
                    taxonomy_version=SYNTHETIC_DATASET_REVISION,
                    review_state="approved",
                ),
                lifecycle_status=ProductLifecycleStatus.active,
                catalog_revision=SYNTHETIC_DATASET_REVISION,
            )
        )
        for variant in product.variants:
            canonical_variant_id = variant_id(variant.slug)
            variants.append(
                ProductVariant(
                    canonical_variant_id=canonical_variant_id,
                    canonical_product_id=canonical_product_id,
                    variant_identity_status=IdentityStatus.established,
                    variant_identity_attributes=[
                        AttributeAssertion(
                            name="pack_size",
                            value=variant.pack_label,
                            role="identity_critical",
                            assertion_status="asserted",
                        )
                    ],
                    pack_configuration=_pack_configuration(variant),
                    lifecycle_status=VariantLifecycleStatus.active,
                    catalog_revision=SYNTHETIC_DATASET_REVISION,
                )
            )
            for listing in variant.listings:
                observation = observations.register(
                    _observation(variant=variant, product=product, listing=listing)
                )
                associations.register(
                    CanonicalListingAssociation(
                        observation_id=observation.observation_id,
                        platform=SYNTHETIC_PLATFORM.value,
                        platform_listing_id=listing_id(variant.slug, listing.suffix),
                        canonical_product_id=canonical_product_id,
                        canonical_variant_id=canonical_variant_id,
                    )
                )

    CatalogFilesystemStore(root_dir=product_intelligence_root / "catalog").save(
        AuthoritativeCatalogRecord(products=products, variants=variants)
    )
    return tuple(products)


def main() -> None:
    settings = get_settings()
    if settings.app_env == "production":
        raise RuntimeError(
            "synthetic demo catalog seeding is disabled in production"
        )
    products = seed_synthetic_demo_catalog(settings.data_dir)
    print(
        "seeded synthetic Cartel Demo catalog: "
        + ", ".join(product.canonical_product_id for product in products)
    )


if __name__ == "__main__":
    main()
