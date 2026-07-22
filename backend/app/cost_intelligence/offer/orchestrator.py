"""Deterministic orchestration for offer-by-offer evaluation."""

from __future__ import annotations

"""Deterministic orchestration for offer-by-offer evaluation.

This orchestrator remains separate from the fee orchestrator on purpose.
The pipeline favors explicit duplication over premature abstraction until
multiple concrete orchestrators prove stable shared behavior.
"""

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.evaluation.types import OfferEvaluationResult
from app.cost_intelligence.offer.service import OfferEvaluationService


class OfferEvaluationOrchestrator:
    """Iterate over observed offers without adding evaluation policy."""

    def __init__(self) -> None:
        self.service = OfferEvaluationService()

    def evaluate(self, context: CostContext) -> tuple[OfferEvaluationResult, ...]:
        """Evaluate every offer in its existing observation order."""
        return tuple(
            self.service.evaluate(context, offer)
            for offer in context.checkout_observation.offers
        )
