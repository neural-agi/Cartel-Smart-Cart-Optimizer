from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.cost_intelligence.context import DeterministicCostContextBuilder
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


def _observation(*, total_minor_units: int | None = 1000) -> CheckoutObservation:
    totals = ()
    if total_minor_units is not None:
        totals = (
            CheckoutTotalObservation(
                label="Subtotal",
                amount=Money(currency="INR", minor_units=total_minor_units),
            ),
        )
    return CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="demo/raw/blinkit/effective-cost/demo.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        capture_context_reference="demo/location/new-delhi",
        evidence_references=(
            EvidenceReference(
                source_type="source_artifact",
                source_id="demo/raw/blinkit/effective-cost/demo.html",
                capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                note="checkout",
            ),
        ),
        line_items=(
            CheckoutLineItemObservation(
                label="Amul Taaza Milk",
                quantity_text="500 ml",
                displayed_price=Money(currency="INR", minor_units=3100),
            ),
        ),
        totals=totals,
    )


def _build_inputs():
    shared = EvidenceReference(
        source_type="source_artifact",
        source_id="shared/evidence.json",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        note="shared",
    )
    offer_extra = EvidenceReference(
        source_type="source_artifact",
        source_id="offer/evidence.json",
        capture_timestamp=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
        note="offer",
    )
    fee_extra = EvidenceReference(
        source_type="source_artifact",
        source_id="fee/evidence.json",
        capture_timestamp=datetime(2026, 1, 1, 12, 2, tzinfo=timezone.utc),
        note="fee",
    )
    membership_extra = EvidenceReference(
        source_type="source_artifact",
        source_id="membership/evidence.json",
        capture_timestamp=datetime(2026, 1, 1, 12, 3, tzinfo=timezone.utc),
        note="membership",
    )
    context = DeterministicCostContextBuilder().build(_observation())
    offers = (
        OfferEvaluationResult(
            evaluation_id="offer-1",
            offer_reference="offer-ref-1",
            offer_type=OfferType.FIXED_DISCOUNT,
            applicable=True,
            immediate_discount=Money(currency="INR", minor_units=100),
            evidence_references=(shared, offer_extra),
        ),
        OfferEvaluationResult(
            evaluation_id="offer-2",
            offer_reference="offer-ref-2",
            offer_type=OfferType.CASHBACK,
            applicable=True,
            deferred_value=Money(currency="INR", minor_units=50),
            evidence_references=(shared,),
        ),
    )
    fees = (
        FeeEvaluationResult(
            evaluation_id="fee-1",
            fee_reference="fee-ref-1",
            fee_type=FeeType.DELIVERY,
            applicable=True,
            fee_amount=Money(currency="INR", minor_units=20),
            evidence_references=(shared, fee_extra),
        ),
        FeeEvaluationResult(
            evaluation_id="fee-2",
            fee_reference="fee-ref-2",
            fee_type=FeeType.PLATFORM,
            applicable=True,
            fee_amount=Money(currency="INR", minor_units=5),
            evidence_references=(shared,),
        ),
    )
    memberships = (
        MembershipEvaluationResult(
            evaluation_id="membership-1",
            membership_reference="membership-ref-1",
            eligible=True,
            benefit_value=Money(currency="INR", minor_units=10),
            evidence_references=(shared, membership_extra),
        ),
    )
    return context, offers, fees, memberships, shared, offer_extra, fee_extra, membership_extra


def _unknown_inputs():
    context = DeterministicCostContextBuilder().build(_observation())
    unknown_offer = OfferEvaluationResult(
        evaluation_id="offer-unknown",
        offer_reference="offer-unknown",
        offer_type=OfferType.UNKNOWN,
        applicable=None,
        evidence_references=tuple(context.evidence_references),
    )
    unknown_fee = FeeEvaluationResult(
        evaluation_id="fee-unknown",
        fee_reference="fee-unknown",
        fee_type=FeeType.UNKNOWN,
        applicable=None,
        fee_amount=None,
        evidence_references=tuple(context.evidence_references),
    )
    unknown_membership = MembershipEvaluationResult(
        evaluation_id="membership-unknown",
        membership_reference="membership-unknown",
        eligible=None,
        benefit_value=None,
        evidence_references=tuple(context.evidence_references),
    )
    return context, unknown_offer, unknown_fee, unknown_membership


def test_known_aggregation() -> None:
    context, offers, fees, memberships, *_ = _build_inputs()

    result = EffectiveCostEvaluationService().evaluate(context, offers, fees, memberships)

    assert result.subtotal is not None
    assert result.subtotal.minor_units == 1000
    assert [money.minor_units for money in result.immediate_discounts] == [100, 10]
    assert [money.minor_units for money in result.fees] == [20, 5]
    assert result.deferred_value is not None
    assert result.deferred_value.minor_units == 50
    assert result.effective_cost is not None
    assert result.effective_cost.minor_units == 915
    assert result.unknown_components == ()


