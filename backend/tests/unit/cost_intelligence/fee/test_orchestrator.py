from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.cost_intelligence.context import DeterministicCostContextBuilder
from app.cost_intelligence.evaluation.types import FeeEvaluationResult
from app.cost_intelligence.fee.orchestrator import FeeEvaluationOrchestrator
from app.cost_intelligence.fee.service import FeeEvaluationService
from app.cost_intelligence.fee.types import FeeType
from app.cost_intelligence.observation.types import (
    CheckoutFeeObservation,
    CheckoutLineItemObservation,
    CheckoutObservation,
)
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


def _observation(*, fee_labels: tuple[str, ...]) -> CheckoutObservation:
    return CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="demo/raw/blinkit/fees/demo-orchestrator.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        capture_context_reference="demo/location/new-delhi",
        evidence_references=(
            EvidenceReference(
                source_type="source_artifact",
                source_id="demo/raw/blinkit/fees/demo-orchestrator.html",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            ),
        ),
        line_items=(
            CheckoutLineItemObservation(
                label="Amul Taaza Milk",
                quantity_text="500 ml",
                displayed_price=Money(currency="INR", minor_units=3100),
            ),
        ),
        fees=tuple(
            CheckoutFeeObservation(
                label=label,
                amount=Money(currency="INR", minor_units=1000 + index * 100),
                raw_text=label,
            )
            for index, label in enumerate(fee_labels)
        ),
    )


def _context(observation: CheckoutObservation):
    return DeterministicCostContextBuilder().build(observation)


def test_empty_checkout_returns_empty_tuple() -> None:
    context = _context(_observation(fee_labels=()))

    result = FeeEvaluationOrchestrator().evaluate(context)

    assert result == ()
    assert isinstance(result, tuple)


def test_single_fee() -> None:
    observation = _observation(fee_labels=("Delivery Fee",))
    context = _context(observation)

    result = FeeEvaluationOrchestrator().evaluate(context)

    assert len(result) == 1
    assert result[0].fee_reference == observation.fees[0].fee_id
    assert result[0].fee_type == FeeType.DELIVERY


def test_multiple_fees_preserve_observation_order() -> None:
    observation = _observation(
        fee_labels=("Delivery Fee", "Platform Fee", "Packaging Fee", "Small Cart Fee")
    )
    context = _context(observation)

    result = FeeEvaluationOrchestrator().evaluate(context)

    assert [item.fee_reference for item in result] == [
        fee.fee_id for fee in observation.fees
    ]


def test_deterministic_replay() -> None:
    observation = _observation(
        fee_labels=("Delivery Fee", "Platform Fee", "Packaging Fee")
    )
    context = _context(observation)
    orchestrator = FeeEvaluationOrchestrator()

    first = orchestrator.evaluate(context)
    second = orchestrator.evaluate(context.model_copy(deep=True))

    assert first == second


def test_returned_object_is_immutable_tuple() -> None:
    observation = _observation(fee_labels=("Delivery Fee",))
    context = _context(observation)

    result = FeeEvaluationOrchestrator().evaluate(context)

    with pytest.raises(TypeError):
        result[0] = result[0]  # type: ignore[index]


def test_evaluator_invoked_exactly_once_per_fee(monkeypatch) -> None:
    observation = _observation(
        fee_labels=("Delivery Fee", "Platform Fee", "Packaging Fee")
    )
    context = _context(observation)
    calls: list[str] = []

    def fake_evaluate(self, current_context, fee):
        calls.append(fee.fee_id)
        return FeeEvaluationResult(
            evaluation_id=f"evaluation-{fee.fee_id}",
            fee_reference=fee.fee_id,
            fee_type=FeeType.UNKNOWN,
            applicable=None,
            fee_amount=None,
            evidence_references=tuple(current_context.evidence_references),
        )

    monkeypatch.setattr(FeeEvaluationService, "evaluate", fake_evaluate, raising=True)

    result = FeeEvaluationOrchestrator().evaluate(context)

    assert calls == [fee.fee_id for fee in observation.fees]
    assert len(result) == len(observation.fees)


def test_evaluator_exceptions_propagate_unchanged(monkeypatch) -> None:
    observation = _observation(fee_labels=("Delivery Fee",))
    context = _context(observation)

    def fake_evaluate(self, current_context, fee):
        raise RuntimeError("boom")

    monkeypatch.setattr(FeeEvaluationService, "evaluate", fake_evaluate, raising=True)

    with pytest.raises(RuntimeError, match="boom"):
        FeeEvaluationOrchestrator().evaluate(context)
