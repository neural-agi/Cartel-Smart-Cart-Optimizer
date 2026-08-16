import pytest
from pydantic import ValidationError

from app.cart_optimization.enums import (
    ConstraintHardness,
    CoverageState,
    OptimizationOutcome,
    PlanFeasibility,
)
from app.cart_optimization.service import CartOptimizationService
from app.cart_optimization.identity import CandidatePlanIdentityBuilder
from app.cart_optimization.types import (
    BudgetConstraint,
    CandidateItemAllocation,
    CandidatePlan,
    CandidatePlanCoverage,
    CartItemRequest,
    CartOptimizationRequest,
    DeliveryPreferenceConstraint,
    CheckoutGroup,
    EffectiveCostEvaluationReference,
    InconveniencePenaltyConstraint,
    ItemAllocation,
    MaximumCheckoutGroupsConstraint,
    MembershipPreferenceConstraint,
    OptimizationConstraintReference,
    RetailerAllocation,
    RetailerPreferenceConstraint,
    SubstitutionPolicyConstraint,
)
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.enums import TaxStatus
from app.data_ingestion.observation_registry.comparison import ComparableRetailObservation
from app.product_intelligence.models import EvidenceReference


def _evaluation(
    evaluation_id: str,
    amount: int | None,
    *,
    currency: str = "INR",
    unknown_components: tuple[str, ...] = (),
) -> EffectiveCostEvaluationResult:
    return EffectiveCostEvaluationResult(
        evaluation_id=evaluation_id,
        context_id=f"context-{evaluation_id}",
        effective_cost=Money(currency=currency, minor_units=amount) if amount is not None else None,
        unknown_components=unknown_components,
        evidence_references=(
            EvidenceReference(source_type="effective_cost", source_id=evaluation_id),
        ),
    )


def _plan(
    plan_id: str,
    evaluation_id: str,
    *,
    feasibility: PlanFeasibility = PlanFeasibility.FEASIBLE,
    checkout_groups: int = 1,
    inconvenience_penalty_units: int = 0,
    retailer_preference_priority: int = 0,
    unknown_components: tuple[str, ...] = (),
) -> CandidatePlan:
    return CandidatePlan(
        plan_id=plan_id,
        inconvenience_penalty_units=inconvenience_penalty_units,
        retailer_preference_priority=retailer_preference_priority,
        checkout_groups=tuple(
            CheckoutGroup(
                checkout_group_id=f"{plan_id}-checkout-{index}",
                retailer_id=f"retailer-{index}",
                effective_cost_evaluation_id=evaluation_id,
            )
            for index in range(checkout_groups)
        ),
        item_allocations=(
            ItemAllocation(
                item_id="item-1",
                canonical_variant_id="variant-1",
                quantity=1,
                retailer_id="retailer-0",
                checkout_group_id=f"{plan_id}-checkout-0",
            ),
        ),
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id=evaluation_id
        ),
        feasibility=feasibility,
        unknown_components=unknown_components,
        provenance_references=(
            EvidenceReference(source_type="candidate_plan", source_id=plan_id),
        ),
    )


def _coverage(state: CoverageState = CoverageState.COMPLETE) -> CandidatePlanCoverage:
    return CandidatePlanCoverage(
        state=state,
        scope_reference="scope-1" if state is CoverageState.COMPLETE else None,
        candidate_set_reference="candidate-set-1" if state is CoverageState.COMPLETE else None,
        coverage_basis="unit-test" if state is CoverageState.COMPLETE else None,
        validation_reference="coverage-validation-1" if state is CoverageState.COMPLETE else None,
        rationale=() if state is CoverageState.COMPLETE else (f"coverage is {state.value}",),
    )


def _request(
    *,
    candidate_plans: tuple[CandidatePlan, ...],
    evaluations: tuple[EffectiveCostEvaluationResult, ...],
    coverage_state: CoverageState = CoverageState.COMPLETE,
    policy_version: str = "policy-v1",
) -> CartOptimizationRequest:
    return CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version=policy_version,
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
        ),
        candidate_plans=candidate_plans,
        candidate_plan_coverage=_coverage(coverage_state),
        effective_cost_evaluations=evaluations,
        provenance_references=(
            EvidenceReference(source_type="request", source_id="request-1"),
        ),
    )


