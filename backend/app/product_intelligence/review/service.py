from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from app.core.logging import get_logger
from app.product_intelligence.review.interfaces import ReviewQueueManager
from app.product_intelligence.review.types import ReviewCase, ReviewDecision, ReviewStatus


logger = get_logger(__name__)


@dataclass(slots=True)
class _ReviewRecord:
    """Internal queue record for deterministic in-memory review storage."""

    review_case_id: str
    review_case: ReviewCase
    decision_rationale: tuple[str, ...] = ()


class _ReviewLifecycleManager:
    """Isolated lifecycle transition rules for review cases."""

    _TRANSITIONS: dict[ReviewStatus, frozenset[ReviewStatus]] = {
        ReviewStatus.queued: frozenset(
            {
                ReviewStatus.in_review,
                ReviewStatus.approved,
                ReviewStatus.rejected,
                ReviewStatus.needs_more_evidence,
                ReviewStatus.superseded,
            }
        ),
        ReviewStatus.in_review: frozenset(
            {
                ReviewStatus.approved,
                ReviewStatus.rejected,
                ReviewStatus.needs_more_evidence,
                ReviewStatus.superseded,
            }
        ),
        ReviewStatus.needs_more_evidence: frozenset(
            {
                ReviewStatus.in_review,
                ReviewStatus.superseded,
            }
        ),
        ReviewStatus.approved: frozenset(),
        ReviewStatus.rejected: frozenset(),
        ReviewStatus.superseded: frozenset(),
    }

    def transition(self, current: ReviewStatus, target: ReviewStatus) -> ReviewStatus:
        allowed = self._TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise ValueError(
                f"invalid review transition current={current.value} target={target.value}"
            )
        return target


class DeterministicReviewQueueManager(ReviewQueueManager):
    """Deterministic in-memory review queue with explicit lifecycle validation."""

    def __init__(self) -> None:
        self._records: dict[str, _ReviewRecord] = {}
        self._lifecycle = _ReviewLifecycleManager()

    async def enqueue(self, review_case: ReviewCase) -> str:
        self._validate_enqueue(review_case)
        review_case_id = self._review_case_id(review_case)
        if review_case_id in self._records:
            logger.info("review_case_deduplicated review_case_id=%s", review_case_id)
            return review_case_id

        stored_case = review_case.model_copy(deep=True)
        self._records[review_case_id] = _ReviewRecord(
            review_case_id=review_case_id,
            review_case=stored_case,
        )
        logger.info(
            "review_case_enqueued review_case_id=%s match_outcome=%s",
            review_case_id,
            review_case.match_outcome.value,
        )
        return review_case_id

    async def resolve(self, decision: ReviewDecision) -> None:
        record = self._records.get(decision.review_case_id)
        if record is None:
            raise KeyError(f"unknown review_case_id={decision.review_case_id}")

        resolved_status = self._lifecycle.transition(
            record.review_case.review_status,
            decision.review_status,
        )
        record.review_case = record.review_case.model_copy(
            update={"review_status": resolved_status},
            deep=True,
        )
        record.decision_rationale = tuple(decision.rationale)
        logger.info(
            "review_case_resolved review_case_id=%s review_status=%s",
            decision.review_case_id,
            resolved_status.value,
        )

    def get_review_case(self, review_case_id: str) -> ReviewCase | None:
        record = self._records.get(review_case_id)
        if record is None:
            return None
        return record.review_case.model_copy(deep=True)

    def get_review_record(self, review_case_id: str) -> _ReviewRecord | None:
        record = self._records.get(review_case_id)
        if record is None:
            return None
        return _ReviewRecord(
            review_case_id=record.review_case_id,
            review_case=record.review_case.model_copy(deep=True),
            decision_rationale=record.decision_rationale,
        )

    def list_review_cases(self) -> list[ReviewCase]:
        return [
            self._records[review_case_id].review_case.model_copy(deep=True)
            for review_case_id in sorted(self._records)
        ]

    def list_review_records(self) -> list[_ReviewRecord]:
        return [
            _ReviewRecord(
                review_case_id=record.review_case_id,
                review_case=record.review_case.model_copy(deep=True),
                decision_rationale=record.decision_rationale,
            )
            for review_case_id, record in sorted(self._records.items())
        ]

    def _validate_enqueue(self, review_case: ReviewCase) -> None:
        if review_case.review_status != ReviewStatus.queued:
            raise ValueError(
                f"review_case must be queued to enqueue, got={review_case.review_status.value}"
            )

    def _review_case_id(self, review_case: ReviewCase) -> str:
        payload = review_case.model_dump(mode="json")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        return f"review_case_{digest[:24]}"
