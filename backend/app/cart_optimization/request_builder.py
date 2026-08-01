from __future__ import annotations

from app.cart_optimization.types import CartOptimizationRequest
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult


class CartOptimizationRequestBuilder:
    """Assemble immutable Cart Optimization inputs from upstream results."""

    def with_effective_cost(
        self,
        request: CartOptimizationRequest,
        evaluation: EffectiveCostEvaluationResult,
    ) -> CartOptimizationRequest:
        return request.model_copy(
            update={
                "effective_cost_evaluations": (
                    *request.effective_cost_evaluations,
                    evaluation,
                )
            }
        )
