"""Explicit-input CandidatePlan construction boundaries.

This module consumes upstream-owned plan inputs. It does not resolve retailer
identity, derive checkout groups, assign feasibility, generate plan IDs, or
create effective-cost evaluations.
"""

from __future__ import annotations

from enum import StrEnum
from itertools import product

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.types import (
    CandidateItemAllocation,
    CandidatePlan,
    CartOptimizationRequest,
    CheckoutGroup,
    EffectiveCostEvaluationReference,
    OptimizationConstraintReference,
    RetailerAllocation,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.product_intelligence.models import EvidenceReference


class CandidateEnumerationStatus(StrEnum):
    complete = "complete"
    no_plan = "no_plan"


class CandidateAllocationSet(BaseModel):
    """Ordered candidates for one requested logical item."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    canonical_variant_id: str
    quantity: int
    candidates: tuple[CandidateItemAllocation, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _validate_candidates(self) -> "CandidateAllocationSet":
        for candidate in self.candidates:
            if (
                candidate.item_id != self.item_id
                or candidate.canonical_variant_id != self.canonical_variant_id
            ):
                raise ValueError("candidate does not match requested logical item")
            if candidate.quantity != self.quantity:
                raise ValueError(
                    "enumeration requires a full-quantity candidate allocation"
                )
        return self


class CandidateEnumerationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: CandidateEnumerationStatus
    combinations: tuple[tuple[CandidateItemAllocation, ...], ...] = Field(
        default_factory=tuple
    )
    reason: str | None = None


class CandidatePlanConstructionInput(BaseModel):
    """All authoritative inputs required to assemble one CandidatePlan."""

    model_config = ConfigDict(frozen=True)

    plan_id: str
    inconvenience_penalty_units: int
    retailer_preference_priority: int
    candidate_item_allocations: tuple[CandidateItemAllocation, ...]
    retailer_allocations: tuple[RetailerAllocation, ...] = Field(default_factory=tuple)
    checkout_groups: tuple[CheckoutGroup, ...]
    effective_cost_evaluation_reference: EffectiveCostEvaluationReference
    effective_cost_evaluation: EffectiveCostEvaluationResult
    feasibility: PlanFeasibility
    feasibility_evidence: tuple[str, ...]
    constraint_references: tuple[OptimizationConstraintReference, ...] = Field(
        default_factory=tuple
    )
    unknown_components: tuple[str, ...] = Field(default_factory=tuple)
    provenance_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _validate_supplied_inputs(self) -> "CandidatePlanConstructionInput":
        if not self.plan_id.strip():
            raise ValueError("supplied plan ID is required")
        if any(
            not value.strip()
            for allocation in self.candidate_item_allocations
            for value in (allocation.item_id, allocation.canonical_variant_id,
                          allocation.retailer_id, allocation.checkout_group_id)
        ):
            raise ValueError("candidate allocation identity fields are required")
        if any(
            not value.strip()
            for group in self.checkout_groups
            for value in (
                group.checkout_group_id,
                group.retailer_id,
                group.effective_cost_evaluation_id,
            )
        ):
            raise ValueError("checkout-group identity fields are required")
        if not self.feasibility_evidence or any(
            not evidence.strip() for evidence in self.feasibility_evidence
        ):
            raise ValueError("explicit feasibility evidence is required")
        if self.feasibility is PlanFeasibility.INVALID:
            raise ValueError("invalid plans cannot be constructed")
        if (
            self.effective_cost_evaluation.evaluation_id
            != self.effective_cost_evaluation_reference.effective_cost_evaluation_id
        ):
            raise ValueError("effective-cost result does not match plan reference")
        return self


class CandidatePlanConstructionService:
    """Enumerate supplied candidates and assemble supplied plan envelopes."""

    def enumerate_allocations(
        self, candidate_sets: tuple[CandidateAllocationSet, ...]
    ) -> CandidateEnumerationResult:
        if not candidate_sets or any(not item.candidates for item in candidate_sets):
            return CandidateEnumerationResult(
                status=CandidateEnumerationStatus.no_plan,
                reason="one or more requested logical items has no allocation-ready candidate",
            )
        ordered_sets = tuple(
            sorted(candidate_sets, key=lambda item: (item.item_id, item.canonical_variant_id))
        )
        return CandidateEnumerationResult(
            status=CandidateEnumerationStatus.complete,
            combinations=tuple(
                product(*(self._ordered_candidates(item) for item in ordered_sets))
            ),
        )

    def construct_plan(self, supplied: CandidatePlanConstructionInput) -> CandidatePlan:
        return CandidatePlan(
            plan_id=supplied.plan_id,
            inconvenience_penalty_units=supplied.inconvenience_penalty_units,
            retailer_preference_priority=supplied.retailer_preference_priority,
            retailer_allocations=supplied.retailer_allocations,
            item_allocations=tuple(
                candidate.to_item_allocation()
                for candidate in supplied.candidate_item_allocations
            ),
            candidate_item_allocations=supplied.candidate_item_allocations,
            checkout_groups=supplied.checkout_groups,
            effective_cost_evaluation_reference=supplied.effective_cost_evaluation_reference,
            constraint_references=supplied.constraint_references,
            feasibility=supplied.feasibility,
            unknown_components=supplied.unknown_components,
            provenance_references=supplied.provenance_references,
        )

    def construct_plans(
        self, supplied: tuple[CandidatePlanConstructionInput, ...]
    ) -> tuple[CandidatePlan, ...]:
        plan_ids = tuple(item.plan_id for item in supplied)
        if len(plan_ids) != len(set(plan_ids)):
            raise ValueError("duplicate supplied plan IDs are invalid")
        return tuple(
            self.construct_plan(item)
            for item in sorted(supplied, key=lambda item: item.plan_id)
        )

    def attach_to_request(
        self,
        request: CartOptimizationRequest,
        supplied: tuple[CandidatePlanConstructionInput, ...],
    ) -> CartOptimizationRequest:
        plans = self.construct_plans(supplied)
        evaluations_by_id = {
            evaluation.evaluation_id: evaluation
            for evaluation in request.effective_cost_evaluations
        }
        for item in supplied:
            existing = evaluations_by_id.get(item.effective_cost_evaluation.evaluation_id)
            if existing is not None and existing != item.effective_cost_evaluation:
                raise ValueError("conflicting effective-cost evaluation IDs are invalid")
            evaluations_by_id[item.effective_cost_evaluation.evaluation_id] = (
                item.effective_cost_evaluation
            )
        return request.model_copy(
            update={
                "candidate_plans": plans,
                "effective_cost_evaluations": tuple(
                    evaluations_by_id[evaluation_id]
                    for evaluation_id in sorted(evaluations_by_id)
                ),
            }
        )

    @staticmethod
    def _ordered_candidates(
        candidate_set: CandidateAllocationSet,
    ) -> tuple[CandidateItemAllocation, ...]:
        return tuple(
            sorted(
                candidate_set.candidates,
                key=lambda candidate: candidate.model_dump_json(
                    exclude_none=False, warnings=False
                ),
            )
        )