def test_complete_coverage_selects_highest_ranked_feasible_plan() -> None:
    expensive = _plan("plan-expensive", "eval-expensive")
    cheap = _plan("plan-cheap", "eval-cheap")
    request = _request(
        candidate_plans=(expensive, cheap),
        evaluations=(_evaluation("eval-expensive", 1200), _evaluation("eval-cheap", 900)),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-cheap"
    assert result.ranked_plan_ids == ("plan-cheap", "plan-expensive")


def test_partial_unknown_and_invalid_coverage_block_recommendation() -> None:
    plan = _plan("plan-1", "eval-1")
    evaluation = _evaluation("eval-1", 1000)

    for state in (CoverageState.PARTIAL, CoverageState.UNKNOWN, CoverageState.INVALID):
        request = _request(
            candidate_plans=(plan,),
            evaluations=(evaluation,),
            coverage_state=state,
        )
        result = CartOptimizationService().optimize(request)

        assert result.outcome is OptimizationOutcome.UNRESOLVED
        assert result.chosen_plan is None
        assert result.ranked_plan_ids == ("plan-1",)


def test_all_plans_infeasible_returns_infeasible() -> None:
    plan = _plan("plan-1", "eval-1", feasibility=PlanFeasibility.INFEASIBLE)
    request = _request(candidate_plans=(plan,), evaluations=(_evaluation("eval-1", 1000),))

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.INFEASIBLE
    assert result.chosen_plan_id is None
    assert result.rejected_plans[0].plan_id == "plan-1"


@pytest.mark.parametrize(
    ("declared_feasibility", "requested_quantity", "expected_outcome", "ranked", "rejected"),
    (
        (
            PlanFeasibility.FEASIBLE,
            1,
            OptimizationOutcome.SELECTED,
            ("plan-1",),
            (),
        ),
        (
            PlanFeasibility.FEASIBLE,
            2,
            OptimizationOutcome.INFEASIBLE,
            (),
            ("plan-1",),
        ),
        (
            PlanFeasibility.UNRESOLVED,
            1,
            OptimizationOutcome.UNRESOLVED,
            (),
            (),
        ),
        (
            PlanFeasibility.UNRESOLVED,
            2,
            OptimizationOutcome.INFEASIBLE,
            (),
            ("plan-1",),
        ),
        (
            PlanFeasibility.INFEASIBLE,
            1,
            OptimizationOutcome.INFEASIBLE,
            (),
            ("plan-1",),
        ),
        (
            PlanFeasibility.INFEASIBLE,
            2,
            OptimizationOutcome.INFEASIBLE,
            (),
            ("plan-1",),
        ),
    ),
)
def test_effective_feasibility_precedence(
    declared_feasibility: PlanFeasibility,
    requested_quantity: int,
    expected_outcome: OptimizationOutcome,
    ranked: tuple[str, ...],
    rejected: tuple[str, ...],
) -> None:
    request = _request(
        candidate_plans=(
            _plan("plan-1", "eval-1", feasibility=declared_feasibility),
        ),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(
                    item_id="item-1",
                    canonical_variant_id="variant-1",
                    quantity=requested_quantity,
                ),
            )
        }
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is expected_outcome
    assert result.ranked_plan_ids == ranked
    assert tuple(plan.plan_id for plan in result.rejected_plans) == rejected


def test_known_fulfillment_mismatch_does_not_require_feasible_ece() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", None, unknown_components=("effective_cost",)),),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
            )
        }
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.INFEASIBLE
    assert result.rejected_plans[0].plan_id == "plan-1"


def test_optimizer_accepts_candidate_allocation_and_preserves_listing_provenance() -> None:
    candidate = CandidateItemAllocation.from_comparable_observation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=1,
        retailer_id="BLINKIT",
        checkout_group_id="plan-1-checkout-0",
        observation=ComparableRetailObservation(
            observation_id="observation-1",
            platform="BLINKIT",
            platform_listing_id="listing-1",
            canonical_product_id="product-1",
            canonical_variant_id="variant-1",
            observed_selling_price=Money(currency="INR", minor_units=10000),
            tax_status=TaxStatus.INCLUDED,
        ),
    )
    plan = _plan("plan-1", "eval-1").model_copy(update={"item_allocations": (candidate,)})
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.chosen_plan is not None
    provenance = result.chosen_plan.item_allocations[0].listing_provenance
    assert provenance is not None
    assert provenance.platform == "BLINKIT"
    assert provenance.platform_listing_id == "listing-1"
    assert provenance.observation_id == "observation-1"
    assert provenance.observed_selling_price == Money(currency="INR", minor_units=10000)
    assert all(reference.source_id != "observation-1" for reference in result.provenance_references)


def test_rejected_plan_listing_provenance_is_not_added_to_result_provenance() -> None:
    candidate = CandidateItemAllocation.from_comparable_observation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=2,
        retailer_id="BLINKIT",
        checkout_group_id="plan-1-checkout-0",
        observation=ComparableRetailObservation(
            observation_id="rejected-observation",
            platform="BLINKIT",
            platform_listing_id="listing-1",
            canonical_product_id="product-1",
            canonical_variant_id="variant-1",
            observed_selling_price=Money(currency="INR", minor_units=10000),
            tax_status=TaxStatus.INCLUDED,
        ),
    )
    plan = _plan("plan-1", "eval-1").model_copy(update={"item_allocations": (candidate,)})
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.chosen_plan is None
    assert all(
        reference.source_id != "rejected-observation"
        for reference in result.provenance_references
    )


