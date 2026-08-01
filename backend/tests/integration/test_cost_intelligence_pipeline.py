from unittest.mock import Mock

from app.cart_optimization.enums import CoverageState, PlanFeasibility
from app.cart_optimization.types import (
    CandidatePlanCoverage,
    CartOptimizationRequest,
)
from app.cost_intelligence.evaluation.types import (
    EffectiveCostEvaluationResult,
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
    OfferType,
)
from app.cost_intelligence.fee.types import FeeType
from app.cost_intelligence.observation.types import CheckoutObservation
from app.cost_intelligence.pipeline.service import CostIntelligencePipelineService
from app.cart_optimization.types import CartOptimizationResult
from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


def _observation() -> CheckoutObservation:
    from datetime import datetime, timezone

    return CheckoutObservation(
        platform="demo",
        source_artifact_reference="artifact-1",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="test-parser",
        evidence_references=(EvidenceReference(source_type="test", source_id="evidence-1"),),
    )


def _request() -> CartOptimizationRequest:
    return CartOptimizationRequest(
        request_id="request-1",
        optimization_policy_version="policy-v1",
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE,
            scope_reference="scope-1",
            candidate_set_reference="set-1",
            coverage_basis="integration",
            validation_reference="validation-1",
        ),
    )


def _stubbed_pipeline() -> tuple[CostIntelligencePipelineService, dict[str, Mock]]:
    context = CostContext(
        context_id="context-1",
        checkout_observation=_observation(),
        evidence_references=_observation().evidence_references,
    )
    offer_results = (
        OfferEvaluationResult(
            evaluation_id="offer-1",
            offer_reference="offer-1",
            offer_type=OfferType.UNKNOWN,
        ),
    )
    fee_results = (
        FeeEvaluationResult(
            evaluation_id="fee-1",
            fee_reference="fee-1",
            fee_type=FeeType.UNKNOWN,
        ),
    )
    membership_results = (
        MembershipEvaluationResult(evaluation_id="membership-1", membership_reference="membership-1"),
    )
    effective = EffectiveCostEvaluationResult(evaluation_id="effective-1", context_id="context-1")
    optimization = CartOptimizationResult(
        optimization_id="optimization-1",
        request_id="request-1",
        outcome="unresolved",
    )
    dependencies = {
        "context": Mock(build=Mock(return_value=context)),
        "offer": Mock(evaluate=Mock(return_value=offer_results)),
        "fee": Mock(evaluate=Mock(return_value=fee_results)),
        "membership": Mock(evaluate=Mock(return_value=membership_results)),
        "effective": Mock(evaluate=Mock(return_value=effective)),
        "optimization": Mock(optimize=Mock(return_value=optimization)),
    }
    return (
        CostIntelligencePipelineService(
            context_builder=dependencies["context"],
            offer_orchestrator=dependencies["offer"],
            fee_orchestrator=dependencies["fee"],
            membership_orchestrator=dependencies["membership"],
            effective_cost_orchestrator=dependencies["effective"],
            cart_optimization_orchestrator=dependencies["optimization"],
        ),
        dependencies,
    )


def test_pipeline_composes_each_stage_once_and_preserves_outputs() -> None:
    pipeline, dependencies = _stubbed_pipeline()

    result = pipeline.run(_observation(), _request())

    assert result.context.context_id == "context-1"
    assert result.offer_results[0].evaluation_id == "offer-1"
    assert result.fee_results[0].evaluation_id == "fee-1"
    assert result.membership_results[0].evaluation_id == "membership-1"
    assert result.effective_cost_result.evaluation_id == "effective-1"
    assert result.optimization_result.optimization_id == "optimization-1"
    for dependency in dependencies.values():
        method = next(iter(dependency.method_calls))[0]
        assert getattr(dependency, method).call_count == 1


def test_pipeline_replay_is_deterministic() -> None:
    pipeline, _ = _stubbed_pipeline()
    observation = _observation()
    request = _request()

    first = pipeline.run(observation, request)
    second = pipeline.run(observation, request)

    assert first == second
    assert observation == _observation()
    assert request == _request()


def test_pipeline_propagates_stage_exceptions() -> None:
    error = RuntimeError("stage failure")
    dependencies = _stubbed_pipeline()[1]
    dependencies["fee"].evaluate.side_effect = error
    pipeline = CostIntelligencePipelineService(
        context_builder=dependencies["context"],
        offer_orchestrator=dependencies["offer"],
        fee_orchestrator=dependencies["fee"],
        membership_orchestrator=dependencies["membership"],
        effective_cost_orchestrator=dependencies["effective"],
        cart_optimization_orchestrator=dependencies["optimization"],
    )

    try:
        pipeline.run(_observation(), _request())
    except RuntimeError as raised:
        assert raised is error
    else:
        raise AssertionError("pipeline did not propagate the stage exception")
