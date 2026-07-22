from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.cost_intelligence.context import DeterministicCostContextBuilder
from app.cost_intelligence.evaluation.types import MembershipEvaluationResult
from app.cost_intelligence.membership.orchestrator import MembershipEvaluationOrchestrator
from app.cost_intelligence.membership.service import MembershipEvaluationService
from app.cost_intelligence.membership.types import MembershipType
from app.cost_intelligence.observation.types import (
    CheckoutLineItemObservation,
    CheckoutMembershipObservation,
    CheckoutObservation,
)
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


def _observation(*, membership_labels: tuple[str, ...]) -> CheckoutObservation:
    return CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="demo/raw/blinkit/membership/orchestrator-demo.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        capture_context_reference="demo/location/new-delhi",
        evidence_references=(
            EvidenceReference(
                source_type="source_artifact",
                source_id="demo/raw/blinkit/membership/orchestrator-demo.html",
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
        memberships=tuple(
            CheckoutMembershipObservation(label=label, raw_text=label)
            for label in membership_labels
        ),
    )


def _context(observation: CheckoutObservation):
    return DeterministicCostContextBuilder().build(observation)


def test_empty_checkout_returns_empty_tuple() -> None:
    context = _context(_observation(membership_labels=()))

    result = MembershipEvaluationOrchestrator().evaluate(context)

    assert result == ()
    assert isinstance(result, tuple)


def test_single_membership() -> None:
    observation = _observation(membership_labels=("Prime membership applied",))
    context = _context(observation)

    result = MembershipEvaluationOrchestrator().evaluate(context)

    assert len(result) == 1
    assert result[0].membership_reference == observation.memberships[0].membership_id
    assert result[0].eligible is True


def test_multiple_memberships_preserve_order() -> None:
    observation = _observation(
        membership_labels=(
            "Prime membership applied",
            "Prime members save ₹40",
            "Not a member",
        )
    )
    context = _context(observation)

    result = MembershipEvaluationOrchestrator().evaluate(context)

    assert [item.membership_reference for item in result] == [
        membership.membership_id for membership in observation.memberships
    ]


def test_deterministic_replay() -> None:
    observation = _observation(
        membership_labels=(
            "Prime membership applied",
            "Prime members save ₹40",
        )
    )
    context = _context(observation)
    orchestrator = MembershipEvaluationOrchestrator()

    first = orchestrator.evaluate(context)
    second = orchestrator.evaluate(context.model_copy(deep=True))

    assert first == second


def test_returned_object_is_immutable_tuple() -> None:
    observation = _observation(membership_labels=("Prime membership applied",))
    context = _context(observation)

    result = MembershipEvaluationOrchestrator().evaluate(context)

    with pytest.raises(TypeError):
        result[0] = result[0]  # type: ignore[index]


def test_evaluator_invoked_exactly_once_per_membership(monkeypatch) -> None:
    observation = _observation(
        membership_labels=(
            "Prime membership applied",
            "Prime members save ₹40",
            "Not a member",
        )
    )
    context = _context(observation)
    calls: list[str] = []

    def fake_evaluate(self, current_context, membership):
        calls.append(membership.membership_id)
        return MembershipEvaluationResult(
            evaluation_id=f"evaluation-{membership.membership_id}",
            membership_reference=membership.membership_id,
            eligible=None,
            benefit_value=None,
            evidence_references=tuple(current_context.evidence_references),
        )

    monkeypatch.setattr(
        MembershipEvaluationService,
        "evaluate",
        fake_evaluate,
        raising=True,
    )

    result = MembershipEvaluationOrchestrator().evaluate(context)

    assert calls == [membership.membership_id for membership in observation.memberships]
    assert len(result) == len(observation.memberships)


def test_evaluator_exceptions_propagate_unchanged(monkeypatch) -> None:
    observation = _observation(membership_labels=("Prime membership applied",))
    context = _context(observation)

    def fake_evaluate(self, current_context, membership):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        MembershipEvaluationService,
        "evaluate",
        fake_evaluate,
        raising=True,
    )

    with pytest.raises(RuntimeError, match="boom"):
        MembershipEvaluationOrchestrator().evaluate(context)