def test_unresolved_group_ece_is_accepted_without_affecting_optimization() -> None:
    plan = _plan("plan-1", "eval-1").model_copy(
        update={
            "checkout_groups": (
                _plan("plan-1", "eval-1").checkout_groups[0].model_copy(
                    update={"effective_cost_evaluation_id": "missing-group-ece"}
                ),
            )
        }
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.chosen_plan_id == "plan-1"


def test_multiple_checkout_groups_may_share_group_ece_id() -> None:
    plan = _plan("plan-1", "eval-1", checkout_groups=2).model_copy(
        update={
            "checkout_groups": tuple(
                group.model_copy(update={"effective_cost_evaluation_id": "shared-group-ece"})
                for group in _plan("plan-1", "eval-1", checkout_groups=2).checkout_groups
            ),
            "item_allocations": (
                ItemAllocation(
                    item_id="item-1",
                    canonical_variant_id="variant-1",
                    quantity=1,
                    retailer_id="retailer-0",
                    checkout_group_id="plan-1-checkout-0",
                ),
                ItemAllocation(
                    item_id="item-1",
                    canonical_variant_id="variant-1",
                    quantity=1,
                    retailer_id="retailer-1",
                    checkout_group_id="plan-1-checkout-1",
                ),
            ),
        }
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
            )
        }
    )

    result = CartOptimizationService().optimize(request)

    assert result.chosen_plan_id == "plan-1"


def test_group_ece_may_differ_from_plan_level_ece() -> None:
    plan = _plan("plan-1", "eval-1").model_copy(
        update={
            "checkout_groups": (
                _plan("plan-1", "eval-1").checkout_groups[0].model_copy(
                    update={"effective_cost_evaluation_id": "different-group-ece"}
                ),
            )
        }
    )
    result = CartOptimizationService().optimize(
        _request(candidate_plans=(plan,), evaluations=(_evaluation("eval-1", 1000),))
    )

    assert result.chosen_plan_id == "plan-1"


def test_group_ece_does_not_affect_plan_level_ranking_or_result_provenance() -> None:
    cheap = _plan("cheap", "eval-cheap").model_copy(
        update={
            "checkout_groups": (
                _plan("cheap", "eval-cheap").checkout_groups[0].model_copy(
                    update={"effective_cost_evaluation_id": "unresolved-group-ece"}
                ),
            )
        }
    )
    request = _request(
        candidate_plans=(cheap, _plan("expensive", "eval-expensive")),
        evaluations=(_evaluation("eval-cheap", 900), _evaluation("eval-expensive", 1000)),
    )

    result = CartOptimizationService().optimize(request)

    assert result.ranked_plan_ids == ("cheap", "expensive")
    assert result.chosen_plan_id == "cheap"
    assert all(
        reference.source_id != "unresolved-group-ece"
        for reference in result.provenance_references
    )


def test_unresolved_plan_blocks_recommendation_and_preserves_unknowns() -> None:
    feasible = _plan("plan-feasible", "eval-feasible")
    unresolved = _plan(
        "plan-unresolved",
        "eval-unresolved",
        feasibility=PlanFeasibility.UNRESOLVED,
        unknown_components=("availability",),
    )
    request = _request(
        candidate_plans=(feasible, unresolved),
        evaluations=(
            _evaluation("eval-feasible", 1000),
            _evaluation("eval-unresolved", None, unknown_components=("effective_cost",)),
        ),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.UNRESOLVED
    assert result.chosen_plan_id is None
    assert result.ranked_plan_ids == ("plan-feasible",)
    assert result.unknowns == ("availability", "effective_cost")
    assert result.rejected_plans == ()
    assert result.rejection_reasons == ()
    assert result.rationale == (
        "unresolved candidate plans block recommendation",
        "plan-unresolved",
    )


def test_constraint_references_remain_opaque_and_unresolved() -> None:
    plan = _plan("plan-1", "eval-1").model_copy(
        update={
            "constraint_references": (
                OptimizationConstraintReference(optimization_constraint_id="missing-constraint"),
            )
        }
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "constraints": (
                BudgetConstraint(
                    amount=Money(currency="INR", minor_units=1),
                    hardness=ConstraintHardness.HARD,
                ),
            )
        }
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-1"


def test_supplied_unresolved_feasibility_remains_authoritative() -> None:
    request = _request(
        candidate_plans=(
            _plan("plan-1", "eval-1", feasibility=PlanFeasibility.UNRESOLVED),
        ),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.UNRESOLVED
    assert result.chosen_plan is None


def test_cart_optimization_does_not_evaluate_hard_constraint_values() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "constraints": (
                BudgetConstraint(
                    amount=Money(currency="INR", minor_units=1),
                    hardness=ConstraintHardness.HARD,
                ),
            )
        }
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-1"


def test_invalid_plan_blocks_optimization() -> None:
    plan = _plan("plan-1", "eval-1", feasibility=PlanFeasibility.INVALID)
    request = _request(candidate_plans=(plan,), evaluations=(_evaluation("eval-1", 1000),))

    with pytest.raises(ValueError, match="invalid candidate plan"):
        CartOptimizationService().optimize(request)


def test_duplicate_plan_ids_fail_closed() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"), _plan("plan-1", "eval-2")),
        evaluations=(_evaluation("eval-1", 1000), _evaluation("eval-2", 900)),
    )

    with pytest.raises(ValueError, match="duplicate candidate plan IDs"):
        CartOptimizationService().optimize(request)


