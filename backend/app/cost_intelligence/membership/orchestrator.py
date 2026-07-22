from __future__ import annotations

"""Deterministic orchestration for membership-by-membership evaluation.

This orchestrator remains separate from the offer and fee orchestrators on purpose.
The pipeline favors explicit duplication over premature abstraction until
multiple concrete orchestrators prove stable shared behavior.
"""

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.evaluation.types import MembershipEvaluationResult
from app.cost_intelligence.membership.service import MembershipEvaluationService


class MembershipEvaluationOrchestrator:
    """Iterate over observed memberships without adding evaluation policy."""

    def __init__(self) -> None:
        self.service = MembershipEvaluationService()

    def evaluate(self, context: CostContext) -> tuple[MembershipEvaluationResult, ...]:
        """Evaluate every membership in its existing observation order."""
        return tuple(
            self.service.evaluate(context, membership)
            for membership in context.checkout_observation.memberships
        )
