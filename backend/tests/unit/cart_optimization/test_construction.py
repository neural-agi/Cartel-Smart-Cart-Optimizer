import pytest

from app.cart_optimization import (
    CandidateAllocationSet,
    CandidateItemAllocation,
    CandidateEnumerationStatus,
    CandidatePlanConstructionInput,
    CandidatePlanConstructionService,
    CartItemRequest,
    CartOptimizationRequest,
    CandidatePlanCoverage,
    CheckoutGroup,
    EffectiveCostEvaluationReference,
    RetailerAllocation,
)
from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.service import CartOptimizationService
from app.cart_optimization.enums import CoverageState
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.enums import TaxStatus
from app.data_ingestion.observation_registry.comparison import ComparableRetailObservation


def _candidate(
    *,
    listing_id: str,
    observation_id: str,
    item_id: str = "item-1",
    variant_id: str = "variant-1",
    quantity: int = 1,
    platform: str = "platform-1",
    price: int = 100,
    retailer_id: str = "retailer-1",
    checkout_group_id: str = "group-1",
) -> CandidateItemAllocation:
    return CandidateItemAllocation.from_comparable_observation(
        item_id=item_id,
        canonical_variant_id=variant_id,
        quantity=quantity,
        retailer_id=retailer_id,
        checkout_group_id=checkout_group_id,
        observation=ComparableRetailObservation(
            observation_id=observation_id,
            platform=platform,
            platform_listing_id=listing_id,
            canonical_product_id="product-1",
            canonical_variant_id=variant_id,
            observed_selling_price=Money(currency="INR", minor_units=price),
            tax_status=TaxStatus.INCLUDED,
        ),
    )


def _input(allocations: tuple[CandidateItemAllocation, ...], plan_id: str = "plan-1"):
    return CandidatePlanConstructionInput(
        plan_id=plan_id,
        inconvenience_penalty_units=7,
        retailer_preference_priority=3,
        candidate_item_allocations=allocations,
        retailer_allocations=(RetailerAllocation(retailer_id="retailer-1", checkout_group_id="group-1"),),
        checkout_groups=(
            CheckoutGroup(
                checkout_group_id="group-1",
                retailer_id="retailer-1",
                effective_cost_evaluation_id="ece-1",
            ),
        ),
        effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
            effective_cost_evaluation_id="ece-1"
        ),
        effective_cost_evaluation=EffectiveCostEvaluationResult(
            evaluation_id="ece-1", context_id="context-1"
        ),
        feasibility=PlanFeasibility.FEASIBLE,
        feasibility_evidence=("upstream-feasibility-1",),
    )


def test_enumeration_is_exhaustive_and_reorder_stable() -> None:
    service = CandidatePlanConstructionService()
    first = _candidate(listing_id="listing-a", observation_id="obs-a")
    second = _candidate(listing_id="listing-b", observation_id="obs-b")
    item = CandidateAllocationSet(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=1,
        candidates=(second, first),
    )

    combinations = service.enumerate_allocations((item,))
    reordered = service.enumerate_allocations(
        (item.model_copy(update={"candidates": (first, second)}),)
    )

    assert combinations.status is CandidateEnumerationStatus.complete
    assert combinations.combinations == reordered.combinations
    assert [row[0].listing_provenance.platform_listing_id for row in combinations.combinations] == [
        "listing-a",
        "listing-b",
    ]


def test_enumeration_is_cartesian_across_multiple_items() -> None:
    service = CandidatePlanConstructionService()
    item_a = CandidateAllocationSet(
        item_id="item-a", canonical_variant_id="variant-a", quantity=1,
        candidates=tuple(
            _candidate(listing_id=f"a-{index}", observation_id=f"obs-a-{index}", item_id="item-a", variant_id="variant-a")
            for index in (2, 1)
        ),
    )
    item_b = CandidateAllocationSet(
        item_id="item-b", canonical_variant_id="variant-b", quantity=1,
        candidates=tuple(
            _candidate(listing_id=f"b-{index}", observation_id=f"obs-b-{index}", item_id="item-b", variant_id="variant-b")
            for index in (3, 1, 2)
        ),
    )

    result = service.enumerate_allocations((item_b, item_a))
    reordered = service.enumerate_allocations((item_a, item_b))

    assert len(result.combinations) == 6
    assert result.combinations == reordered.combinations
    assert {
        tuple(allocation.listing_provenance.platform_listing_id for allocation in combination)
        for combination in result.combinations
    } == {
        (f"a-{a}", f"b-{b}") for a in (1, 2) for b in (1, 2, 3)
    }


def test_enumeration_requires_each_candidate_to_cover_requested_quantity() -> None:
    with pytest.raises(ValueError, match="full-quantity"):
        CandidateAllocationSet(
            item_id="item-1", canonical_variant_id="variant-1", quantity=2,
            candidates=(_candidate(listing_id="listing-1", observation_id="obs-1", quantity=1),),
        )


