from __future__ import annotations

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.effective_cost.aggregation import EffectiveCostAggregation
from app.cost_intelligence.effective_cost.identity import EffectiveCostIdentityGenerator
from app.cost_intelligence.effective_cost.provenance import EvidenceMerger
from app.cost_intelligence.effective_cost.subtotal import SubtotalExtractor
from app.cost_intelligence.effective_cost.unknowns import UnknownPropagationPolicy
from app.cost_intelligence.evaluation.types import (
    EffectiveCostEvaluationResult,
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
)


class EffectiveCostEvaluationService:
    """Deterministic aggregator for structured Cost Intelligence evaluator outputs."""

    def __init__(self) -> None:
        self._subtotal_extractor = SubtotalExtractor()
        self._unknown_policy = UnknownPropagationPolicy()
        self._aggregation = EffectiveCostAggregation()
        self._evidence_merger = EvidenceMerger()
        self._identity_generator = EffectiveCostIdentityGenerator()

    def evaluate(
        self,
        context: CostContext,
        offer_results: tuple[OfferEvaluationResult, ...],
        fee_results: tuple[FeeEvaluationResult, ...],
        membership_results: tuple[MembershipEvaluationResult, ...],
    ) -> EffectiveCostEvaluationResult:
        subtotal = self._subtotal_extractor.extract(context)
        immediate_discounts = self._aggregation.collect_immediate_discounts(
            offer_results,
            membership_results,
        )
        fee_amounts = self._aggregation.collect_fee_amounts(fee_results)
        deferred_value = self._aggregation.collect_deferred_value(offer_results)
        unknown_components, has_blocking_unknowns = self._unknown_policy.evaluate(
            subtotal,
            offer_results,
            fee_results,
            membership_results,
        )
        effective_cost = self._aggregation.calculate_effective_cost(
            subtotal=subtotal,
            immediate_discounts=immediate_discounts,
            fee_amounts=fee_amounts,
            has_blocking_unknowns=has_blocking_unknowns,
        )

        return EffectiveCostEvaluationResult(
            evaluation_id=self._identity_generator.evaluation_id(
                context.context_id,
                offer_results,
                fee_results,
                membership_results,
            ),
            context_id=context.context_id,
            subtotal=subtotal,
            immediate_discounts=immediate_discounts,
            fees=fee_amounts,
            effective_cost=effective_cost,
            deferred_value=deferred_value,
            unknown_components=unknown_components,
            evidence_references=self._evidence_merger.merge(
                context.evidence_references,
                offer_results,
                fee_results,
                membership_results,
            ),
        )

    def _evaluation_id(
        self,
        context_id: str,
        offer_results: tuple[OfferEvaluationResult, ...],
        fee_results: tuple[FeeEvaluationResult, ...],
        membership_results: tuple[MembershipEvaluationResult, ...],
    ) -> str:
        return self._identity_generator.evaluation_id(
            context_id,
            offer_results,
            fee_results,
            membership_results,
        )