def test_deferred_value_remains_separate() -> None:
    context, offers, fees, memberships, *_ = _build_inputs()

    result = EffectiveCostEvaluationService().evaluate(context, offers, fees, memberships)

    assert result.deferred_value is not None
    assert result.effective_cost is not None
    assert result.effective_cost.minor_units == 915
    assert result.deferred_value.minor_units == 50


def test_zero_vs_unknown() -> None:
    observation = _observation(total_minor_units=1000)
    context = DeterministicCostContextBuilder().build(observation)
    zero_offer = OfferEvaluationResult(
        evaluation_id="offer-zero",
        offer_reference="offer-zero",
        offer_type=OfferType.FIXED_DISCOUNT,
        applicable=True,
        immediate_discount=Money(currency="INR", minor_units=0),
        evidence_references=tuple(context.evidence_references),
    )
    zero_fee = FeeEvaluationResult(
        evaluation_id="fee-zero",
        fee_reference="fee-zero",
        fee_type=FeeType.DELIVERY,
        applicable=True,
        fee_amount=Money(currency="INR", minor_units=0),
        evidence_references=tuple(context.evidence_references),
    )
    zero_membership = MembershipEvaluationResult(
        evaluation_id="membership-zero",
        membership_reference="membership-zero",
        eligible=True,
        benefit_value=Money(currency="INR", minor_units=0),
        evidence_references=tuple(context.evidence_references),
    )

    result = EffectiveCostEvaluationService().evaluate(
        context,
        (zero_offer,),
        (zero_fee,),
        (zero_membership,),
    )

    assert result.effective_cost is not None
    assert result.effective_cost.minor_units == 1000
    assert result.unknown_components == ()


def test_unknown_propagation() -> None:
    context, unknown_offer, unknown_fee, unknown_membership = _unknown_inputs()
    result = EffectiveCostEvaluationService().evaluate(
        context,
        (unknown_offer,),
        (unknown_fee,),
        (unknown_membership,),
    )

    assert result.effective_cost is None
    assert result.unknown_components == (
        "offer:offer-unknown:unresolved",
        "fee:fee-unknown:unresolved",
        "membership:membership-unknown:unresolved",
    )


def test_unknown_deferred_value_does_not_block_effective_cost() -> None:
    context = DeterministicCostContextBuilder().build(_observation(total_minor_units=1000))
    deferred_unknown = OfferEvaluationResult(
        evaluation_id="offer-deferred-unknown",
        offer_reference="offer-deferred-unknown",
        offer_type=OfferType.CASHBACK,
        applicable=True,
        deferred_value=None,
        evidence_references=tuple(context.evidence_references),
    )

    result = EffectiveCostEvaluationService().evaluate(context, (deferred_unknown,), (), ())

    assert result.effective_cost is not None
    assert result.effective_cost.minor_units == 1000
    assert result.deferred_value is None
    assert result.unknown_components == ("offer:offer-deferred-unknown:deferred_value",)


def test_deterministic_replay() -> None:
    context, offers, fees, memberships, *_ = _build_inputs()
    service = EffectiveCostEvaluationService()

    first = service.evaluate(context, offers, fees, memberships)
    second = service.evaluate(
        context.model_copy(deep=True),
        tuple(result.model_copy(deep=True) for result in offers),
        tuple(result.model_copy(deep=True) for result in fees),
        tuple(result.model_copy(deep=True) for result in memberships),
    )

    assert first == second


def test_stable_evaluation_identity() -> None:
    context, offers, fees, memberships, *_ = _build_inputs()
    service = EffectiveCostEvaluationService()

    first = service.evaluate(context, offers, fees, memberships)
    second = service.evaluate(context.model_copy(deep=True), offers, fees, memberships)

    assert first.evaluation_id == second.evaluation_id
    assert first.evaluation_id == service._evaluation_id(
        context.context_id,
        offers,
        fees,
        memberships,
    )


def test_canonical_ordering() -> None:
    context, offers, fees, memberships, *_ = _build_inputs()
    result = EffectiveCostEvaluationService().evaluate(context, offers, fees, memberships)

    assert [money.minor_units for money in result.immediate_discounts] == [100, 10]
    assert [money.minor_units for money in result.fees] == [20, 5]


def test_evidence_preservation() -> None:
    context, offers, fees, memberships, shared, offer_extra, fee_extra, membership_extra = _build_inputs()

    result = EffectiveCostEvaluationService().evaluate(context, offers, fees, memberships)

    assert result.evidence_references == (
        context.evidence_references[0],
        shared,
        offer_extra,
        fee_extra,
        membership_extra,
    )


def test_result_is_immutable() -> None:
    context, offers, fees, memberships, *_ = _build_inputs()
    result = EffectiveCostEvaluationService().evaluate(context, offers, fees, memberships)

    with pytest.raises((TypeError, ValueError, ValidationError)):
        result.effective_cost = None  # type: ignore[misc]
