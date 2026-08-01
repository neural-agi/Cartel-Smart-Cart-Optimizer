from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from app.cart_optimization.enums import (
    CoverageState,
    OptimizationOutcome,
    PlanFeasibility,
    PlanRejectionCode,
)
from app.cart_optimization.identity import CandidatePlanIdentityBuilder
from app.cart_optimization.types import (
    CandidatePlan,
    CartOptimizationRequest,
    CartOptimizationResult,
    RejectedPlan,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.product_intelligence.models import EvidenceReference
from app.cost_intelligence.shared.evidence import evidence_identity


class CartOptimizationService:
    """Pure deterministic optimizer over supplied immutable candidate plans."""

    def __init__(self, supported_policy_versions: tuple[str, ...] = ("policy-v1",)) -> None:
        if not supported_policy_versions:
            raise ValueError("at least one supported policy version is required")
        if any(not version.strip() for version in supported_policy_versions):
            raise ValueError("supported policy versions must be non-empty")
        self._supported_policy_versions = tuple(supported_policy_versions)
        self._identity_builder = CandidatePlanIdentityBuilder()

    def optimize(self, request: CartOptimizationRequest) -> CartOptimizationResult:
        evaluations_by_id = self._validate_request(request)
        linked_evaluations = self._resolve_linked_evaluations(request, evaluations_by_id)
        effective_cost_by_plan_id = self._extract_effective_costs(linked_evaluations)

        feasible_plans = tuple(
            plan for plan in request.candidate_plans if plan.feasibility is PlanFeasibility.FEASIBLE
        )
        unresolved_plans = tuple(
            plan
            for plan in request.candidate_plans
            if plan.feasibility is PlanFeasibility.UNRESOLVED
        )
        infeasible_plans = tuple(
            plan
            for plan in request.candidate_plans
            if plan.feasibility is PlanFeasibility.INFEASIBLE
        )

        ranked_plans = self._rank_feasible_plans(feasible_plans, effective_cost_by_plan_id)
        outcome = self._classify_outcome(
            request=request,
            ranked_plans=ranked_plans,
            unresolved_plans=unresolved_plans,
            infeasible_plans=infeasible_plans,
        )
        chosen_plan = self._choose_plan(request, outcome, ranked_plans, unresolved_plans)

        return CartOptimizationResult(
            optimization_id=self._build_optimization_id(request),
            request_id=request.request_id,
            chosen_plan_id=chosen_plan.plan_id if chosen_plan is not None else None,
            chosen_plan=chosen_plan,
            outcome=outcome,
            rationale=self._build_rationale(request, outcome, chosen_plan, unresolved_plans),
            unknowns=self._collect_unknowns(request, linked_evaluations),
            assumptions=(),
            provenance_references=self._collect_provenance(request, linked_evaluations),
            ranked_plan_ids=tuple(plan.plan_id for plan in ranked_plans),
            alternative_plans=tuple(
                plan for plan in ranked_plans if chosen_plan is None or plan.plan_id != chosen_plan.plan_id
            ),
            rejected_plans=self._build_rejected_plans(infeasible_plans),
            rejection_reasons=self._build_rejection_reasons(infeasible_plans),
        )

    def _validate_request(
        self, request: CartOptimizationRequest
    ) -> dict[str, EffectiveCostEvaluationResult]:
        self._validate_request_identity(request)
        self._validate_candidate_plans(request.candidate_plans)
        evaluations_by_id = self._index_effective_cost_evaluations(
            request.effective_cost_evaluations
        )
        self._validate_effective_cost_currencies(request, evaluations_by_id)
        return evaluations_by_id

    def _validate_request_identity(self, request: CartOptimizationRequest) -> None:
        if not request.request_id.strip():
            raise ValueError("request_id is required")
        if request.optimization_policy_version not in self._supported_policy_versions:
            raise ValueError("unsupported optimization policy version")

    def _validate_candidate_plans(self, plans: tuple[CandidatePlan, ...]) -> None:
        plan_ids = [plan.plan_id for plan in plans]
        if any(not plan_id.strip() for plan_id in plan_ids):
            raise ValueError("candidate plan IDs are required")
        if len(plan_ids) != len(set(plan_ids)):
            raise ValueError("duplicate candidate plan IDs are invalid")
        if any(plan.feasibility is PlanFeasibility.INVALID for plan in plans):
            raise ValueError("invalid candidate plan blocks optimization")

    def _index_effective_cost_evaluations(
        self, evaluations: tuple[EffectiveCostEvaluationResult, ...]
    ) -> dict[str, EffectiveCostEvaluationResult]:
        evaluations_by_id = {evaluation.evaluation_id: evaluation for evaluation in evaluations}
        if len(evaluations_by_id) != len(evaluations):
            raise ValueError("duplicate effective-cost evaluation IDs are invalid")
        return evaluations_by_id

    def _validate_effective_cost_currencies(
        self,
        request: CartOptimizationRequest,
        evaluations_by_id: dict[str, EffectiveCostEvaluationResult],
    ) -> None:
        currencies: set[str] = set()
        for plan in request.candidate_plans:
            evaluation = evaluations_by_id.get(
                plan.effective_cost_evaluation_reference.effective_cost_evaluation_id
            )
            if evaluation is not None and evaluation.effective_cost is not None:
                currencies.add(evaluation.effective_cost.currency)
        if len(currencies) > 1:
            raise ValueError("linked effective-cost result currencies must match")

    def _resolve_linked_evaluations(
        self,
        request: CartOptimizationRequest,
        evaluations_by_id: dict[str, EffectiveCostEvaluationResult],
    ) -> dict[str, EffectiveCostEvaluationResult]:
        linked: dict[str, EffectiveCostEvaluationResult] = {}
        for plan in request.candidate_plans:
            reference = plan.effective_cost_evaluation_reference.effective_cost_evaluation_id
            evaluation = evaluations_by_id.get(reference)
            if evaluation is None:
                raise ValueError("candidate plan references missing effective-cost evaluation")
            if (
                plan.feasibility is PlanFeasibility.FEASIBLE
                and (evaluation.effective_cost is None or evaluation.unknown_components)
            ):
                raise ValueError(
                    "feasible candidate plan requires known linked effective cost without unknowns"
                )
            linked[plan.plan_id] = evaluation
        return linked

    def _rank_feasible_plans(
        self,
        plans: tuple[CandidatePlan, ...],
        effective_cost_by_plan_id: dict[str, int],
    ) -> tuple[CandidatePlan, ...]:
        return tuple(sorted(plans, key=lambda plan: self._ranking_key(plan, effective_cost_by_plan_id)))

    def _extract_effective_costs(
        self, linked_evaluations: dict[str, EffectiveCostEvaluationResult]
    ) -> dict[str, int]:
        costs: dict[str, int] = {}
        for plan_id, evaluation in linked_evaluations.items():
            if evaluation.effective_cost is not None:
                costs[plan_id] = evaluation.effective_cost.minor_units
        return costs

    def _ranking_key(
        self,
        plan: CandidatePlan,
        effective_cost_by_plan_id: dict[str, int],
    ) -> tuple[int, int, int, int, str]:
        return (
            effective_cost_by_plan_id[plan.plan_id],
            len(plan.checkout_groups),
            plan.inconvenience_penalty_units,
            -plan.retailer_preference_priority,
            plan.plan_id,
        )

    def _classify_outcome(
        self,
        request: CartOptimizationRequest,
        ranked_plans: tuple[CandidatePlan, ...],
        unresolved_plans: tuple[CandidatePlan, ...],
        infeasible_plans: tuple[CandidatePlan, ...],
    ) -> OptimizationOutcome:
        if request.candidate_plan_coverage.state is not CoverageState.COMPLETE:
            return OptimizationOutcome.UNRESOLVED
        if unresolved_plans:
            return OptimizationOutcome.UNRESOLVED
        if ranked_plans:
            return OptimizationOutcome.SELECTED
        if infeasible_plans or not request.candidate_plans:
            return OptimizationOutcome.INFEASIBLE
        return OptimizationOutcome.UNRESOLVED

    def _choose_plan(
        self,
        request: CartOptimizationRequest,
        outcome: OptimizationOutcome,
        ranked_plans: tuple[CandidatePlan, ...],
        unresolved_plans: tuple[CandidatePlan, ...],
    ) -> CandidatePlan | None:
        if (
            outcome is OptimizationOutcome.SELECTED
            and request.candidate_plan_coverage.state is CoverageState.COMPLETE
            and ranked_plans
            and not unresolved_plans
        ):
            return ranked_plans[0]
        return None

    def _build_optimization_id(self, request: CartOptimizationRequest) -> str:
        payload = {
            "request_id": request.request_id,
            "optimization_policy_version": request.optimization_policy_version,
            "candidate_plans": sorted(
                (self._identity_builder.build(plan) for plan in request.candidate_plans),
                key=lambda item: item["plan_id"],
            ),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "cartopt_" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _build_rationale(
        self,
        request: CartOptimizationRequest,
        outcome: OptimizationOutcome,
        chosen_plan: CandidatePlan | None,
        unresolved_plans: tuple[CandidatePlan, ...],
    ) -> tuple[str, ...]:
        if request.candidate_plan_coverage.state is not CoverageState.COMPLETE:
            return (
                f"coverage_state={request.candidate_plan_coverage.state.value} blocks recommendation",
            ) + tuple(request.candidate_plan_coverage.rationale)
        if unresolved_plans:
            return (
                "unresolved candidate plans block recommendation",
                *tuple(plan.plan_id for plan in unresolved_plans),
            )
        if outcome is OptimizationOutcome.SELECTED and chosen_plan is not None:
            return (f"selected highest-ranked feasible plan {chosen_plan.plan_id}",)
        if outcome is OptimizationOutcome.INFEASIBLE:
            return ("no feasible candidate plan is available",)
        return ("optimization unresolved",)

    def _collect_unknowns(
        self,
        request: CartOptimizationRequest,
        linked_evaluations: dict[str, EffectiveCostEvaluationResult],
    ) -> tuple[str, ...]:
        unknowns: list[str] = []
        for plan in request.candidate_plans:
            unknowns.extend(plan.unknown_components)
            evaluation = linked_evaluations.get(plan.plan_id)
            if evaluation is not None:
                unknowns.extend(evaluation.unknown_components)
        return tuple(unknowns)

    def _collect_provenance(
        self,
        request: CartOptimizationRequest,
        linked_evaluations: dict[str, EffectiveCostEvaluationResult],
    ) -> tuple[EvidenceReference, ...]:
        return self._dedupe_evidence(
            (
                *request.provenance_references,
                *(reference for plan in request.candidate_plans for reference in plan.provenance_references),
                *(
                    reference
                    for evaluation in linked_evaluations.values()
                    for reference in evaluation.evidence_references
                ),
            )
        )

    def _dedupe_evidence(
        self, references: Iterable[EvidenceReference]
    ) -> tuple[EvidenceReference, ...]:
        seen: set[tuple[str, str]] = set()
        unique: list[EvidenceReference] = []
        for reference in references:
            key = evidence_identity(reference)
            if key not in seen:
                seen.add(key)
                unique.append(reference)
        return tuple(unique)

    def _build_rejected_plans(
        self, infeasible_plans: tuple[CandidatePlan, ...]
    ) -> tuple[RejectedPlan, ...]:
        return tuple(
            RejectedPlan(
                plan_id=plan.plan_id,
                code=PlanRejectionCode.UNSUPPORTED_PLAN,
                explanation="candidate plan is deterministically infeasible",
            )
            for plan in sorted(infeasible_plans, key=lambda item: item.plan_id)
        )

    def _build_rejection_reasons(
        self, infeasible_plans: tuple[CandidatePlan, ...]
    ) -> tuple[str, ...]:
        return tuple(
            f"{plan.plan_id}: candidate plan is deterministically infeasible"
            for plan in sorted(infeasible_plans, key=lambda item: item.plan_id)
        )
