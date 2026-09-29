from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.cart_optimization.automatic_planning import (
    AutomaticCartPlanningService,
    AutomaticPlanningResult,
)
from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.planning import CartPlanningService
from app.cart_optimization.providers import (
    DeterministicPlanIdProvider,
    PlanningProviderUnavailable,
    UnavailableCheckoutObservationProvider,
)
from app.core.config import Settings
from app.cost_intelligence.observation.types import (
    CheckoutFeeObservation,
    CheckoutLineItemObservation,
    CheckoutObservation,
    CheckoutOfferObservation,
    CheckoutTotalObservation,
)
from app.cost_intelligence.pipeline.service import CostIntelligencePipelineService
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.models import EvidenceReference
from app.scrapers.blinkit.checkout_capture import BlinkitCheckoutCaptureUnavailable
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItem,
    CartCandidateDiscoveryResult,
    CartCandidateDiscoveryStatus,
    PersistedCandidateReadiness,
    PersistedListingCandidate,
)
from app.main import create_application


class FixedDiscovery:
    """Deterministic lowest-level discovery fixture; no persistence or network."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.calls = []

    def discover(self, request):
        self.calls.append(request)
        items = []
        for item in request.items:
            candidates = ()
            status = CartCandidateDiscoveryStatus.no_candidates
            if self.available:
                observation = NormalizedObservation.model_construct(
                    observed_selling_price=Money(currency="INR", minor_units=100),
                    platform_identifiers=(("retailer_product_id", "fixture-retailer-product"),),
                )
                candidates = (
                    PersistedListingCandidate(
                        platform="fixture",
                        platform_listing_id="fixture-listing-1",
                        canonical_product_id=item.canonical_product_id,
                        canonical_variant_id=item.canonical_variant_id,
                        observation_id="fixture-observation-1",
                        observation=observation,
                        readiness=PersistedCandidateReadiness.ready_for_allocation,
                    ),
                )
                status = CartCandidateDiscoveryStatus.candidates_available
            items.append(CartCandidateDiscoveryItem(
                item_id=item.item_id,
                quantity=item.quantity,
                canonical_product_id=item.canonical_product_id,
                canonical_variant_id=item.canonical_variant_id,
                status=status,
                reason=None if candidates else "no persisted listing candidates available",
                candidates=candidates,
            ))
        return CartCandidateDiscoveryResult(items=tuple(items))


class ExplicitRetailer:
    def retailer_id(self, **_kwargs):
        return "test-retailer"


class ExplicitGroup:
    def checkout_group_id(self, **_kwargs):
        return "test-checkout-group"


class ExplicitPolicy:
    def __init__(self, feasibility: PlanFeasibility = PlanFeasibility.FEASIBLE) -> None:
        self.feasibility = feasibility

    def resolve(self, **_kwargs):
        return 0, 0, self.feasibility, ("test supplied feasibility evidence",)


def _checkout_observation() -> CheckoutObservation:
    captured_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    evidence = (EvidenceReference(
        source_type="fixture_checkout",
        source_id="fixture://checkout/test-plan",
        capture_timestamp=captured_at,
        note="test-only structured checkout fixture",
    ),)
    return CheckoutObservation(
        platform="fixture",
        source_artifact_reference="fixture://checkout/test-plan",
        capture_timestamp=captured_at,
        parser_version="fixture-parser-v1",
        evidence_references=evidence,
        line_items=(CheckoutLineItemObservation(
            label="fixture item",
            quantity_text="1",
            displayed_price=Money(currency="INR", minor_units=2000),
        ),),
        fees=(CheckoutFeeObservation(
            label="delivery",
            amount=Money(currency="INR", minor_units=400),
            raw_text="delivery fee ₹4",
        ),),
        offers=(CheckoutOfferObservation(
            label="₹1 OFF",
            amount=Money(currency="INR", minor_units=100),
            raw_text="₹1 OFF",
        ),),
        totals=(
            CheckoutTotalObservation(
                label="subtotal",
                amount=Money(currency="INR", minor_units=2000),
            ),
            CheckoutTotalObservation(
                label="total",
                amount=Money(currency="INR", minor_units=2300),
            ),
        ),
    )


class FixtureCheckoutProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get_observation(self, *, plan_id: str, request_id: str):
        self.calls.append((request_id, plan_id))
        return _checkout_observation()


class AccessDeniedCapture:
    def capture(self, _request):
        raise BlinkitCheckoutCaptureUnavailable(
            "retailer_access_denied; secret diagnostic must not escape",
            reason_code="retailer_access_denied",
            diagnostics={"token": "must-not-escape"},
        )


def _client(
    tmp_path,
    *,
    discovery=None,
    checkout_provider=None,
    checkout_capture=None,
    feasibility=PlanFeasibility.FEASIBLE,
):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        checkout_observation_provider_mode="unavailable",
        checkout_capture_adapter_mode="unavailable",
        docs_enabled=False,
    )
    application = create_application(settings)
    discovery = discovery or FixedDiscovery()
    checkout_provider = checkout_provider or FixtureCheckoutProvider()
    application.state.automatic_cart_planning = AutomaticCartPlanningService(
        discovery=discovery,
        planning=application.state.cart_planning,
        retailer_provider=ExplicitRetailer(),
        checkout_group_provider=ExplicitGroup(),
        policy_provider=ExplicitPolicy(feasibility),
        plan_id_provider=DeterministicPlanIdProvider(),
        checkout_observation_provider=checkout_provider,
        cost_intelligence=CostIntelligencePipelineService(),
        checkout_capture=checkout_capture,
        optimization_policy_version="policy-v1",
    )
    return TestClient(application), discovery, checkout_provider


def _payload(cart_id: str = "request-a") -> dict:
    return {
        "cart_id": cart_id,
        "items": [{
            "item_id": "item-1",
            "canonical_product_id": "product-1",
            "canonical_variant_id": "variant-1",
            "quantity": 1,
        }],
    }


def test_optimize_api_configured_success_runs_real_planner_ece_and_optimizer(tmp_path) -> None:
    provider = FixtureCheckoutProvider()
    client, discovery, _ = _client(tmp_path, checkout_provider=provider)
    with client:
        first = client.post("/api/v1/cart/optimize", json=_payload("request-a"))
        second = client.post("/api/v1/cart/optimize", json=_payload("request-b"))

    assert first.status_code == second.status_code == 200
    first_body = AutomaticPlanningResult.model_validate(first.json())
    second_body = AutomaticPlanningResult.model_validate(second.json())
    assert first_body.status == "ready", first_body.unresolved_reasons
    assert second_body.status == "ready"
    assert first_body.optimization_result is not None
    assert second_body.optimization_result is not None
    assert first_body.optimization_result.outcome.value == "selected"
    assert first_body.optimization_result.request_id == "request-a"
    assert second_body.optimization_result.request_id == "request-b"
    assert first_body.optimization_result.request_id != second_body.optimization_result.request_id
    assert first_body.optimization_result.chosen_plan_id != "request-a"
    assert first_body.optimization_result.chosen_plan is not None
    chosen_plan = first_body.optimization_result.chosen_plan
    assert chosen_plan.effective_cost_evaluation_reference.effective_cost_evaluation_id
    serialized_plan = chosen_plan.model_dump(mode="json")
    assert "effective_cost" not in serialized_plan
    assert all(
        "observed_selling_price" not in allocation
        for allocation in serialized_plan["item_allocations"]
    )
    assert provider.calls[0][0] == "request-a"
    assert provider.calls[1][0] == "request-b"
    assert len(discovery.calls) == 2
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
    assert set(first.json()) == {
        "request_id", "status", "optimization_result", "unresolved_reasons"
    }


def test_optimize_api_returns_structured_unresolved_without_success_result(tmp_path) -> None:
    client, _, _ = _client(tmp_path, discovery=FixedDiscovery(available=False))
    with client:
        response = client.post("/api/v1/cart/optimize", json=_payload())

    assert response.status_code == 200
    body = AutomaticPlanningResult.model_validate(response.json())
    assert body.status == "unresolved"
    assert body.optimization_result is None
    assert body.unresolved_reasons == ("item-1: no persisted listing candidates available",)


def test_optimizer_unresolved_outcome_is_not_wrapped_as_ready(tmp_path) -> None:
    client, _, _ = _client(tmp_path, feasibility=PlanFeasibility.UNRESOLVED)
    with client:
        response = client.post("/api/v1/cart/optimize", json=_payload())

    assert response.status_code == 200
    body = AutomaticPlanningResult.model_validate(response.json())
    assert body.status == "unresolved"
    assert body.optimization_result is not None
    assert body.optimization_result.outcome.value == "unresolved"
    assert body.optimization_result.chosen_plan is None


def test_optimize_api_returns_503_when_checkout_provider_is_unavailable(tmp_path) -> None:
    client, _, _ = _client(
        tmp_path,
        checkout_provider=UnavailableCheckoutObservationProvider(),
    )
    with client:
        response = client.post("/api/v1/cart/optimize", json=_payload())

    assert response.status_code == 503
    assert response.json() == {
        "detail": "required planning evidence or provider is unavailable"
    }
    assert "traceback" not in response.text.lower()


def test_optimize_api_maps_access_denied_to_sanitized_unavailable(tmp_path) -> None:
    client, _, _ = _client(
        tmp_path,
        checkout_capture=AccessDeniedCapture(),
    )
    with client:
        response = client.post("/api/v1/cart/optimize", json=_payload())

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "retailer_access_denied",
            "message": "checkout capture is unavailable",
        }
    }
    assert "secret" not in response.text
    assert "token" not in response.text


def test_optimize_api_rejects_invalid_request_and_publishes_schema(tmp_path) -> None:
    client, _, _ = _client(tmp_path)
    with client:
        invalid = client.post("/api/v1/cart/optimize", json={
            "cart_id": "request-a",
            "items": [{
                "item_id": "item-1",
                "canonical_product_id": "product-1",
                "canonical_variant_id": "variant-1",
                "quantity": 0,
            }],
        })
        openapi = client.get("/api/v1/openapi.json")

    assert invalid.status_code == 422
    assert "canonical cart item quantity must be positive" in invalid.text
    assert openapi.status_code == 200
    operation = openapi.json()["paths"]["/api/v1/cart/optimize"]["post"]
    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response_schema["$ref"].endswith("/AutomaticPlanningResult")
    result_schema = openapi.json()["components"]["schemas"]["AutomaticPlanningResult"]
    assert set(result_schema["properties"]) >= {
        "request_id", "status", "optimization_result", "unresolved_reasons"
    }
    assert result_schema["properties"]["status"]["$ref"].endswith("/AutomaticPlanningStatus")
