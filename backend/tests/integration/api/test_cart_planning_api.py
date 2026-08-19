from unittest.mock import Mock
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from app.core.config import Settings
from app.cart_optimization.planning import CartPlanningService
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.types import NormalizedObservation
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItem,
    CartCandidateDiscoveryResult,
    CartCandidateDiscoveryStatus,
    PersistedCandidateReadiness,
    PersistedListingCandidate,
)
from app.cost_intelligence.observation.types import CheckoutObservation, CheckoutTotalObservation
from app.cost_intelligence.observation.capture import CheckoutCaptureRegistration
from app.product_intelligence.models import EvidenceReference
from app.cart_optimization.providers import PlanningProviderUnavailable


def _candidate(listing: str, observation: str, item: str, price: int = 100):
    return PersistedListingCandidate(
        platform="platform-1",
        platform_listing_id=listing,
        canonical_product_id=f"product-{item}",
        canonical_variant_id=f"variant-{item}",
        observation_id=observation,
        observation=NormalizedObservation.model_construct(
            observed_selling_price=Money(currency="INR", minor_units=price),
        ),
        readiness=PersistedCandidateReadiness.ready_for_allocation,
    )


def _payload(*, plans=None, contexts=None):
    plans = plans or [{
        "plan_id": "plan-1",
        "combination_index": 0,
        "inconvenience_penalty_units": 1,
        "retailer_preference_priority": 5,
        "checkout_groups": [{
            "checkout_group_id": "group-1",
            "retailer_id": "retailer-1",
            "effective_cost_evaluation_id": "ece-1",
        }],
        "effective_cost_evaluation_reference": {"effective_cost_evaluation_id": "ece-1"},
        "effective_cost_evaluation": {
            "evaluation_id": "ece-1",
            "context_id": "context-1",
            "effective_cost": {"currency": "INR", "minor_units": 100},
        },
        "feasibility": "feasible",
        "feasibility_evidence": ["evidence-1"],
    }]
    contexts = contexts if contexts is not None else [{
        "key": {
            "item_id": "item-1",
            "platform": "platform-1",
            "platform_listing_id": "listing-1",
            "observation_id": "observation-1",
        },
        "retailer_id": "retailer-1",
        "checkout_group_id": "group-1",
    }]
    return {
        "discovery": {"items": [{
            "item_id": "item-1",
            "quantity": 1,
            "canonical_product_id": "product-item-1",
            "canonical_variant_id": "variant-item-1",
        }]},
        "candidate_contexts": contexts,
        "plans": plans,
        "request_id": "request-1",
        "optimization_policy_version": "policy-v1",
    }


def _client(candidate=None, *, readiness=PersistedCandidateReadiness.ready_for_allocation, result=None):
    application = create_application()
    candidate = candidate or _candidate("listing-1", "observation-1", "item-1")
    item = CartCandidateDiscoveryItem(
        item_id="item-1",
        quantity=1,
        canonical_product_id="product-item-1",
        canonical_variant_id="variant-item-1",
        status=(
            CartCandidateDiscoveryStatus.candidates_available
            if readiness is PersistedCandidateReadiness.ready_for_allocation
            else CartCandidateDiscoveryStatus.candidates_not_ready
        ),
        candidates=(candidate.model_copy(update={"readiness": readiness}),),
    )
    discovery = Mock()
    discovery.discover.return_value = result or CartCandidateDiscoveryResult(items=(item,))
    application.state.cart_candidate_discovery = discovery
    application.state.cart_planning = CartPlanningService(discovery=discovery)
    return TestClient(application)


