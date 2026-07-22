from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.cost_intelligence.context import DeterministicCostContextBuilder
from app.cost_intelligence.effective_cost.orchestrator import (
    EffectiveCostEvaluationOrchestrator,
)
from app.cost_intelligence.effective_cost.service import EffectiveCostEvaluationService
from app.cost_intelligence.evaluation.types import (
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
    OfferType,
)
from app.cost_intelligence.fee.types import FeeType
from app.cost_intelligence.observation.types import (
    CheckoutLineItemObservation,
    CheckoutObservation,
    CheckoutTotalObservation,
)
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


def _context() -> CheckoutObservation:
    return CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="demo/raw/blinkit/effective-cost/orchestrator-demo.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        capture_context_reference="demo/location/new-delhi",
        evidence_references=(
            EvidenceReference(
                source_type="source_artifact",
                source_id="demo/raw/blinkit/effective-cost/orchestrator-demo.html",
            ),
        ),
        line_items=(
            CheckoutLineItemObservation(
                label="Amul Taaza Milk",
                quantity_text="500 ml",
                displayed_price=Money(currency="INR", minor_units=3100),
            ),
        ),
        totals=(
            CheckoutTotalObservation(
                label="Subtotal",
                amount=Money(currency="INR", minor_units=1000),
            ),
        ),
    )


def _inputs(context: DeterministicCostContextBuilder):
    shared = tuple(context.evidence_references)
    return (
        (
            OfferEvaluationResult(
                evaluation_id="offer-1",
                offer_reference="offer-1",
                offer_type=OfferType.FIXED_DISCOUNT,
                applicable=True,
                immediate_discount=Money(currency="INR", minor_units=100),
                evidence_references=shared,
            ),
        ),
        (
            FeeEvaluationResult(
                evaluation_id="fee-1",
                fee_reference="fee-1",
                fee_type=FeeType.DELIVERY,
                applicable=True,
                fee_amount=Money(currency="INR", minor_units=20),
                evidence_references=shared,
            ),
        ),
        (
            MembershipEvaluationResult(
                evaluation_id="membership-1",
                membership_reference="membership-1",
                eligible=True,
                benefit_value=Money(currency="INR", minor_units=10),
                evidence_references=shared,
            ),
        ),
    )


def test_delegates_exactly_once(monkeypatch) -> None:
    context = DeterministicCostContextBuilder().build(_context())
    offer_results, fee_results, membership_results = _inputs(context)
    calls: list[tuple[str, tuple[str, ...]]] = []
    sentinel = object()

    def fake_evaluate(self, current_context, offers, fees, memberships):
        calls.append((current_context.context_id, tuple(result.evaluation_id for result in offers)))
        return sentinel

    monkeypatch.setattr(
        EffectiveCostEvaluationService,
        "evaluate",
        fake_evaluate,
        raising=True,
    )

    orchestrator = EffectiveCostEvaluationOrchestrator()
    result = orchestrator.evaluate(context, offer_results, fee_results, membership_results)

    assert len(calls) == 1
    assert result is sentinel


def test_deterministic_replay() -> None:
    context = DeterministicCostContextBuilder().build(_context())
    offer_results, fee_results, membership_results = _inputs(context)
    orchestrator = EffectiveCostEvaluationOrchestrator()

    first = orchestrator.evaluate(context, offer_results, fee_results, membership_results)
    second = orchestrator.evaluate(
        context.model_copy(deep=True),
        tuple(result.model_copy(deep=True) for result in offer_results),
        tuple(result.model_copy(deep=True) for result in fee_results),
        tuple(result.model_copy(deep=True) for result in membership_results),
    )

    assert first == second


def test_immutable_output() -> None:
    context = DeterministicCostContextBuilder().build(_context())
    offer_results, fee_results, membership_results = _inputs(context)
    result = EffectiveCostEvaluationOrchestrator().evaluate(
        context,
        offer_results,
        fee_results,
        membership_results,
    )

    with pytest.raises((TypeError, ValidationError)):
        result.immediate_discounts = ()  # type: ignore[misc]


def test_exception_propagation(monkeypatch) -> None:
    context = DeterministicCostContextBuilder().build(_context())
    offer_results, fee_results, membership_results = _inputs(context)

    def fake_evaluate(self, current_context, offers, fees, memberships):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        EffectiveCostEvaluationService,
        "evaluate",
        fake_evaluate,
        raising=True,
    )

    with pytest.raises(RuntimeError, match="boom"):
        EffectiveCostEvaluationOrchestrator().evaluate(
            context,
            offer_results,
            fee_results,
            membership_results,
        )
