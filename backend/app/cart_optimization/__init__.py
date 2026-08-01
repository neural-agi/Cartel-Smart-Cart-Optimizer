"""Immutable Cart Optimization contract models."""

from app.cart_optimization.orchestrator import CartOptimizationOrchestrator

from app.cart_optimization.enums import (
    ConstraintHardness,
    CoverageState,
    OptimizationOutcome,
    PlanRejectionCode,
    PlanFeasibility,
)
from app.cart_optimization.types import (
    BudgetConstraint,
    CandidatePlan,
    CandidatePlanCoverage,
    CartItemRequest,
    CartOptimizationRequest,
    CartOptimizationResult,
    CheckoutGroup,
    DeliveryPreferenceConstraint,
    EffectiveCostEvaluationReference,
    InconveniencePenaltyConstraint,
    ItemAllocation,
    MaximumCheckoutGroupsConstraint,
    MembershipPreferenceConstraint,
    OptimizationConstraintReference,
    RejectedPlan,
    RetailerAllocation,
    RetailerPreferenceConstraint,
    SubstitutionPolicyConstraint,
)

__all__ = [
    "BudgetConstraint",
    "CandidatePlan",
    "CandidatePlanCoverage",
    "CartItemRequest",
    "CartOptimizationRequest",
    "CartOptimizationResult",
    "CartOptimizationOrchestrator",
    "CheckoutGroup",
    "ConstraintHardness",
    "CoverageState",
    "DeliveryPreferenceConstraint",
    "EffectiveCostEvaluationReference",
    "InconveniencePenaltyConstraint",
    "ItemAllocation",
    "MaximumCheckoutGroupsConstraint",
    "MembershipPreferenceConstraint",
    "OptimizationConstraintReference",
    "OptimizationOutcome",
    "PlanRejectionCode",
    "PlanFeasibility",
    "RejectedPlan",
    "RetailerAllocation",
    "RetailerPreferenceConstraint",
    "SubstitutionPolicyConstraint",
]
