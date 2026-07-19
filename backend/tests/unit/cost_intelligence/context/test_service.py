from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.cost_intelligence.context import (
    CostContext,
    DeterministicCostContextBuilder,
)
from app.cost_intelligence.observation.types import (
    CheckoutObservation,
    CheckoutOfferObservation,
)
from app.product_intelligence.models import EvidenceReference


def _observation() -> CheckoutObservation:
    return CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="raw/blinkit/checkout.json",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="checkout-v1",
        evidence_references=(
            EvidenceReference(source_type="artifact", source_id="checkout-1"),
        ),
        offers=(CheckoutOfferObservation(label="10% off"),),
    )


def test_identical_observations_produce_identical_contexts() -> None:
    builder = DeterministicCostContextBuilder()

    first = builder.build(_observation())
    second = builder.build(_observation())

    assert first == second
    assert first.context_id == second.context_id


def test_context_preserves_observation_and_evidence() -> None:
    observation = _observation()
    context = DeterministicCostContextBuilder().build(observation)

    assert context.checkout_observation == observation
    assert context.evidence_references == observation.evidence_references


def test_context_is_immutable() -> None:
    context = DeterministicCostContextBuilder().build(_observation())

    with pytest.raises((TypeError, ValueError)):
        context.context_id = "changed"  # type: ignore[misc]


def test_missing_evidence_fails_closed() -> None:
    observation = _observation().model_copy(update={"evidence_references": ()})

    with pytest.raises(ValueError, match="evidence-backed"):
        DeterministicCostContextBuilder().build(observation)
