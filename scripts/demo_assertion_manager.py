from __future__ import annotations

import asyncio
import sys
import warnings
from datetime import datetime, timezone
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
from app.product_intelligence.assertions import DeterministicAssertionManager
from app.product_intelligence.assertions.types import AssertionUpdateRequest
from app.product_intelligence.matching.types import MatchOutcome
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
    EvidenceReference,
    IdentityStatus,
    ListingObservation,
    PackConfiguration,
    PackKind,
    PlatformListing,
    Product,
    ProductLifecycleStatus,
    ProductVariant,
    QuantityDimension,
    Measurement,
    VariantLifecycleStatus,
)
from app.product_intelligence.review.service import DeterministicReviewQueueManager
from app.product_intelligence.review.types import ReviewCase, ReviewDecision, ReviewStatus


def _product() -> Product:
    return Product(
        canonical_product_id="product-1",
        product_identity_status=IdentityStatus.established,
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
            review_state="approved",
        ),
        lifecycle_status=ProductLifecycleStatus.active,
        catalog_revision="rev-1",
        evidence_references=[
            EvidenceReference(source_type="catalog", source_id="product-1")
        ],
    )


def _variant() -> ProductVariant:
    return ProductVariant(
        canonical_variant_id="variant-1",
        canonical_product_id="product-1",
        variant_identity_status=IdentityStatus.established,
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
        evidence_references=[
            EvidenceReference(source_type="catalog", source_id="variant-1")
        ],
    )


async def main() -> None:
    configure_logging(log_level="INFO", json_logs=False)

    review_queue = DeterministicReviewQueueManager()
    listing = PlatformListing(
        platform="blinkit",
        platform_listing_id="blinkit-demo-001",
        raw_title="Amul Taaza Milk",
        raw_quantity_text="500 ml",
        raw_category_text="milk",
        listing_url="https://example.invalid/blinkit-demo-001",
    )
    observation = ListingObservation(
        platform_listing_id="blinkit-demo-001",
        displayed_price="31",
        reference_price="35",
        offer_text=None,
        availability_signal="ADD",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo",
        source_artifact_reference="demo/raw/blinkit/milk.html",
        capture_context_reference="demo/location/new-delhi",
    )
    review_case = ReviewCase(
        platform_listing=listing,
        listing_observation=observation,
        evidence_references=[
            EvidenceReference(
                source_type="source_artifact",
                source_id="demo/raw/blinkit/milk.html",
            )
        ],
        match_outcome=MatchOutcome.ambiguous,
    )
    review_case_id = await review_queue.enqueue(review_case)
    await review_queue.resolve(
        ReviewDecision(
            review_case_id=review_case_id,
            review_status=ReviewStatus.approved,
            rationale=["approved-for-assertion-demo"],
        )
    )

    manager = DeterministicAssertionManager()
    request = AssertionUpdateRequest(
        product=_product(),
        variant=_variant(),
        evidence_references=[
            EvidenceReference(
                source_type="review_case",
                source_id=review_case_id,
            )
        ],
        decision_references=[review_case_id],
    )

    first_response = await manager.apply(request)
    second_response = await manager.apply(request.model_copy(deep=True))

    print("accepted_review_case_id=", review_case_id)
    print("first_application=")
    print(first_response.model_dump(mode="json"))
    print("second_application_no_op=")
    print(second_response.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
