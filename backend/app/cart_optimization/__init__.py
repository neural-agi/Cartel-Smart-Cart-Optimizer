"""Immutable Cart Optimization contract models."""

from app.cart_optimization.orchestrator import CartOptimizationOrchestrator
from app.cart_optimization.quantity_semantics import (
    QuantityResolutionStatus,
    VariantQuantityResolutionService,
    VariantQuantitySemantics,
)
from app.cart_optimization.request_builder import CartOptimizationRequestBuilder
from app.cart_optimization.service import CartOptimizationService

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
    CandidateItemAllocation,
    CandidateListingProvenance,
    LogicalCart,
    MaximumCheckoutGroupsConstraint,
    MembershipPreferenceConstraint,
    OptimizationConstraintReference,
    PlatformCartGroup,
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
    "CartOptimizationRequestBuilder",
    "CartOptimizationService",
    "CheckoutGroup",
    "ConstraintHardness",
    "CoverageState",
    "DeliveryPreferenceConstraint",
    "EffectiveCostEvaluationReference",
    "InconveniencePenaltyConstraint",
    "ItemAllocation",
    "CandidateItemAllocation",
    "CandidateListingProvenance",
    "LogicalCart",
    "MaximumCheckoutGroupsConstraint",
    "MembershipPreferenceConstraint",
    "OptimizationConstraintReference",
    "OptimizationOutcome",
    "PlanRejectionCode",
    "PlanFeasibility",
    "PlatformCartGroup",
    "QuantityResolutionStatus",
    "RejectedPlan",
    "RetailerAllocation",
    "RetailerPreferenceConstraint",
    "SubstitutionPolicyConstraint",
    "VariantQuantityResolutionService",
    "VariantQuantitySemantics",
]
