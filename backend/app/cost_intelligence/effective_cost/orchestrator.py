from __future__ import annotations

"""Deterministic orchestration for effective-cost aggregation.

This orchestrator remains separate from the peer evaluators on purpose.
The pipeline favors explicit duplication over premature abstraction until
multiple concrete orchestrators prove stable shared behavior.
"""

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.effective_cost.service import EffectiveCostEvaluationService
from app.cost_intelligence.evaluation.types import (
    EffectiveCostEvaluationResult,
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
)


class EffectiveCostEvaluationOrchestrator:
    """Delegate a single aggregation step without introducing policy."""

    def __init__(self) -> None:
        self.service = EffectiveCostEvaluationService()

    def evaluate(
        self,
        context: CostContext,
        offer_results: tuple[OfferEvaluationResult, ...],
        fee_results: tuple[FeeEvaluationResult, ...],
        membership_results: tuple[MembershipEvaluationResult, ...],
    ) -> EffectiveCostEvaluationResult:
        return self.service.evaluate(
            context,
            offer_results,
            fee_results,
            membership_results,
        )
