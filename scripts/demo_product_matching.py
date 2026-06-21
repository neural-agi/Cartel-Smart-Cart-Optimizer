import asyncio
from datetime import datetime, timezone
import sys
import warnings
from pathlib import Path

if sys.platform.startswith("win"):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.logging import configure_logging
from app.product_intelligence.candidate_generation import (
    CandidateCatalogSnapshot,
    CandidateGenerationRequest,
    DeterministicCandidateGenerationService,
)
from app.product_intelligence.matching import (
    DeterministicProductMatcher,
    ProductMatchRequest,
)
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
    EvidenceReference,
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


async def main() -> None:
    configure_logging(log_level="INFO", json_logs=False)

    product = Product(
        canonical_product_id="prod_amul_taaza_toned_milk",
        product_identity_status="established",
        brand_reference=BrandReference(display_label="Amul"),
        product_type="milk",
        canonical_display_name="Amul Taaza Toned Milk",
        identity_attributes=[
            AttributeAssertion(
                name="milk_type",
                value="toned",
                role="identity_critical",
            )
        ],
        canonical_category_reference=CategoryReference(category_id="milk"),
        lifecycle_status=ProductLifecycleStatus.active,
        catalog_revision="rev-1",
        evidence_references=[],
    )
    variant = ProductVariant(
        canonical_variant_id="var_amul_taaza_toned_milk_500ml",
        canonical_product_id=product.canonical_product_id,
        variant_identity_status="established",
        variant_identity_attributes=[],
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.single_unit,
            consumer_unit_count=1,
            content_per_consumer_unit=Measurement(
                value=500,
                unit="ml",
                dimension=QuantityDimension.volume,
            ),
            total_declared_content=Measurement(
                value=500,
                unit="ml",
                dimension=QuantityDimension.volume,
            ),
            packaging_form="pouch",
            component_set=[],
            pack_configuration_status="complete",
        ),
        lifecycle_status=VariantLifecycleStatus.active,
        catalog_revision="rev-1",
        evidence_references=[],
    )
    catalog = CandidateCatalogSnapshot(products=(product,), variants=(variant,))
    candidate_service = DeterministicCandidateGenerationService(catalog)
    listing = PlatformListing(
        platform="blinkit",
        platform_listing_id="blinkit_demo_milk_001",
        raw_title="Amul Taaza Toned Milk",
        raw_quantity_text="500 ml",
        raw_category_text="Milk",
        listing_url="https://blinkit.example/item/001",
    )
    observation = ListingObservation(
        platform_listing_id="blinkit_demo_milk_001",
        displayed_price="31",
        reference_price=None,
        offer_text=None,
        availability_signal="ADD",
        capture_timestamp=datetime.now(timezone.utc),
        parser_version="demo",
        source_artifact_reference="demo/raw/blinkit/milk.html",
        capture_context_reference="demo/location/new-delhi",
    )
    candidate_response = await candidate_service.generate(
        CandidateGenerationRequest(
            platform_listing=listing,
            listing_observation=observation,
            evidence_references=[
                EvidenceReference(
                    source_type="source_artifact",
                    source_id="demo/raw/blinkit/milk.html",
                )
            ],
        )
    )

    matcher = DeterministicProductMatcher()
    match_response = await matcher.match(
        ProductMatchRequest(
            platform_listing=listing,
            listing_observation=observation,
            evidence_references=[
                EvidenceReference(
                    source_type="source_artifact",
                    source_id="demo/raw/blinkit/milk.html",
                )
            ],
            product_candidates=candidate_response.product_candidates,
        )
    )

    print(f"outcome={match_response.outcome.value}")
    print(
        "selected_product="
        + (
            match_response.selected_product.canonical_product_id
            if match_response.selected_product
            else "none"
        )
    )
    for line in match_response.rationale:
        print(f"- {line}")


if __name__ == "__main__":
    asyncio.run(main())
