from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import create_application
from app.api.routes.cost_intelligence import CostIntelligenceEvaluateRequest
from app.cart_optimization.enums import CoverageState
from app.cart_optimization.types import CandidatePlanCoverage, CartOptimizationRequest
from app.cost_intelligence.observation.types import CheckoutObservation
from app.product_intelligence.models import EvidenceReference


def _payload() -> dict:
    request = CostIntelligenceEvaluateRequest(
        observation=CheckoutObservation(
            platform="blinkit",
            source_artifact_reference="checkout-artifact-1",
            capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            parser_version="checkout-v1",
            evidence_references=(
                EvidenceReference(source_type="artifact", source_id="checkout-1"),
            ),
            totals=(
                {"label": "Subtotal", "amount": {"currency": "INR", "minor_units": 1000}},
            ),
        ),
        optimization_request=CartOptimizationRequest(
            request_id="api-request-1",
            optimization_policy_version="policy-v1",
            candidate_plan_coverage=CandidatePlanCoverage(
                state=CoverageState.COMPLETE,
                scope_reference="scope-1",
                candidate_set_reference="set-1",
                coverage_basis="api-test",
                validation_reference="validation-1",
            ),
        ),
    )
    return request.model_dump(mode="json")


def test_valid_request_returns_complete_pipeline_result() -> None:
    client = TestClient(create_application())

    response = client.post("/api/v1/cost-intelligence/evaluate", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["context"]["context_id"]
    assert "effective_cost_result" in body
    assert "optimization_result" in body


def test_identical_requests_return_identical_responses() -> None:
    client = TestClient(create_application())
    payload = _payload()

    first = client.post("/api/v1/cost-intelligence/evaluate", json=payload)
    second = client.post("/api/v1/cost-intelligence/evaluate", json=payload)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


def test_malformed_request_returns_validation_error() -> None:
    client = TestClient(create_application())

    response = client.post("/api/v1/cost-intelligence/evaluate", json={})

    assert response.status_code == 422


def test_pipeline_validation_failure_returns_deterministic_client_error() -> None:
    client = TestClient(create_application())
    payload = _payload()
    payload["observation"]["evidence_references"] = []

    response = client.post("/api/v1/cost-intelligence/evaluate", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "cost context requires an evidence-backed observation"


def test_response_contract_contains_serialized_stage_outputs() -> None:
    client = TestClient(create_application())

    response = client.post("/api/v1/cost-intelligence/evaluate", json=_payload())

    body = response.json()
    assert isinstance(body["offer_results"], list)
    assert isinstance(body["fee_results"], list)
    assert isinstance(body["membership_results"], list)
    assert isinstance(body["context"]["checkout_observation"], dict)
