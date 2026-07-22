from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.cost_intelligence.context import DeterministicCostContextBuilder
from app.cost_intelligence.membership.service import MembershipEvaluationService
from app.cost_intelligence.membership.types import MembershipType
from app.cost_intelligence.observation.types import (
    CheckoutLineItemObservation,
    CheckoutMembershipObservation,
    CheckoutObservation,
)
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


def _observation(text: str) -> CheckoutObservation:
    return CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="demo/raw/blinkit/membership/demo.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        capture_context_reference="demo/location/new-delhi",
        evidence_references=(
            EvidenceReference(
                source_type="source_artifact",
                source_id="demo/raw/blinkit/membership/demo.html",
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
        memberships=(
            CheckoutMembershipObservation(label=text, raw_text=text),
        ),
    )


def _context(observation: CheckoutObservation):
    return DeterministicCostContextBuilder().build(observation)


@pytest.mark.parametrize(
    ("text", "eligible", "benefit_minor_units", "membership_type"),
    [
        ("Prime membership applied", True, None, MembershipType.ENTITLEMENT),
        ("Not a member", False, None, MembershipType.UNKNOWN),
        ("Prime members save ₹40", True, 4000, MembershipType.BENEFIT),
        ("Membership benefit ₹25", True, 2500, MembershipType.BENEFIT),
    ],
)
def test_supported_membership_cases(
    text: str,
    eligible: bool,
    benefit_minor_units: int | None,
    membership_type: MembershipType,
) -> None:
    observation = _observation(text)
    context = _context(observation)
    membership = observation.memberships[0]

    result = MembershipEvaluationService().evaluate(context, membership)

    assert result.membership_reference == membership.membership_id
    assert result.evaluation_id
    assert result.eligible is eligible
    assert result.evidence_references == tuple(context.evidence_references)
    if benefit_minor_units is None:
        assert result.benefit_value is None
    else:
        assert result.benefit_value is not None
        assert result.benefit_value.minor_units == benefit_minor_units


def test_unknown_membership_fails_closed() -> None:
    observation = _observation("Prime Plus")
    context = _context(observation)
    membership = observation.memberships[0]

    result = MembershipEvaluationService().evaluate(context, membership)

    assert result.eligible is None
    assert result.benefit_value is None


def test_deterministic_replay_and_stable_identity() -> None:
    observation = _observation("Prime members save ₹40")
    context = _context(observation)
    membership = observation.memberships[0]
    service = MembershipEvaluationService()

    first = service.evaluate(context, membership)
    second = service.evaluate(context.model_copy(deep=True), membership.model_copy(deep=True))

    assert first == second
    assert first.evaluation_id == second.evaluation_id
    assert first.evaluation_id == service._evaluation_id(context, membership.membership_id)


def test_result_is_immutable() -> None:
    observation = _observation("Prime membership applied")
    context = _context(observation)
    result = MembershipEvaluationService().evaluate(context, observation.memberships[0])

    with pytest.raises((TypeError, ValueError, ValidationError)):
        result.eligible = None  # type: ignore[misc]


def test_evidence_preservation() -> None:
    observation = _observation("Membership benefit ₹25")
    context = _context(observation)
    result = MembershipEvaluationService().evaluate(context, observation.memberships[0])

    assert result.evidence_references == tuple(context.evidence_references)


def test_no_inferred_savings() -> None:
    observation = _observation("Prime membership applied")
    context = _context(observation)
    result = MembershipEvaluationService().evaluate(context, observation.memberships[0])

    assert result.benefit_value is None
