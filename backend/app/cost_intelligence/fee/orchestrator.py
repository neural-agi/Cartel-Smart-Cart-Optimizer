from __future__ import annotations

"""Deterministic orchestration for fee-by-fee evaluation.

This orchestrator remains separate from the offer orchestrator on purpose.
The pipeline favors explicit duplication over premature abstraction until
multiple concrete orchestrators prove stable shared behavior.
"""

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.evaluation.types import FeeEvaluationResult
from app.cost_intelligence.fee.service import FeeEvaluationService


class FeeEvaluationOrchestrator:
    """Iterate over observed fees without adding evaluation policy."""

    def __init__(self) -> None:
        self.service = FeeEvaluationService()

    def evaluate(self, context: CostContext) -> tuple[FeeEvaluationResult, ...]:
        """Evaluate every fee in its existing observation order."""
        return tuple(
            self.service.evaluate(context, fee) for fee in context.checkout_observation.fees
        )
