from __future__ import annotations

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
from app.product_intelligence.matching import DeterministicVariantMatcher
from app.product_intelligence.matching.types import VariantMatchRequest
from app.product_intelligence.models import EvidenceReference, ListingObservation, PlatformListing
from app.product_intelligence.review.service import DeterministicReviewQueueManager
from app.product_intelligence.review.types import ReviewCase, ReviewDecision, ReviewStatus


async def main() -> None:
    configure_logging(log_level="INFO", json_logs=False)

    matcher = DeterministicVariantMatcher()
    request = VariantMatchRequest(
        platform_listing=PlatformListing(
            platform="blinkit",
            platform_listing_id="blinkit-review-demo-001",
            raw_title="Amul Taaza Milk",
            raw_quantity_text=None,
            raw_category_text="Milk",
            listing_url="https://example.invalid/review-demo",
        ),
        listing_observation=ListingObservation(
            platform_listing_id="blinkit-review-demo-001",
            displayed_price="31",
            reference_price=None,
            offer_text=None,
            availability_signal="ADD",
            capture_timestamp=datetime.now(timezone.utc),
            parser_version="demo",
            source_artifact_reference="demo/raw/blinkit/review-demo.html",
            capture_context_reference="demo/location/new-delhi",
        ),
        evidence_references=[
            EvidenceReference(source_type="source_artifact", source_id="demo/raw/blinkit/review-demo.html")
        ],
        product=None,
        variant_candidates=[],
    )
    match_response = await matcher.match(request)

    queue = DeterministicReviewQueueManager()
    review_case = ReviewCase(
        platform_listing=request.platform_listing,
        listing_observation=request.listing_observation,
        evidence_references=request.evidence_references,
        match_outcome=match_response.outcome,
    )
    review_case_id = await queue.enqueue(review_case)

    print(f"review_case_id={review_case_id}")
    print(f"queued_outcome={match_response.outcome.value}")
    print("queued_case:")
    queued = queue.get_review_case(review_case_id)
    print(queued.model_dump(mode="json") if queued else "missing")

    await queue.resolve(
        ReviewDecision(
            review_case_id=review_case_id,
            review_status=ReviewStatus.needs_more_evidence,
            rationale=["demo_requires_more_evidence"],
        )
    )

    print("resolved_case:")
    resolved = queue.get_review_record(review_case_id)
    if resolved is None:
        print("missing")
    else:
        print(resolved.review_case.model_dump(mode="json"))
        print(f"decision_rationale={list(resolved.decision_rationale)}")


if __name__ == "__main__":
    asyncio.run(main())
