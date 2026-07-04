from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.product_intelligence.matching import DeterministicVariantMatcher
from app.product_intelligence.matching.types import MatchOutcome, VariantMatchRequest
from app.product_intelligence.models import EvidenceReference, ListingObservation, PlatformListing
from app.product_intelligence.review.service import DeterministicReviewQueueManager
from app.product_intelligence.review.types import ReviewCase, ReviewDecision, ReviewStatus


def _run(coro):
    return asyncio.run(coro)


def _listing(platform_listing_id: str, raw_title: str) -> PlatformListing:
    return PlatformListing(
        platform="blinkit",
        platform_listing_id=platform_listing_id,
        raw_title=raw_title,
        raw_quantity_text=None,
        raw_category_text="milk",
        listing_url="https://example.invalid/listing",
    )


def _observation(platform_listing_id: str) -> ListingObservation:
    return ListingObservation(
        platform_listing_id=platform_listing_id,
        displayed_price="31",
        reference_price=None,
        offer_text=None,
        availability_signal="ADD",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="parser-v1",
        source_artifact_reference="artifact-1",
        capture_context_reference="context-1",
    )


def _review_case(
    *,
    platform_listing_id: str,
    raw_title: str,
    outcome: MatchOutcome,
) -> ReviewCase:
    return ReviewCase(
        platform_listing=_listing(platform_listing_id, raw_title),
        listing_observation=_observation(platform_listing_id),
        evidence_references=[
            EvidenceReference(source_type="source_artifact", source_id="artifact-1")
        ],
        match_outcome=outcome,
    )


def _matcher_request() -> VariantMatchRequest:
    return VariantMatchRequest(
        platform_listing=_listing("listing-1", "Amul Taaza Milk"),
        listing_observation=_observation("listing-1"),
        evidence_references=[
            EvidenceReference(source_type="source_artifact", source_id="artifact-1")
        ],
        product=None,
        variant_candidates=[],
    )


def test_enqueue_of_unresolved_case_is_deterministic() -> None:
    manager = DeterministicReviewQueueManager()
    review_case = _review_case(
        platform_listing_id="listing-1",
        raw_title="Amul Taaza Milk",
        outcome=MatchOutcome.unresolved,
    )

    first_id = _run(manager.enqueue(review_case))
    second_id = _run(manager.enqueue(review_case.model_copy(deep=True)))

    assert first_id == second_id
    assert manager.get_review_case(first_id) is not None
    assert len(manager.list_review_cases()) == 1


def test_enqueue_of_ambiguous_case_is_deterministic() -> None:
    manager = DeterministicReviewQueueManager()
    review_case = _review_case(
        platform_listing_id="listing-2",
        raw_title="Amul Taaza Milk",
        outcome=MatchOutcome.ambiguous,
    )

    first_id = _run(manager.enqueue(review_case))
    second_id = _run(manager.enqueue(review_case.model_copy(deep=True)))

    assert first_id == second_id
    assert len(manager.list_review_cases()) == 1


def test_deterministic_queue_ordering_is_by_review_case_id() -> None:
    manager = DeterministicReviewQueueManager()
    review_case_a = _review_case(
        platform_listing_id="listing-a",
        raw_title="Amul Taaza Milk",
        outcome=MatchOutcome.unresolved,
    )
    review_case_b = _review_case(
        platform_listing_id="listing-b",
        raw_title="Amul Taaza Milk",
        outcome=MatchOutcome.unresolved,
    )

    id_b = _run(manager.enqueue(review_case_b))
    id_a = _run(manager.enqueue(review_case_a))

    ordered_ids = [
        case.platform_listing.platform_listing_id for case in manager.list_review_cases()
    ]

    assert ordered_ids == [
        manager.get_review_case(id_a).platform_listing.platform_listing_id,
        manager.get_review_case(id_b).platform_listing.platform_listing_id,
    ]


def test_valid_lifecycle_transition_resolves_review_case() -> None:
    manager = DeterministicReviewQueueManager()
    review_case = _review_case(
        platform_listing_id="listing-1",
        raw_title="Amul Taaza Milk",
        outcome=MatchOutcome.unresolved,
    )

    review_case_id = _run(manager.enqueue(review_case))
    _run(
        manager.resolve(
            ReviewDecision(
                review_case_id=review_case_id,
                review_status=ReviewStatus.approved,
                rationale=["human-approved"],
            )
        )
    )

    stored = manager.get_review_record(review_case_id)
    assert stored is not None
    assert stored.review_case.review_status == ReviewStatus.approved
    assert stored.decision_rationale == ("human-approved",)


def test_invalid_lifecycle_transition_fails_closed() -> None:
    manager = DeterministicReviewQueueManager()
    review_case = _review_case(
        platform_listing_id="listing-1",
        raw_title="Amul Taaza Milk",
        outcome=MatchOutcome.unresolved,
    )

    review_case_id = _run(manager.enqueue(review_case))
    _run(
        manager.resolve(
            ReviewDecision(
                review_case_id=review_case_id,
                review_status=ReviewStatus.rejected,
                rationale=["first-decision"],
            )
        )
    )

    with pytest.raises(ValueError):
        _run(
            manager.resolve(
                ReviewDecision(
                    review_case_id=review_case_id,
                    review_status=ReviewStatus.approved,
                    rationale=["second-decision"],
                )
            )
        )


def test_enqueue_rejects_non_queued_review_cases() -> None:
    manager = DeterministicReviewQueueManager()
    review_case = _review_case(
        platform_listing_id="listing-1",
        raw_title="Amul Taaza Milk",
        outcome=MatchOutcome.unresolved,
    ).model_copy(update={"review_status": ReviewStatus.in_review})

    with pytest.raises(ValueError):
        _run(manager.enqueue(review_case))


def test_review_queue_does_not_change_matcher_behavior() -> None:
    matcher = DeterministicVariantMatcher()
    request = _matcher_request()

    before = _run(matcher.match(request))

    manager = DeterministicReviewQueueManager()
    review_case = _review_case(
        platform_listing_id="listing-1",
        raw_title="Amul Taaza Milk",
        outcome=before.outcome,
    )
    review_case_id = _run(manager.enqueue(review_case))
    _run(
        manager.resolve(
            ReviewDecision(
                review_case_id=review_case_id,
                review_status=ReviewStatus.needs_more_evidence,
                rationale=["needs more evidence"],
            )
        )
    )

    after = _run(matcher.match(request))

    assert before.outcome == MatchOutcome.unresolved
    assert after.outcome == MatchOutcome.unresolved
    assert before.outcome == after.outcome
    assert before.rationale == after.rationale