def test_unsupported_policy_version_fails_closed() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
        policy_version="unsupported-policy",
    )

    with pytest.raises(ValueError, match="unsupported optimization policy version"):
        CartOptimizationService().optimize(request)


def test_missing_or_unknown_linked_effective_cost_for_feasible_plan_fails_closed() -> None:
    missing_request = _request(
        candidate_plans=(_plan("plan-1", "missing-eval"),),
        evaluations=(_evaluation("eval-1", 1000),),
    )
    unknown_request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", None, unknown_components=("effective_cost",)),),
    )

    with pytest.raises(ValueError, match="missing effective-cost evaluation"):
        CartOptimizationService().optimize(missing_request)
    with pytest.raises(ValueError, match="known linked effective cost"):
        CartOptimizationService().optimize(unknown_request)


def test_currency_mismatch_fails_closed() -> None:
    request = _request(
        candidate_plans=(_plan("plan-inr", "eval-inr"), _plan("plan-usd", "eval-usd")),
        evaluations=(_evaluation("eval-inr", 1000), _evaluation("eval-usd", 900, currency="USD")),
    )

    with pytest.raises(ValueError, match="currencies must match"):
        CartOptimizationService().optimize(request)


def test_ranking_tie_breakers_are_deterministic() -> None:
    by_checkout_count = _plan("plan-b", "eval-b", checkout_groups=2)
    by_penalty = _plan("plan-c", "eval-c", inconvenience_penalty_units=5)
    by_priority = _plan("plan-d", "eval-d", retailer_preference_priority=1)
    by_plan_id = _plan("plan-a", "eval-a")
    plans = tuple(
        plan.model_copy(
            update={
                "item_allocations": (
                    *plan.item_allocations,
                    ItemAllocation(
                        item_id="item-2",
                        canonical_variant_id="variant-2",
                        quantity=1,
                        retailer_id="retailer-1" if len(plan.checkout_groups) > 1 else "retailer-0",
                        checkout_group_id=(
                            f"{plan.plan_id}-checkout-1"
                            if len(plan.checkout_groups) > 1
                            else f"{plan.plan_id}-checkout-0"
                        ),
                    ),
                )
            }
        )
        for plan in (by_checkout_count, by_penalty, by_priority, by_plan_id)
    )
    request = _request(
        candidate_plans=plans,
        evaluations=(
            _evaluation("eval-b", 1000),
            _evaluation("eval-c", 1000),
            _evaluation("eval-d", 1000),
            _evaluation("eval-a", 1000),
        ),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
                CartItemRequest(item_id="item-2", canonical_variant_id="variant-2", quantity=1),
            )
        }
    )

    result = CartOptimizationService().optimize(request)

    assert result.ranked_plan_ids == ("plan-d", "plan-a", "plan-c", "plan-b")
    assert result.chosen_plan_id == "plan-d"


def test_deterministic_replay_and_optimization_id_stability() -> None:
    request = _request(
        candidate_plans=(_plan("plan-2", "eval-2"), _plan("plan-1", "eval-1")),
        evaluations=(_evaluation("eval-1", 900), _evaluation("eval-2", 1100)),
    )
    service = CartOptimizationService()

    first = service.optimize(request)
    second = service.optimize(request)

    assert first == second
    assert first.optimization_id == second.optimization_id


def test_provenance_is_preserved_and_deduplicated_by_identity() -> None:
    shared = EvidenceReference(source_type="shared", source_id="same")
    plan = _plan("plan-1", "eval-1").model_copy(
        update={"provenance_references": (shared, shared)}
    )
    request = CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
        ),
        candidate_plans=(plan,),
        candidate_plan_coverage=_coverage(),
        effective_cost_evaluations=(
            EffectiveCostEvaluationResult(
                evaluation_id="eval-1",
                context_id="context-1",
                effective_cost=Money(currency="INR", minor_units=1000),
                evidence_references=(shared,),
            ),
        ),
        provenance_references=(shared,),
    )

    result = CartOptimizationService().optimize(request)

    assert result.provenance_references == (shared,)


def test_result_and_request_are_immutable() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    )
    result = CartOptimizationService().optimize(request)

    with pytest.raises((TypeError, ValidationError)):
        request.request_id = "changed"  # type: ignore[misc]
    with pytest.raises((TypeError, ValidationError)):
        result.request_id = "changed"  # type: ignore[misc]


def test_optimization_identity_excludes_request_id() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    )
    changed = request.model_copy(update={"request_id": "different-request"})

    assert CartOptimizationService().optimize(request).optimization_id == (
        CartOptimizationService().optimize(changed).optimization_id
    )


