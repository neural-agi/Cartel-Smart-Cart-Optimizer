from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.cost_intelligence.context import DeterministicCostContextBuilder
from app.cost_intelligence.fee import FeeEvaluationService, FeeType
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
        source_artifact_reference="demo/raw/blinkit/fees/demo.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        capture_context_reference="demo/location/new-delhi",
        evidence_references=(
            EvidenceReference(
                source_type="source_artifact",
                source_id="demo/raw/blinkit/fees/demo.html",
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


@pytest.mark.parametrize(
    ("label", "expected_fee_type"),
    [
        ("Delivery Fee", FeeType.DELIVERY),
        ("Platform Fee", FeeType.PLATFORM),
        ("Handling Fee", FeeType.HANDLING),
        ("Packaging Fee", FeeType.PACKAGING),
        ("Small Cart Fee", FeeType.SMALL_CART),
        ("Surge Fee", FeeType.SURGE),
    ],
)
def test_supported_fee_categories(label: str, expected_fee_type: FeeType) -> None:
    observation = _observation(fee_labels=(label,))
    context = _context(observation)
    fee = observation.fees[0]

    result = FeeEvaluationService().evaluate(context, fee)

    assert result.fee_reference == fee.fee_id
    assert result.fee_type == expected_fee_type
    assert result.applicable is True
    assert result.fee_amount == fee.amount
    assert result.evidence_references == tuple(context.evidence_references)


def test_unknown_fee_is_fail_closed() -> None:
    observation = _observation(fee_labels=("Mystery Charge",))
    context = _context(observation)
    fee = observation.fees[0]

    result = FeeEvaluationService().evaluate(context, fee)

    assert result.fee_type == FeeType.UNKNOWN
    assert result.applicable is None
    assert result.fee_amount is None


def test_deterministic_replay_and_stable_identity() -> None:
    observation = _observation(fee_labels=("Delivery Fee",))
    context = _context(observation)
    fee = observation.fees[0]
    service = FeeEvaluationService()

    first = service.evaluate(context, fee)
    second = service.evaluate(context.model_copy(deep=True), fee.model_copy(deep=True))

    assert first.evaluation_id == second.evaluation_id
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.evaluation_id == service._evaluation_id(context, fee.fee_id)


def test_immutable_result() -> None:
    observation = _observation(fee_labels=("Platform Fee",))
    context = _context(observation)
    result = FeeEvaluationService().evaluate(context, observation.fees[0])

    with pytest.raises(ValidationError):
        result.fee_type = "changed"


def test_identical_inputs_produce_identical_outputs() -> None:
    observation = _observation(fee_labels=("Packaging Fee",))
    context = _context(observation)
    service = FeeEvaluationService()

    first = service.evaluate(context, observation.fees[0])
    second = service.evaluate(context.model_copy(deep=True), observation.fees[0].model_copy(deep=True))

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_evidence_preservation() -> None:
    observation = _observation(fee_labels=("Small Cart Fee",))
    context = _context(observation)
    result = FeeEvaluationService().evaluate(context, observation.fees[0])

    assert result.evidence_references == tuple(context.evidence_references)


def test_fail_closed_on_blank_inputs() -> None:
    fee = CheckoutFeeObservation(label="   ", amount=None, raw_text="   ")
    observation = CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="demo/raw/blinkit/fees/demo.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        evidence_references=(
            EvidenceReference(source_type="source_artifact", source_id="demo/raw/blinkit/fees/demo.html"),
        ),
        line_items=(
            CheckoutLineItemObservation(
                label="Amul Taaza Milk",
                quantity_text="500 ml",
                displayed_price=Money(currency="INR", minor_units=3100),
            ),
        ),
        fees=(fee,),
    )
    context = _context(observation)

    result = FeeEvaluationService().evaluate(context, fee)

    assert result.fee_type == FeeType.UNKNOWN
    assert result.applicable is None
    assert result.fee_amount is None
