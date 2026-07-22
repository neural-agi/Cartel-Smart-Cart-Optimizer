from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.evaluation.types import MembershipEvaluationResult
from app.cost_intelligence.membership.types import MembershipType
from app.cost_intelligence.observation.types import CheckoutMembershipObservation
from app.cost_intelligence.shared.money import Money


class MembershipEvaluationService:
    """Pure deterministic evaluator for observed checkout membership facts."""

    _NEGATIVE_TERMS = (
        "not eligible",
        "not a member",
        "membership inactive",
        "membership expired",
        "membership unavailable",
        "no membership",
        "not entitled",
    )
    _BENEFIT_TERMS = (
        "save",
        "benefit",
        "member price",
        "member-only",
        "members only",
    )
    _ENTITLEMENT_TERMS = (
        "membership active",
        "membership applied",
        "subscription active",
        "eligible",
        "prime member",
        "plus member",
        "member entitlement",
    )

    def evaluate(
        self,
        context: CostContext,
        membership: CheckoutMembershipObservation,
    ) -> MembershipEvaluationResult:
        membership_reference = membership.membership_id
        text = self._membership_text(membership)
        normalized_text = self._normalize_text(text)
        membership_type = self._classify_membership(normalized_text)
        eligible = self._interpret_eligibility(text, normalized_text, membership_type)
        benefit_value = self._interpret_benefit_value(text, normalized_text)
        evaluation_id = self._evaluation_id(context, membership_reference)

        return MembershipEvaluationResult(
            evaluation_id=evaluation_id,
            membership_reference=membership_reference,
            eligible=eligible,
            benefit_value=benefit_value,
            evidence_references=tuple(context.evidence_references),
        )

    def _classify_membership(self, normalized_text: str) -> MembershipType:
        if not normalized_text:
            return MembershipType.UNKNOWN

        if self._contains_any(normalized_text, *self._BENEFIT_TERMS):
            return MembershipType.BENEFIT
        if self._contains_any(normalized_text, *self._ENTITLEMENT_TERMS):
            return MembershipType.ENTITLEMENT
        return MembershipType.UNKNOWN

    def _interpret_eligibility(
        self,
        text: str,
        normalized_text: str,
        membership_type: MembershipType,
    ) -> bool | None:
        if not text:
            return None

        if self._contains_any(normalized_text, *self._NEGATIVE_TERMS):
            return False

        if self._contains_any(normalized_text, *self._BENEFIT_TERMS):
            return True
        if membership_type is MembershipType.ENTITLEMENT:
            return True
        return None

    def _interpret_benefit_value(
        self,
        text: str,
        normalized_text: str,
    ) -> Money | None:
        if not text or not self._contains_any(normalized_text, *self._BENEFIT_TERMS):
            return None

        return self._parse_rupee_amount(text)

    def _membership_text(self, membership: CheckoutMembershipObservation) -> str:
        return (membership.raw_text or membership.label).strip()

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.casefold().split())

    def _contains_any(self, text: str, *needles: str) -> bool:
        return any(needle in text for needle in needles)

    def _parse_rupee_amount(self, text: str) -> Money | None:
        match = re.search(r"₹\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text)
        if match is None:
            return None
        numeric = match.group(1).replace(",", "")
        try:
            amount = Decimal(numeric)
        except InvalidOperation:
            return None
        if amount < 0 or amount != amount.quantize(Decimal("0.01")):
            return None
        return Money(currency="INR", minor_units=int(amount * 100))

    def _evaluation_id(self, context: CostContext, membership_reference: str) -> str:
        payload = json.dumps(
            {
                "context_id": context.context_id,
                "membership_reference": membership_reference,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