def test_cart_plan_api_runs_full_application_flow() -> None:
    with _client() as client:
        response = client.post("/api/v1/cart/plan", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["chosen_plan_id"] == "plan-1"
    assert body["chosen_plan"]["item_allocations"][0]["retailer_id"] == "retailer-1"
    assert body["chosen_plan"]["item_allocations"][0]["checkout_group_id"] == "group-1"
    assert body["chosen_plan"]["feasibility"] == "feasible"
    assert body["chosen_plan"]["effective_cost_evaluation_reference"]["effective_cost_evaluation_id"] == "ece-1"


def test_cart_plan_api_rejects_missing_context() -> None:
    with _client() as client:
        response = client.post("/api/v1/cart/plan", json=_payload(contexts=[]))
    assert response.status_code == 422
    assert "missing candidate context" in response.json()["detail"]


@pytest.mark.parametrize("field", ["retailer_id", "checkout_group_id"])
def test_cart_plan_api_rejects_blank_enrichment(field: str) -> None:
    contexts = _payload()["candidate_contexts"]
    contexts[0][field] = ""
    with _client() as client:
        response = client.post("/api/v1/cart/plan", json=_payload(contexts=contexts))
    assert response.status_code == 422


def test_cart_plan_api_rejects_not_ready_candidates() -> None:
    with _client(readiness=PersistedCandidateReadiness.not_ready_for_allocation) as client:
        response = client.post("/api/v1/cart/plan", json=_payload())
    assert response.status_code == 422


def test_cart_plan_api_rejects_duplicate_plan_ids_and_unknown_combination() -> None:
    duplicate = _payload(plans=[_payload()["plans"][0], _payload()["plans"][0]])
    with _client() as client:
        duplicate_response = client.post("/api/v1/cart/plan", json=duplicate)
        assert duplicate_response.status_code == 422
        assert "duplicate supplied plan IDs" in duplicate_response.json()["detail"]

        unknown = _payload()
        unknown["plans"][0]["combination_index"] = 3
        unknown_response = client.post("/api/v1/cart/plan", json=unknown)
        assert unknown_response.status_code == 422
        assert "combination index" in unknown_response.json()["detail"]


def test_cart_plan_api_rejects_missing_ece_linkage() -> None:
    payload = _payload()
    payload["plans"][0].pop("effective_cost_evaluation_reference")
    with _client() as client:
        response = client.post("/api/v1/cart/plan", json=payload)
    assert response.status_code == 422


def test_cart_plan_api_enumerates_and_ranks_multiple_items_and_plans() -> None:
    a1 = _candidate("a1", "oa1", "a", 100)
    a2 = _candidate("a2", "oa2", "a", 110)
    b1 = _candidate("b1", "ob1", "b", 100)
    b2 = _candidate("b2", "ob2", "b", 110)
    result = CartCandidateDiscoveryResult(items=(
        CartCandidateDiscoveryItem(
            item_id="a", quantity=1, canonical_product_id="product-a",
            canonical_variant_id="variant-a", status=CartCandidateDiscoveryStatus.candidates_available,
            candidates=(a1, a2),
        ),
        CartCandidateDiscoveryItem(
            item_id="b", quantity=1, canonical_product_id="product-b",
            canonical_variant_id="variant-b", status=CartCandidateDiscoveryStatus.candidates_available,
            candidates=(b1, b2),
        ),
    ))
    contexts = [
        {"key": {"item_id": "a", "platform": "platform-1", "platform_listing_id": "a1", "observation_id": "oa1"}, "retailer_id": "r1", "checkout_group_id": "g1"},
        {"key": {"item_id": "a", "platform": "platform-1", "platform_listing_id": "a2", "observation_id": "oa2"}, "retailer_id": "r2", "checkout_group_id": "g2"},
        {"key": {"item_id": "b", "platform": "platform-1", "platform_listing_id": "b1", "observation_id": "ob1"}, "retailer_id": "r1", "checkout_group_id": "g1"},
        {"key": {"item_id": "b", "platform": "platform-1", "platform_listing_id": "b2", "observation_id": "ob2"}, "retailer_id": "r2", "checkout_group_id": "g2"},
    ]
    def plan(plan_id, index, group, penalty, priority, cost):
        return {"plan_id": plan_id, "combination_index": index,
                "inconvenience_penalty_units": penalty,
                "retailer_preference_priority": priority,
                "checkout_groups": [{"checkout_group_id": group, "retailer_id": group.replace("g", "r"), "effective_cost_evaluation_id": plan_id + "-ece"}],
                "effective_cost_evaluation_reference": {"effective_cost_evaluation_id": plan_id + "-ece"},
                "effective_cost_evaluation": {"evaluation_id": plan_id + "-ece", "context_id": plan_id + "-ctx", "effective_cost": {"currency": "INR", "minor_units": cost}},
                "feasibility": "feasible", "feasibility_evidence": ["upstream"]}
    payload = {
        "discovery": {"items": [
            {"item_id": "a", "quantity": 1, "canonical_product_id": "product-a", "canonical_variant_id": "variant-a"},
            {"item_id": "b", "quantity": 1, "canonical_product_id": "product-b", "canonical_variant_id": "variant-b"},
        ]},
        "candidate_contexts": contexts,
        "plans": [plan("plan-r1", 0, "g1", 1, 1, 100), plan("plan-r2", 3, "g2", 2, 9, 110)],
        "request_id": "multi-request", "optimization_policy_version": "policy-v1",
    }
    with _client(result=result) as client:
        response = client.post("/api/v1/cart/plan", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ranked_plan_ids"] == ["plan-r1", "plan-r2"]
    assert body["chosen_plan_id"] == "plan-r1"
    assert len(body["chosen_plan"]["item_allocations"]) == 2


def _checkout_observation(total: int = 100) -> CheckoutObservation:
    return CheckoutObservation(
        platform="checkout-platform",
        source_artifact_reference="checkout-artifact",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="checkout-v1",
        evidence_references=(EvidenceReference(source_type="test", source_id="checkout-evidence"),),
        totals=(CheckoutTotalObservation(label="subtotal", amount=Money(currency="INR", minor_units=total)),),
    )


def test_cart_plan_api_evaluates_caller_checkout_observation() -> None:
    payload = _payload()
    payload["plans"][0].pop("effective_cost_evaluation_reference")
    payload["plans"][0].pop("effective_cost_evaluation")
    payload["checkout_observations"] = {"plan-1": _checkout_observation().model_dump(mode="json")}
    with _client() as client:
        response = client.post("/api/v1/cart/plan", json=payload)
    assert response.status_code == 200, response.text
    reference = response.json()["chosen_plan"]["effective_cost_evaluation_reference"]
    assert reference["effective_cost_evaluation_id"]
    assert reference["effective_cost_evaluation_id"] != "ece-1"


class _FakeCheckoutProvider:
    def get_observation(self, *, plan_id: str, request_id: str):
        if plan_id != "plan-1":
            return None
        return _checkout_observation()


def test_cart_plan_api_uses_injected_checkout_provider() -> None:
    client = _client()
    application = client.app
    discovery = application.state.cart_candidate_discovery
    application.state.cart_planning = CartPlanningService(
        discovery=discovery,
        checkout_provider=_FakeCheckoutProvider(),
    )
    payload = _payload()
    payload["plans"][0].pop("effective_cost_evaluation_reference")
    payload["plans"][0].pop("effective_cost_evaluation")
    with client:
        response = client.post("/api/v1/cart/plan", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["chosen_plan"]["effective_cost_evaluation_reference"]["effective_cost_evaluation_id"]


def test_cart_plan_api_returns_503_when_checkout_provider_is_unavailable() -> None:
    payload = _payload()
    payload["plans"][0].pop("effective_cost_evaluation_reference")
    payload["plans"][0].pop("effective_cost_evaluation")
    with _client() as client:
        response = client.post("/api/v1/cart/plan", json=payload)
    assert response.status_code == 503
    assert "checkout observation" in response.json()["detail"]


def test_cart_planning_consumes_registry_correlation_with_request_scoped_ownership(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path, checkout_observation_provider_mode="registry")
    application = create_application(settings)
    candidate = _candidate("listing-1", "observation-1", "item-1")
    item = CartCandidateDiscoveryItem(
        item_id="item-1",
        quantity=1,
        canonical_product_id="product-item-1",
        canonical_variant_id="variant-item-1",
        status=CartCandidateDiscoveryStatus.candidates_available,
        candidates=(candidate,),
    )
    discovery = Mock()
    discovery.discover.return_value = CartCandidateDiscoveryResult(items=(item,))
    application.state.cart_candidate_discovery = discovery
    # create_application wires discovery into the planner by value and exposes no
    # discovery replacement seam. Reconstruct only this test planner so the
    # deterministic discovery fixture is used, while retaining the exact
    # production-configured registry provider from the original planner.
    application.state.cart_planning = CartPlanningService(
        discovery=discovery,
        checkout_provider=application.state.cart_planning._checkout_provider,
    )
    application.state.checkout_capture_registration.register(
        CheckoutCaptureRegistration(
            request_id="request-1", plan_id="plan-1", observation=_checkout_observation()
        )
    )

    payload = _payload()
    payload["plans"][0].pop("effective_cost_evaluation_reference")
    payload["plans"][0].pop("effective_cost_evaluation")
    payload.pop("checkout_observations", None)

    with TestClient(application) as client:
        matching = client.post("/api/v1/cart/plan", json=payload)
        wrong_request = client.post(
            "/api/v1/cart/plan",
            json={**payload, "request_id": "request-2"},
        )

    assert matching.status_code == 200, matching.text
    assert matching.json()["chosen_plan"]["effective_cost_evaluation_reference"][
        "effective_cost_evaluation_id"
    ]
    assert wrong_request.status_code == 503
    assert "checkout observation" in wrong_request.json()["detail"]
