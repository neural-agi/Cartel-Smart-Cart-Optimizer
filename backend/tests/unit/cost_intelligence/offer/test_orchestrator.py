from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.cost_intelligence.context import DeterministicCostContextBuilder
from app.cost_intelligence.observation.types import (
    CheckoutObservation,
    CheckoutOfferObservation,
)
from app.cost_intelligence.offer import OfferEvaluationOrchestrator, OfferType
from app.product_intelligence.models import EvidenceReference


def _context(labels: tuple[str, ...]):
    observation = CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="raw/checkout/orchestrator.json",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="checkout-v1",
        evidence_references=(EvidenceReference(source_type="artifact", source_id="orchestrator"),),
        offers=tuple(CheckoutOfferObservation(label=label) for label in labels),
    )
    return DeterministicCostContextBuilder().build(observation)


def test_empty_checkout_returns_empty_tuple() -> None:
    assert OfferEvaluationOrchestrator().evaluate(_context(())) == ()


def test_one_offer_is_evaluated() -> None:
    results = OfferEvaluationOrchestrator().evaluate(_context(("₹100 OFF",)))

    assert len(results) == 1
    assert results[0].offer_type is OfferType.FIXED_DISCOUNT


def test_multiple_offers_preserve_observation_order() -> None:
    results = OfferEvaluationOrchestrator().evaluate(
        _context(("₹100 OFF", "10% OFF", "₹150 Cashback"))
    )

    assert [result.offer_type for result in results] == [
        OfferType.FIXED_DISCOUNT,
        OfferType.PERCENTAGE_DISCOUNT,
        OfferType.CASHBACK,
    ]


def test_replay_is_deterministic() -> None:
    context = _context(("₹100 OFF", "10% OFF", "₹150 Cashback"))
    orchestrator = OfferEvaluationOrchestrator()

    assert orchestrator.evaluate(context) == orchestrator.evaluate(context)


def test_result_is_an_immutable_tuple() -> None:
    results = OfferEvaluationOrchestrator().evaluate(_context(("₹100 OFF",)))

    assert isinstance(results, tuple)
    with pytest.raises(TypeError):
        results[0] = results[0]  # type: ignore[index]


def test_evaluator_is_invoked_once_per_offer() -> None:
    context = _context(("₹100 OFF", "10% OFF", "₹150 Cashback"))
    orchestrator = OfferEvaluationOrchestrator()
    calls = []
    original = orchestrator.service.evaluate

    def evaluate(context_arg, offer):
        calls.append(offer.offer_id)
        return original(context_arg, offer)

    orchestrator.service.evaluate = evaluate  # type: ignore[method-assign]
    orchestrator.evaluate(context)

    assert calls == [offer.offer_id for offer in context.checkout_observation.offers]


def test_evaluator_exception_propagates_unchanged() -> None:
    context = _context(("₹100 OFF",))
    orchestrator = OfferEvaluationOrchestrator()
    error = ValueError("evaluation failed")

    def evaluate(_context, _offer):
        raise error

    orchestrator.service.evaluate = evaluate  # type: ignore[method-assign]
    with pytest.raises(ValueError) as raised:
        orchestrator.evaluate(context)

    assert raised.value is error
