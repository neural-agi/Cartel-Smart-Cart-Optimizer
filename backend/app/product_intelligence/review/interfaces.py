from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.product_intelligence.review.types import ReviewCase, ReviewDecision


class ReviewQueueManager(ABC):
    """Abstract contract for managing review cases."""

    @abstractmethod
    async def enqueue(self, review_case: ReviewCase) -> str:
        """Add a review case and return its identifier."""

    @abstractmethod
    async def resolve(self, decision: ReviewDecision) -> None:
        """Apply a review decision."""

    @abstractmethod
    def get_review_case(self, review_case_id: str) -> ReviewCase | None:
        """Return the current queued review case, if any."""

    @abstractmethod
    def get_review_record(self, review_case_id: str) -> Any:
        """Return the current review record, if any."""
