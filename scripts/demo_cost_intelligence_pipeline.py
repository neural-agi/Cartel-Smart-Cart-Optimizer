from datetime import datetime, timezone

from app.cart_optimization.enums import CoverageState
from app.cart_optimization.types import CandidatePlanCoverage, CartOptimizationRequest
from app.cost_intelligence.observation.types import CheckoutObservation
from app.cost_intelligence.pipeline.service import CostIntelligencePipelineService
from app.product_intelligence.models import EvidenceReference


def build_observation() -> CheckoutObservation:
    return CheckoutObservation(
        platform="demo",
        source_artifact_reference="checkout-artifact-1",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        evidence_references=(
            EvidenceReference(source_type="demo", source_id="checkout-evidence-1"),
        ),
    )


def build_request() -> CartOptimizationRequest:
    return CartOptimizationRequest(
        request_id="pipeline-demo-request",
        optimization_policy_version="policy-v1",
        candidate_plan_coverage=CandidatePlanCoverage(
            state=CoverageState.COMPLETE,
            scope_reference="demo-scope",
            candidate_set_reference="demo-candidates",
            coverage_basis="deterministic demo",
            validation_reference="demo-validation",
        ),
    )


def main() -> None:
    pipeline = CostIntelligencePipelineService()
    observation = build_observation()
    request = build_request()
    first = pipeline.run(observation, request)
    second = pipeline.run(observation, request)

    print(f"Context ID: {first.context.context_id}")
    print(f"Offer Evaluations: {len(first.offer_results)}")
    print(f"Fee Evaluations: {len(first.fee_results)}")
    print(f"Membership Evaluations: {len(first.membership_results)}")
    print(f"Effective Cost: {first.effective_cost_result.effective_cost}")
    print(f"Optimization ID: {first.optimization_result.optimization_id}")
    print(f"Optimization Outcome: {first.optimization_result.outcome.value}")
    print(f"Chosen Plan ID: {first.optimization_result.chosen_plan_id}")
    print(f"Replay Equality: {first == second}")


if __name__ == "__main__":
    main()