def test_optimization_identity_includes_cart_item_identity_and_quantity() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    )
    changed_quantity = request.model_copy(
        update={"cart_items": (CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),)}
    )
    changed_variant = request.model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-2", quantity=1),
            ),
            "candidate_plans": (
                _plan("plan-1", "eval-1").model_copy(
                    update={
                        "item_allocations": (
                            _plan("plan-1", "eval-1").item_allocations[0].model_copy(
                                update={"canonical_variant_id": "variant-2"}
                            ),
                        )
                    }
                ),
            ),
        }
    )
    service = CartOptimizationService()

    original_id = service.optimize(request).optimization_id
    assert service.optimize(changed_quantity).optimization_id != original_id
    assert service.optimize(changed_variant).optimization_id != original_id


def test_optimization_identity_includes_plan_evaluation_policy_and_constraint_values() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    )
    service = CartOptimizationService(supported_policy_versions=("policy-v1", "policy-v2"))
    original_id = service.optimize(request).optimization_id

    changed_plan = request.model_copy(
        update={
            "candidate_plans": (
                _plan("plan-1", "eval-1", inconvenience_penalty_units=1),
            )
        }
    )
    changed_evaluation = request.model_copy(
        update={
            "candidate_plans": (_plan("plan-1", "eval-2"),),
            "effective_cost_evaluations": (_evaluation("eval-2", 1000),),
        }
    )
    changed_policy = request.model_copy(update={"optimization_policy_version": "policy-v2"})
    changed_constraint = request.model_copy(
        update={
            "constraints": (
                BudgetConstraint(
                    amount=Money(currency="INR", minor_units=1001),
                    hardness=ConstraintHardness.HARD,
                ),
            )
        }
    )

    assert service.optimize(changed_plan).optimization_id != original_id
    assert service.optimize(changed_evaluation).optimization_id != original_id
    assert service.optimize(changed_policy).optimization_id != original_id
    assert service.optimize(changed_constraint).optimization_id != original_id


def test_request_identity_is_stable_for_reordered_canonical_collections() -> None:
    first = _request(
        candidate_plans=(_plan("plan-2", "eval-2"), _plan("plan-1", "eval-1")),
        evaluations=(_evaluation("eval-1", 1000), _evaluation("eval-2", 900)),
    )
    second = first.model_copy(
        update={
            "candidate_plans": tuple(reversed(first.candidate_plans)),
            "effective_cost_evaluations": tuple(reversed(first.effective_cost_evaluations)),
        }
    )
    service = CartOptimizationService()

    assert service.optimize(first).optimization_id == service.optimize(second).optimization_id


def test_candidate_plan_identity_payload_is_directly_stable() -> None:
    builder = CandidatePlanIdentityBuilder()
    first = builder.build(_plan("plan-1", "eval-1"))
    second = builder.build(_plan("plan-1", "eval-1"))

    assert first == second
    assert first["plan_id"] == "plan-1"
    assert first["effective_cost_evaluation_id"] == "eval-1"


def test_reordering_cart_items_does_not_change_optimization_identity() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
                CartItemRequest(item_id="item-2", canonical_variant_id="variant-2", quantity=2),
            )
        }
    )
    reordered = request.model_copy(update={"cart_items": tuple(reversed(request.cart_items))})
    service = CartOptimizationService()

    assert service.optimize(request).optimization_id == service.optimize(reordered).optimization_id


def test_reordering_constraints_does_not_change_optimization_identity() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "constraints": (
                BudgetConstraint(
                    amount=Money(currency="INR", minor_units=1000),
                    hardness=ConstraintHardness.HARD,
                ),
                RetailerPreferenceConstraint(
                    retailer_ids=("retailer-1",),
                    hardness=ConstraintHardness.SOFT,
                ),
            )
        }
    )
    reordered = request.model_copy(update={"constraints": tuple(reversed(request.constraints))})
    service = CartOptimizationService()

    assert service.optimize(request).optimization_id == service.optimize(reordered).optimization_id


def test_unused_effective_cost_evaluation_does_not_change_optimization_identity() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    )
    with_unused = request.model_copy(
        update={
            "effective_cost_evaluations": (
                *_request(
                    candidate_plans=(_plan("plan-1", "eval-1"),),
                    evaluations=(_evaluation("eval-1", 1000),),
                ).effective_cost_evaluations,
                _evaluation("eval-2", 900),
            )
        }
    )
    service = CartOptimizationService()

    assert service.optimize(request).optimization_id == service.optimize(with_unused).optimization_id


def test_constraint_hardness_is_part_of_request_identity() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "constraints": (
                BudgetConstraint(
                    amount=Money(currency="INR", minor_units=1000),
                    hardness=ConstraintHardness.HARD,
                ),
            )
        }
    )
    changed = request.model_copy(
        update={
            "constraints": (
                BudgetConstraint(
                    amount=Money(currency="INR", minor_units=1000),
                    hardness=ConstraintHardness.SOFT,
                ),
            )
        }
    )
    service = CartOptimizationService()

    assert service.optimize(request).optimization_id != service.optimize(changed).optimization_id


