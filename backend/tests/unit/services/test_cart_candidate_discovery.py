import pytest

from app.cost_intelligence.shared.money import Money
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryService,
    PersistedCandidateReadiness,
)


@pytest.mark.parametrize("availability", [None, "unknown", "out_of_stock", "ADD"])
def test_allocation_requires_explicit_available_observation(availability):
    service = CartCandidateDiscoveryService(
        catalog=None,
        association_registry=None,
        observation_registry=None,
    )
    observation = type("Observation", (), {
        "observed_selling_price": Money(currency="INR", minor_units=100),
        "availability_signal": availability,
    })()

    readiness, reason = service._readiness(observation)

    assert readiness is PersistedCandidateReadiness.not_ready_for_allocation
    assert reason == "observation does not explicitly establish current availability"


@pytest.mark.parametrize("availability", ["available", "in_stock"])
def test_explicit_available_observation_with_typed_price_is_allocatable(availability):
    service = CartCandidateDiscoveryService(
        catalog=None,
        association_registry=None,
        observation_registry=None,
    )
    observation = type("Observation", (), {
        "observed_selling_price": Money(currency="INR", minor_units=100),
        "availability_signal": availability,
    })()

    readiness, reason = service._readiness(observation)

    assert readiness is PersistedCandidateReadiness.ready_for_allocation
    assert reason is None