def test_distinct_candidate_evidence_is_preserved_without_deduplication() -> None:
    candidates = (
        _candidate(listing_id="listing-a", observation_id="obs-a", platform="platform-a", price=100, retailer_id="retailer-a"),
        _candidate(listing_id="listing-b", observation_id="obs-b", platform="platform-b", price=200, retailer_id="retailer-b"),
        _candidate(listing_id="listing-a", observation_id="obs-c", platform="platform-a", price=300, retailer_id="retailer-a"),
    )
    result = CandidatePlanConstructionService().enumerate_allocations((CandidateAllocationSet(
        item_id="item-1", canonical_variant_id="variant-1", quantity=1, candidates=candidates,
    ),))

    assert len(result.combinations) == 3
    assert {(row[0].listing_provenance.observation_id, row[0].listing_provenance.observed_selling_price.minor_units)
            for row in result.combinations} == {("obs-a", 100), ("obs-b", 200), ("obs-c", 300)}


def test_zero_candidate_sets_produce_explicit_no_plan_result() -> None:
    result = CandidatePlanConstructionService().enumerate_allocations(
        (
            CandidateAllocationSet(
                item_id="item-1",
                canonical_variant_id="variant-1",
                quantity=1,
                candidates=(),
            ),
        )
    )

    assert result.status is CandidateEnumerationStatus.no_plan
    assert result.combinations == ()
    assert result.reason is not None


def test_construction_consumes_supplied_inputs_and_preserves_provenance() -> None:
    candidate = _candidate(listing_id="listing-a", observation_id="obs-a")
    plan = CandidatePlanConstructionService().construct_plan(_input((candidate,)))

    assert plan.plan_id == "plan-1"
    assert plan.inconvenience_penalty_units == 7
    assert plan.retailer_preference_priority == 3
    assert plan.item_allocations[0].listing_provenance == candidate.listing_provenance


def test_construction_rejects_missing_feasibility_evidence() -> None:
    with pytest.raises(ValueError, match="feasibility evidence"):
        CandidatePlanConstructionInput.model_validate(
            _input(
                (_candidate(listing_id="listing-a", observation_id="obs-a"),)
            ).model_dump(mode="python")
            | {"feasibility_evidence": ()}
        )


def test_construction_rejects_mismatched_ece_reference() -> None:
    with pytest.raises(ValueError, match="does not match plan reference"):
        CandidatePlanConstructionInput.model_validate(
            _input(
                (_candidate(listing_id="listing-a", observation_id="obs-a"),)
            ).model_dump(mode="python")
            | {
                "effective_cost_evaluation": EffectiveCostEvaluationResult(
                    evaluation_id="ece-2", context_id="context-1"
                )
            }
        )


@pytest.mark.parametrize("missing_field", ["effective_cost_evaluation_reference", "effective_cost_evaluation"])
def test_construction_rejects_missing_ece_inputs(missing_field: str) -> None:
    payload = _input(
        (_candidate(listing_id="listing-a", observation_id="obs-a"),)
    ).model_dump(mode="python")
    payload.pop(missing_field)

    with pytest.raises(ValueError):
        CandidatePlanConstructionInput.model_validate(payload)


def test_unknown_supplied_ece_is_rejected_at_optimizer_handoff() -> None:
    supplied = _input((_candidate(listing_id="listing-a", observation_id="obs-a"),)).model_copy(
        update={
            "effective_cost_evaluation": EffectiveCostEvaluationResult(
                evaluation_id="ece-1",
                context_id="context-1",
                unknown_components=("effective_cost",),
            )
        }
    )
    request = CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        cart_items=(CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),),
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE, scope_reference="scope-1", candidate_set_reference="set-1",
            coverage_basis="supplied", validation_reference="validation-1",
        ),
    )
    attached = CandidatePlanConstructionService().attach_to_request(request, (supplied,))

    with pytest.raises(ValueError, match="known linked effective cost"):
        CartOptimizationService().optimize(attached)


def test_currency_mismatch_is_rejected_at_optimizer_handoff() -> None:
    first = _input((_candidate(listing_id="listing-a", observation_id="obs-a"),), plan_id="plan-a").model_copy(
        update={
            "effective_cost_evaluation": EffectiveCostEvaluationResult(
                evaluation_id="ece-1", context_id="context-1", effective_cost=Money(currency="INR", minor_units=100)
            )
        }
    )
    second = _input((_candidate(listing_id="listing-b", observation_id="obs-b"),), plan_id="plan-b").model_copy(
        update={
            "effective_cost_evaluation_reference": EffectiveCostEvaluationReference(effective_cost_evaluation_id="ece-2"),
            "effective_cost_evaluation": EffectiveCostEvaluationResult(
                evaluation_id="ece-2", context_id="context-2", effective_cost=Money(currency="USD", minor_units=100)
            ),
        }
    )
    request = CartOptimizationRequest(
        request_id="request-1", optimization_policy_version="policy-v1",
        cart_items=(CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),),
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE, scope_reference="scope-1", candidate_set_reference="set-1",
            coverage_basis="supplied", validation_reference="validation-1",
        ),
    )
    attached = CandidatePlanConstructionService().attach_to_request(request, (first, second))

    with pytest.raises(ValueError, match="currencies must match"):
        CartOptimizationService().optimize(attached)