@pytest.mark.parametrize(
    ("original", "changed"),
    (
        (
            BudgetConstraint(amount=Money(currency="INR", minor_units=1000), hardness=ConstraintHardness.HARD),
            BudgetConstraint(amount=Money(currency="INR", minor_units=1100), hardness=ConstraintHardness.HARD),
        ),
        (
            RetailerPreferenceConstraint(retailer_ids=("retailer-1",), hardness=ConstraintHardness.SOFT),
            RetailerPreferenceConstraint(retailer_ids=("retailer-2",), hardness=ConstraintHardness.SOFT),
        ),
        (
            MaximumCheckoutGroupsConstraint(maximum_checkout_groups=1, hardness=ConstraintHardness.HARD),
            MaximumCheckoutGroupsConstraint(maximum_checkout_groups=2, hardness=ConstraintHardness.HARD),
        ),
        (
            InconveniencePenaltyConstraint(penalty_units=1, hardness=ConstraintHardness.SOFT),
            InconveniencePenaltyConstraint(penalty_units=2, hardness=ConstraintHardness.SOFT),
        ),
        (
            DeliveryPreferenceConstraint(preference="fast", hardness=ConstraintHardness.SOFT),
            DeliveryPreferenceConstraint(preference="standard", hardness=ConstraintHardness.SOFT),
        ),
        (
            SubstitutionPolicyConstraint(allow_substitutions=False, hardness=ConstraintHardness.HARD),
            SubstitutionPolicyConstraint(allow_substitutions=True, hardness=ConstraintHardness.HARD),
        ),
        (
            MembershipPreferenceConstraint(preference="none", hardness=ConstraintHardness.SOFT),
            MembershipPreferenceConstraint(preference="preferred", hardness=ConstraintHardness.SOFT),
        ),
    ),
)
def test_each_constraint_variant_value_changes_request_identity(original, changed) -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(update={"constraints": (original,)})
    changed_request = request.model_copy(update={"constraints": (changed,)})
    service = CartOptimizationService()

    assert service.optimize(request).optimization_id != service.optimize(changed_request).optimization_id


def test_each_candidate_plan_identity_component_changes_plan_identity() -> None:
    builder = CandidatePlanIdentityBuilder()
    base = CandidatePlan(
        plan_id="plan-1",
        inconvenience_penalty_units=1,
        retailer_preference_priority=1,
        retailer_allocations=(RetailerAllocation(retailer_id="retailer-1", checkout_group_id="group-1"),),
        item_allocations=(
            ItemAllocation(
                item_id="item-1",
                canonical_variant_id="variant-1",
                quantity=1,
                retailer_id="retailer-1",
                checkout_group_id="group-1",
            ),
        ),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="group-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="eval-1",
            ),
        ),
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        constraint_references=(OptimizationConstraintReference(optimization_constraint_id="constraint-1"),),
        feasibility=PlanFeasibility.FEASIBLE,
    )
    changes = (
        {"plan_id": "plan-2"},
        {"inconvenience_penalty_units": 2},
        {"retailer_preference_priority": 2},
        {"retailer_allocations": (RetailerAllocation(retailer_id="retailer-2", checkout_group_id="group-1"),)},
        {"item_allocations": (base.item_allocations[0].model_copy(update={"quantity": 2}),)},
        {"checkout_groups": (base.checkout_groups[0].model_copy(update={"checkout_group_id": "group-2"}),)},
        {"effective_cost_evaluation_reference": EffectiveCostEvaluationReference(effective_cost_evaluation_id="eval-2")},
        {"constraint_references": (OptimizationConstraintReference(optimization_constraint_id="constraint-2"),)},
    )
    original = builder.build(base)

    for change in changes:
        assert builder.build(base.model_copy(update=change)) != original


def test_checkout_group_evaluation_identity_changes_plan_identity() -> None:
    builder = CandidatePlanIdentityBuilder()
    base = _plan("plan-1", "eval-1", checkout_groups=1)
    changed = base.model_copy(
        update={
            "checkout_groups": (
                base.checkout_groups[0].model_copy(
                    update={"effective_cost_evaluation_id": "group-eval-2"}
                ),
            )
        }
    )

    assert builder.build(changed) != builder.build(base)


