from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.cost_intelligence.context import DeterministicCostContextBuilder
from app.cost_intelligence.observation.types import (
    CheckoutObservation,
    CheckoutOfferObservation,
)
from app.cost_intelligence.offer import OfferEvaluationService, OfferType
from app.product_intelligence.models import EvidenceReference


def _context(text: str):
    observation = CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="raw/checkout.json",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="checkout-v1",
        evidence_references=(EvidenceReference(source_type="artifact", source_id="a1"),),
        offers=(CheckoutOfferObservation(label=text),),
    )
    return DeterministicCostContextBuilder().build(observation), observation.offers[0]


@pytest.mark.parametrize(
    ("text", "offer_type", "minor_units", "deferred"),
    [
        ("₹100 OFF", OfferType.FIXED_DISCOUNT, 10000, False),
        ("10% OFF", OfferType.PERCENTAGE_DISCOUNT, None, False),
        ("₹150 Cashback", OfferType.CASHBACK, 15000, True),
        ("₹75 Wallet Credit", OfferType.WALLET_CREDIT, 7500, True),
    ],
)
def test_supported_offer_types(text, offer_type, minor_units, deferred) -> None:
    context, offer = _context(text)
    result = OfferEvaluationService().evaluate(context, offer)

    assert result.offer_type is offer_type
    if offer_type is OfferType.PERCENTAGE_DISCOUNT:
        assert result.percentage_discount == 10
    value = result.deferred_value if deferred else result.immediate_discount
    assert value is None if minor_units is None else value.minor_units == minor_units


def test_unknown_offer_fails_closed_without_value() -> None:
    context, offer = _context("Buy one get one free")
    result = OfferEvaluationService().evaluate(context, offer)

    assert result.offer_type is OfferType.UNKNOWN
    assert result.applicable is None
    assert result.immediate_discount is None
    assert result.deferred_value is None


def test_replay_is_deterministic_and_preserves_evidence() -> None:
    context, offer = _context("₹100 OFF")
    service = OfferEvaluationService()

    first = service.evaluate(context, offer)
    second = service.evaluate(context, offer)

    assert first == second
    assert first.evaluation_id == second.evaluation_id
    assert first.evidence_references == context.evidence_references


def test_result_is_immutable() -> None:
    context, offer = _context("10% OFF")
    result = OfferEvaluationService().evaluate(context, offer)

    with pytest.raises((TypeError, ValueError)):
        result.offer_type = OfferType.UNKNOWN  # type: ignore[misc]


def test_multi_offer_checkout_is_evaluated_offer_by_offer() -> None:
    observation = CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="raw/checkout/multi.json",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="checkout-v1",
        evidence_references=(EvidenceReference(source_type="artifact", source_id="multi"),),
        offers=(
            CheckoutOfferObservation(label="₹100 OFF"),
            CheckoutOfferObservation(label="10% OFF"),
            CheckoutOfferObservation(label="₹150 Cashback"),
        ),
    )
    context = DeterministicCostContextBuilder().build(observation)
    service = OfferEvaluationService()

    forward = [service.evaluate(context, offer) for offer in observation.offers]
    reverse = [service.evaluate(context, offer) for offer in reversed(observation.offers)]

    assert len(forward) == 3
    assert [result.offer_reference for result in forward] == [
        offer.offer_id for offer in observation.offers
    ]
    assert {result.evaluation_id for result in forward} == {
        result.evaluation_id for result in reverse
    }
    assert forward == list(reversed(reverse))
    assert [service.evaluate(context, offer) for offer in observation.offers] == forward