def test_batch_construction_rejects_duplicate_supplied_plan_ids() -> None:
    service = CandidatePlanConstructionService()
    supplied = _input((_candidate(listing_id="listing-a", observation_id="obs-a"),))

    with pytest.raises(ValueError, match="duplicate supplied plan IDs"):
        service.construct_plans((supplied, supplied))


@pytest.mark.parametrize("plan_id", ["", "   "])
def test_construction_rejects_empty_supplied_plan_id(plan_id: str) -> None:
    with pytest.raises(ValueError, match="supplied plan ID"):
        _input((_candidate(listing_id="listing-a", observation_id="obs-a"),), plan_id=plan_id)


def test_supplied_plan_ids_are_preserved_and_output_order_is_deterministic() -> None:
    service = CandidatePlanConstructionService()
    plans = service.construct_plans((
        _input((_candidate(listing_id="listing-b", observation_id="obs-b"),), plan_id="plan-b"),
        _input((_candidate(listing_id="listing-a", observation_id="obs-a"),), plan_id="plan-a"),
    ))

    assert [plan.plan_id for plan in plans] == ["plan-a", "plan-b"]


@pytest.mark.parametrize("state", [PlanFeasibility.FEASIBLE, PlanFeasibility.INFEASIBLE, PlanFeasibility.UNRESOLVED])
def test_supplied_feasibility_state_is_preserved(state: PlanFeasibility) -> None:
    plan = CandidatePlanConstructionService().construct_plan(
        _input((_candidate(listing_id="listing-a", observation_id="obs-a"),)).model_copy(update={"feasibility": state})
    )
    assert plan.feasibility is state


def test_invalid_feasibility_state_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid plans"):
        CandidatePlanConstructionInput.model_validate(
            _input((_candidate(listing_id="listing-a", observation_id="obs-a"),)).model_dump(mode="python")
            | {"feasibility": PlanFeasibility.INVALID}
        )


def test_supplied_penalty_and_preference_are_not_derived_or_changed() -> None:
    supplied = _input((_candidate(listing_id="listing-a", observation_id="obs-a"),)).model_copy(
        update={"inconvenience_penalty_units": 41, "retailer_preference_priority": -7}
    )
    plan = CandidatePlanConstructionService().construct_plan(supplied)

    assert plan.inconvenience_penalty_units == 41
    assert plan.retailer_preference_priority == -7


def test_construction_attaches_supplied_plans_and_ece_to_existing_request() -> None:
    request = CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        cart_items=(
            CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),
        ),
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE,
            scope_reference="scope-1",
            candidate_set_reference="set-1",
            coverage_basis="supplied",
            validation_reference="validation-1",
        ),
    )
    supplied = _input((_candidate(listing_id="listing-a", observation_id="obs-a"),))

    attached = CandidatePlanConstructionService().attach_to_request(request, (supplied,))

    assert attached.candidate_plans[0].plan_id == "plan-1"
    assert attached.effective_cost_evaluations[0].evaluation_id == "ece-1"


def test_attach_preserves_two_plan_references_sharing_one_ece() -> None:
    request = CartOptimizationRequest(
        request_id="request-1", optimization_policy_version="policy-v1",
        cart_items=(CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),),
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE, scope_reference="scope-1", candidate_set_reference="set-1",
            coverage_basis="supplied", validation_reference="validation-1",
        ),
    )
    service = CandidatePlanConstructionService()
    supplied = (
        _input((_candidate(listing_id="listing-a", observation_id="obs-a"),), plan_id="plan-a"),
        _input((_candidate(listing_id="listing-b", observation_id="obs-b"),), plan_id="plan-b"),
    )
    attached = service.attach_to_request(request, supplied)

    assert [plan.effective_cost_evaluation_reference.effective_cost_evaluation_id for plan in attached.candidate_plans] == ["ece-1", "ece-1"]
    assert [evaluation.evaluation_id for evaluation in attached.effective_cost_evaluations] == ["ece-1"]


def test_attach_rejects_conflicting_results_with_same_ece_id() -> None:
    request = CartOptimizationRequest(
        request_id="request-1", optimization_policy_version="policy-v1",
        cart_items=(CartItemRequest(item_id="item-1", canonical_variant_id="variant-1", quantity=1),),
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE, scope_reference="scope-1", candidate_set_reference="set-1",
            coverage_basis="supplied", validation_reference="validation-1",
        ),
        effective_cost_evaluations=(EffectiveCostEvaluationResult(evaluation_id="ece-1", context_id="existing"),),
    )
    supplied = _input((_candidate(listing_id="listing-a", observation_id="obs-a"),))

    with pytest.raises(ValueError, match="conflicting effective-cost"):
        CandidatePlanConstructionService().attach_to_request(request, (supplied,))