def test_candidate_plan_identity_is_stable_for_reordered_nested_collections() -> None:
    builder = CandidatePlanIdentityBuilder()
    base = CandidatePlan(
        plan_id="plan-1",
        inconvenience_penalty_units=1,
        retailer_preference_priority=1,
        retailer_allocations=(
            RetailerAllocation(retailer_id="retailer-1", checkout_group_id="group-1"),
            RetailerAllocation(retailer_id="retailer-2", checkout_group_id="group-2"),
        ),
        item_allocations=(
            ItemAllocation(
                item_id="item-1",
                canonical_variant_id="variant-1",
                quantity=1,
                retailer_id="retailer-1",
                checkout_group_id="group-1",
            ),
            ItemAllocation(
                item_id="item-2",
                canonical_variant_id="variant-2",
                quantity=1,
                retailer_id="retailer-2",
                checkout_group_id="group-2",
            ),
        ),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="group-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="group-eval-1",
            ),
            CheckoutGroup(
                checkout_group_id="group-2",
                retailer_id="retailer-2",
                effective_cost_evaluation_id="group-eval-2",
            ),
        ),
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="eval-1"
        ),
        constraint_references=(
            OptimizationConstraintReference(optimization_constraint_id="constraint-1"),
            OptimizationConstraintReference(optimization_constraint_id="constraint-2"),
        ),
        feasibility=PlanFeasibility.FEASIBLE,
    )
    reordered = base.model_copy(
        update={
            "retailer_allocations": tuple(reversed(base.retailer_allocations)),
            "item_allocations": tuple(reversed(base.item_allocations)),
            "checkout_groups": tuple(reversed(base.checkout_groups)),
            "constraint_references": tuple(reversed(base.constraint_references)),
        }
    )

    assert builder.build(reordered) == builder.build(base)


def test_single_allocation_exactly_fulfills_request_item() -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "plan-1"


def test_split_allocations_exactly_fulfill_request_item() -> None:
    plan = _plan("plan-1", "eval-1", checkout_groups=2).model_copy(
        update={
            "item_allocations": (
                ItemAllocation(
                    item_id="item-1",
                    canonical_variant_id="variant-1",
                    quantity=1,
                    retailer_id="retailer-0",
                    checkout_group_id="plan-1-checkout-0",
                ),
                ItemAllocation(
                    item_id="item-1",
                    canonical_variant_id="variant-1",
                    quantity=1,
                    retailer_id="retailer-1",
                    checkout_group_id="plan-1-checkout-1",
                ),
            )
        }
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
            )
        }
    )

    assert CartOptimizationService().optimize(request).outcome is OptimizationOutcome.SELECTED


def test_split_allocation_order_does_not_change_result() -> None:
    plan = _plan("plan-1", "eval-1", checkout_groups=2).model_copy(
        update={
            "item_allocations": (
                ItemAllocation(
                    item_id="item-1",
                    canonical_variant_id="variant-1",
                    quantity=1,
                    retailer_id="retailer-0",
                    checkout_group_id="plan-1-checkout-0",
                ),
                ItemAllocation(
                    item_id="item-1",
                    canonical_variant_id="variant-1",
                    quantity=1,
                    retailer_id="retailer-1",
                    checkout_group_id="plan-1-checkout-1",
                ),
            )
        }
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
            )
        }
    )
    reordered = request.model_copy(
        update={
            "candidate_plans": (
                plan.model_copy(update={"item_allocations": tuple(reversed(plan.item_allocations))}),
            )
        }
    )
    service = CartOptimizationService()

    first = service.optimize(request)
    second = service.optimize(reordered)
    assert first.outcome is OptimizationOutcome.SELECTED
    assert first.optimization_id == second.optimization_id


def test_allocation_must_reference_declared_checkout_group() -> None:
    plan = _plan("plan-1", "eval-1").model_copy(
        update={
            "item_allocations": (
                _plan("plan-1", "eval-1").item_allocations[0].model_copy(
                    update={"checkout_group_id": "unknown-group"}
                ),
            )
        }
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    with pytest.raises(ValueError, match="undeclared checkout group"):
        CartOptimizationService().optimize(request)


def test_declared_empty_checkout_group_is_invalid() -> None:
    plan = _plan("plan-1", "eval-1", checkout_groups=2)
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    with pytest.raises(ValueError, match="empty checkout group"):
        CartOptimizationService().optimize(request)


def test_multiple_allocations_may_share_one_checkout_group() -> None:
    base = _plan("plan-1", "eval-1").item_allocations[0]
    plan = _plan("plan-1", "eval-1").model_copy(
        update={
            "item_allocations": (
                base,
                base.model_copy(update={"retailer_id": "another-retailer"}),
            )
        }
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
            )
        }
    )

    result = CartOptimizationService().optimize(request)

    assert result.chosen_plan_id == "plan-1"


def test_reordering_checkout_groups_and_allocations_does_not_change_result() -> None:
    plan = _plan("plan-1", "eval-1", checkout_groups=2).model_copy(
        update={
            "item_allocations": (
                ItemAllocation(
                    item_id="item-1",
                    canonical_variant_id="variant-1",
                    quantity=1,
                    retailer_id="retailer-0",
                    checkout_group_id="plan-1-checkout-0",
                ),
                ItemAllocation(
                    item_id="item-1",
                    canonical_variant_id="variant-1",
                    quantity=1,
                    retailer_id="retailer-1",
                    checkout_group_id="plan-1-checkout-1",
                ),
            )
        }
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
            )
        }
    )
    reordered = request.model_copy(
        update={
            "candidate_plans": (
                plan.model_copy(
                    update={
                        "item_allocations": tuple(reversed(plan.item_allocations)),
                        "checkout_groups": tuple(reversed(plan.checkout_groups)),
                    }
                ),
            )
        }
    )

    first = CartOptimizationService().optimize(request)
    second = CartOptimizationService().optimize(reordered)

    assert first.outcome is second.outcome is OptimizationOutcome.SELECTED
    assert first.optimization_id == second.optimization_id
    assert first.chosen_plan_id == second.chosen_plan_id


