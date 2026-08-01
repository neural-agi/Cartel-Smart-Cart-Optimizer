from __future__ import annotations

from dataclasses import dataclass

from app.cart_optimization.orchestrator import CartOptimizationOrchestrator
from app.cart_optimization.request_builder import CartOptimizationRequestBuilder
from app.cart_optimization.types import CartOptimizationRequest, CartOptimizationResult
from app.cost_intelligence.context.service import DeterministicCostContextBuilder
from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.effective_cost.orchestrator import (
    EffectiveCostEvaluationOrchestrator,
)
from app.cost_intelligence.evaluation.types import (
    EffectiveCostEvaluationResult,
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
)
from app.cost_intelligence.fee.orchestrator import FeeEvaluationOrchestrator
from app.cost_intelligence.membership.orchestrator import MembershipEvaluationOrchestrator
from app.cost_intelligence.observation.types import CheckoutObservation
from app.cost_intelligence.offer.orchestrator import OfferEvaluationOrchestrator


@dataclass(frozen=True)
class CostIntelligencePipelineResult:
    """Immutable outputs from every completed Cost Intelligence stage."""

    context: CostContext
    offer_results: tuple[OfferEvaluationResult, ...]
    fee_results: tuple[FeeEvaluationResult, ...]
    membership_results: tuple[MembershipEvaluationResult, ...]
    effective_cost_result: EffectiveCostEvaluationResult
    optimization_result: CartOptimizationResult


class CostIntelligencePipelineService:
    """Compose Cost Intelligence stages without owning domain policy."""

    def __init__(
        self,
        *,
        context_builder: DeterministicCostContextBuilder | None = None,
        offer_orchestrator: OfferEvaluationOrchestrator | None = None,
        fee_orchestrator: FeeEvaluationOrchestrator | None = None,
        membership_orchestrator: MembershipEvaluationOrchestrator | None = None,
        effective_cost_orchestrator: EffectiveCostEvaluationOrchestrator | None = None,
        cart_optimization_orchestrator: CartOptimizationOrchestrator | None = None,
        cart_optimization_request_builder: CartOptimizationRequestBuilder | None = None,
    ) -> None:
        self._context_builder = context_builder or DeterministicCostContextBuilder()
        self._offer_orchestrator = offer_orchestrator or OfferEvaluationOrchestrator()
        self._fee_orchestrator = fee_orchestrator or FeeEvaluationOrchestrator()
        self._membership_orchestrator = (
            membership_orchestrator or MembershipEvaluationOrchestrator()
        )
        self._effective_cost_orchestrator = (
            effective_cost_orchestrator or EffectiveCostEvaluationOrchestrator()
        )
        self._cart_optimization_orchestrator = (
            cart_optimization_orchestrator or CartOptimizationOrchestrator()
        )
        self._cart_optimization_request_builder = (
            cart_optimization_request_builder or CartOptimizationRequestBuilder()
        )

    def run(
        self,
        observation: CheckoutObservation,
        optimization_request: CartOptimizationRequest,
    ) -> CostIntelligencePipelineResult:
        context = self._context_builder.build(observation)
        offer_results = self._offer_orchestrator.evaluate(context)
        fee_results = self._fee_orchestrator.evaluate(context)
        membership_results = self._membership_orchestrator.evaluate(context)
        effective_cost_result = self._effective_cost_orchestrator.evaluate(
            context,
            offer_results,
            fee_results,
            membership_results,
        )
        request_with_effective_cost = self._cart_optimization_request_builder.with_effective_cost(
            optimization_request,
            effective_cost_result,
        )
        optimization_result = self._cart_optimization_orchestrator.optimize(
            request_with_effective_cost
        )
        return CostIntelligencePipelineResult(
            context=context,
            offer_results=offer_results,
            fee_results=fee_results,
            membership_results=membership_results,
            effective_cost_result=effective_cost_result,
            optimization_result=optimization_result,
        )
