from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.cost_intelligence.observation import (
    CheckoutFeeObservation,
    CheckoutLineItemObservation,
    CheckoutObservation,
    CheckoutObservationRegistrationRequest,
    CheckoutOfferObservation,
    CheckoutTotalObservation,
    DeterministicCheckoutObservationRegistry,
)
from app.cost_intelligence.shared import Money
from app.product_intelligence.models import EvidenceReference


def _run(coro):
    return asyncio.run(coro)


def _evidence_reference(
    *,
    source_type: str,
    source_id: str,
    capture_timestamp: datetime | None = None,
    note: str | None = None,
) -> EvidenceReference:
    return EvidenceReference(
        source_type=source_type,
        source_id=source_id,
        capture_timestamp=capture_timestamp,
        note=note,
    )


def _money(minor_units: int, currency: str = "inr") -> Money:
    return Money(currency=currency, minor_units=minor_units)


def _observation(
    *,
    line_items: tuple[CheckoutLineItemObservation, ...],
    evidence_references: tuple[EvidenceReference, ...],
    fees: tuple[CheckoutFeeObservation, ...] = (),
    offers: tuple[CheckoutOfferObservation, ...] = (),
    totals: tuple[CheckoutTotalObservation, ...] = (),
) -> CheckoutObservation:
    return CheckoutObservation(
        platform=" Blinkit ",
        source_artifact_reference=" checkout/rendered.html ",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version=" parser-v1 ",
        capture_context_reference=" context-1 ",
        evidence_references=evidence_references,
        line_items=line_items,
        fees=fees,
        offers=offers,
        totals=totals,
    )


def _registry_request(observation: CheckoutObservation) -> CheckoutObservationRegistrationRequest:
    return CheckoutObservationRegistrationRequest(observation=observation)


def test_register_canonicalizes_and_deduplicates_observation(tmp_path) -> None:
    registry = DeterministicCheckoutObservationRegistry()
    observation_a = _observation(
        line_items=(
            CheckoutLineItemObservation(
                label="   Amul Taaza Milk   ",
                quantity_text=" 500 ml ",
                displayed_price=_money(3100, "inr"),
                reference_price=_money(3500, "inr"),
                raw_text=" line item text ",
            ),
            CheckoutLineItemObservation(
                label="Britannia Bread",
                quantity_text="400 g",
                displayed_price=_money(4000, "inr"),
                raw_text=" bread text ",
            ),
        ),
        evidence_references=(
            _evidence_reference(
                source_type=" source_artifact ",
                source_id=" artifact-1 ",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                note="zeta",
            ),
            _evidence_reference(
                source_type="source_artifact",
                source_id="artifact-1",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                note="alpha",
            ),
            _evidence_reference(
                source_type=" evidence_record ",
                source_id=" evidence-1 ",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                note=" filesystem ",
            ),
        ),
        fees=(
            CheckoutFeeObservation(
                label="Delivery fee",
                amount=_money(2900, "inr"),
                raw_text=" delivery fee ",
            ),
        ),
        offers=(
            CheckoutOfferObservation(
                label="10% off",
                amount=_money(1000, "inr"),
                raw_text=" 10% off ",
            ),
        ),
        totals=(
            CheckoutTotalObservation(
                label="Cart total",
                amount=_money(7500, "inr"),
                raw_text=" cart total ",
            ),
        ),
    )
    observation_b = observation_a.model_copy(
        update={
            "line_items": tuple(reversed(observation_a.line_items)),
            "evidence_references": tuple(reversed(observation_a.evidence_references)),
        },
        deep=True,
    )

    first = _run(registry.register(_registry_request(observation_a)))
    second = _run(registry.register(_registry_request(observation_b)))

    assert first.observation_id == second.observation_id
    assert first.observation.model_dump(mode="json") == second.observation.model_dump(
        mode="json"
    )
    assert first.observation.platform == "blinkit"
    assert first.observation.source_artifact_reference == "checkout/rendered.html"
    assert first.observation.parser_version == "parser-v1"
    assert first.observation.capture_context_reference == "context-1"
    assert [item.label for item in first.observation.line_items] == [
        "Amul Taaza Milk",
        "Britannia Bread",
    ]
    assert [ref.source_id for ref in first.observation.evidence_references] == [
        "evidence-1",
        "artifact-1",
    ]
    assert len(registry.list_checkout_observations()) == 1