@pytest.mark.parametrize("requested_quantity", (2, 3))
def test_missing_or_under_allocated_item_is_infeasible(requested_quantity: int) -> None:
    request = _request(
        candidate_plans=(_plan("plan-1", "eval-1"),),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(
                    item_id="item-1",
                    canonical_variant_id="variant-1",
                    quantity=requested_quantity,
                ),
            )
        }
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.INFEASIBLE
    assert result.chosen_plan is None
    assert result.ranked_plan_ids == ()
    assert result.rejected_plans[0].plan_id == "plan-1"


def test_over_allocated_item_is_infeasible() -> None:
    plan = _plan("plan-1", "eval-1").model_copy(
        update={
            "item_allocations": (
                _plan("plan-1", "eval-1").item_allocations[0].model_copy(update={"quantity": 2}),
            )
        }
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.INFEASIBLE
    assert result.chosen_plan is None
    assert result.ranked_plan_ids == ()
    assert result.rejected_plans[0].plan_id == "plan-1"


@pytest.mark.parametrize("quantity", (0, -1))
def test_non_positive_allocation_quantity_is_invalid(quantity: int) -> None:
    plan = _plan("plan-1", "eval-1").model_copy(
        update={
            "item_allocations": (
                _plan("plan-1", "eval-1").item_allocations[0].model_copy(update={"quantity": quantity}),
            )
        }
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    with pytest.raises(ValueError, match="non-positive allocation quantity"):
        CartOptimizationService().optimize(request)


def test_exact_duplicate_allocation_is_invalid() -> None:
    allocation = _plan("plan-1", "eval-1").item_allocations[0]
    plan = _plan("plan-1", "eval-1").model_copy(
        update={"item_allocations": (allocation, allocation)}
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    with pytest.raises(ValueError, match="duplicate item allocation"):
        CartOptimizationService().optimize(request)


@pytest.mark.parametrize(
    "allocation",
    (
        ItemAllocation(
            item_id="unknown-item",
            canonical_variant_id="variant-1",
            quantity=1,
            retailer_id="retailer-0",
            checkout_group_id="plan-1-checkout-0",
        ),
        ItemAllocation(
            item_id="item-1",
            canonical_variant_id="unknown-variant",
            quantity=1,
            retailer_id="retailer-0",
            checkout_group_id="plan-1-checkout-0",
        ),
    ),
)
def test_allocation_for_unknown_logical_item_is_invalid(allocation: ItemAllocation) -> None:
    plan = _plan("plan-1", "eval-1").model_copy(update={"item_allocations": (allocation,)})
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    )

    with pytest.raises(ValueError, match="unknown cart item"):
        CartOptimizationService().optimize(request)


def test_multiple_requested_items_are_fulfilled_independently() -> None:
    first = _plan("plan-1", "eval-1").item_allocations[0]
    second = first.model_copy(
        update={
            "item_id": "item-2",
            "canonical_variant_id": "variant-2",
            "quantity": 2,
        }
    )
    plan = _plan("plan-1", "eval-1").model_copy(
        update={"item_allocations": (first, second)}
    )
    request = _request(
        candidate_plans=(plan,),
        evaluations=(_evaluation("eval-1", 1000),),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
                CartItemRequest(item_id="item-2", canonical_variant_id="variant-2", quantity=2),
            )
        }
    )

    assert CartOptimizationService().optimize(request).outcome is OptimizationOutcome.SELECTED


def test_structurally_infeasible_cheaper_plan_cannot_be_selected() -> None:
    cheap = _plan("cheap", "eval-cheap").model_copy(
        update={
            "item_allocations": (
                _plan("cheap", "eval-cheap").item_allocations[0].model_copy(update={"quantity": 1}),
            )
        }
    )
    expensive = _plan("expensive", "eval-expensive").model_copy(
        update={
            "item_allocations": (
                _plan("expensive", "eval-expensive").item_allocations[0].model_copy(update={"quantity": 2}),
            )
        }
    )
    request = _request(
        candidate_plans=(cheap, expensive),
        evaluations=(_evaluation("eval-cheap", 100), _evaluation("eval-expensive", 1000)),
    ).model_copy(
        update={
            "cart_items": (
                CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=2),
            )
        }
    )

    result = CartOptimizationService().optimize(request)

    assert result.outcome is OptimizationOutcome.SELECTED
    assert result.chosen_plan_id == "expensive"
    assert result.rejected_plans[0].plan_id == "cheap"