def test_repeated_registration_is_deterministic_no_op(tmp_path) -> None:
    registry = DeterministicCheckoutObservationRegistry()
    observation = _observation(
        line_items=(
            CheckoutLineItemObservation(
                label="Amul Taaza Milk",
                quantity_text="500 ml",
                displayed_price=_money(3100, "inr"),
                raw_text="line item text",
            ),
        ),
        evidence_references=(
            _evidence_reference(
                source_type="source_artifact",
                source_id="artifact-1",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                note="demo",
            ),
        ),
    )

    first = _run(registry.register(_registry_request(observation)))
    second = _run(registry.register(_registry_request(observation.model_copy(deep=True))))

    assert first.observation_id == second.observation_id
    assert first.observation.model_dump(mode="json") == second.observation.model_dump(
        mode="json"
    )
    assert len(registry.list_checkout_observations()) == 1


def test_list_checkout_observations_is_deterministic(tmp_path) -> None:
    registry = DeterministicCheckoutObservationRegistry()
    observation_a = _observation(
        line_items=(
            CheckoutLineItemObservation(
                label="Amul Taaza Milk",
                quantity_text="500 ml",
                displayed_price=_money(3100, "inr"),
            ),
        ),
        evidence_references=(
            _evidence_reference(
                source_type="source_artifact",
                source_id="artifact-a",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            ),
        ),
    )
    observation_b = _observation(
        line_items=(
            CheckoutLineItemObservation(
                label="Britannia Bread",
                quantity_text="400 g",
                displayed_price=_money(4000, "inr"),
            ),
        ),
        evidence_references=(
            _evidence_reference(
                source_type="source_artifact",
                source_id="artifact-b",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            ),
        ),
    )

    first = _run(registry.register(_registry_request(observation_b)))
    second = _run(registry.register(_registry_request(observation_a)))

    listed = registry.list_checkout_observations()
    expected_ids = sorted([first.observation_id, second.observation_id])
    expected = [
        registry.get_checkout_observation(observation_id).model_dump(mode="json")
        for observation_id in expected_ids
    ]
    assert len(listed) == 2
    assert [obs.model_dump(mode="json") for obs in listed] == expected


@pytest.mark.parametrize(
    "observation_builder,expected_message",
    [
        (
            lambda: CheckoutObservation(
                platform="blinkit",
                source_artifact_reference="checkout/rendered.html",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                parser_version="parser-v1",
                evidence_references=(
                    _evidence_reference(
                        source_type="source_artifact",
                        source_id="artifact-1",
                        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                    ),
                ),
                line_items=(),
            ),
            "requires at least one child observation",
        ),
        (
            lambda: CheckoutObservation(
                platform="blinkit",
                source_artifact_reference="checkout/rendered.html",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                parser_version="parser-v1",
                evidence_references=(),
                line_items=(
                    CheckoutLineItemObservation(
                        label="Amul Taaza Milk",
                        quantity_text="500 ml",
                        displayed_price=_money(3100, "inr"),
                    ),
                ),
            ),
            "requires at least one evidence reference",
        ),
        (
            lambda: CheckoutObservation(
                platform="blinkit",
                source_artifact_reference="checkout/rendered.html",
                capture_timestamp=datetime(2026, 1, 1, 12, 0),
                parser_version="parser-v1",
                evidence_references=(
                    _evidence_reference(
                        source_type="source_artifact",
                        source_id="artifact-1",
                    ),
                ),
                line_items=(
                    CheckoutLineItemObservation(
                        label="Amul Taaza Milk",
                        quantity_text="500 ml",
                        displayed_price=_money(3100, "inr"),
                    ),
                ),
            ),
            "timestamps must be timezone-aware",
        ),
        (
            lambda: CheckoutObservation(
                platform="blinkit",
                source_artifact_reference="   ",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                parser_version="parser-v1",
                evidence_references=(
                    _evidence_reference(
                        source_type="source_artifact",
                        source_id="artifact-1",
                    ),
                ),
                line_items=(
                    CheckoutLineItemObservation(
                        label="Amul Taaza Milk",
                        quantity_text="500 ml",
                        displayed_price=_money(3100, "inr"),
                    ),
                ),
            ),
            "source_artifact_reference must not be blank",
        ),
    ],
)
def test_register_fail_closed_validation(
    observation_builder,
    expected_message: str,
) -> None:
    registry = DeterministicCheckoutObservationRegistry()

    with pytest.raises(ValueError, match=expected_message):
        _run(registry.register(_registry_request(observation_builder())))
