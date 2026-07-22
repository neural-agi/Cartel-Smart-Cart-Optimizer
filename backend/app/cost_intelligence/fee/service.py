from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.evaluation.types import FeeEvaluationResult
from app.cost_intelligence.fee.types import FeeType
from app.cost_intelligence.observation.types import CheckoutFeeObservation
from app.cost_intelligence.shared.money import Money


class FeeEvaluationService:
    """Pure deterministic evaluator for observed checkout fee lines."""

    def evaluate(
        self,
        context: CostContext,
        fee: CheckoutFeeObservation,
    ) -> FeeEvaluationResult:
        fee_reference = fee.fee_id
        fee_type = self._interpret_type(fee)
        fee_amount = self._interpret_amount(fee)
        evaluation_id = self._evaluation_id(context, fee_reference)

        return FeeEvaluationResult(
            evaluation_id=evaluation_id,
            fee_reference=fee_reference,
            fee_type=fee_type,
            applicable=None if fee_type is FeeType.UNKNOWN else True,
            fee_amount=fee_amount if fee_type is not FeeType.UNKNOWN else None,
            evidence_references=tuple(context.evidence_references),
        )

    def _interpret_type(self, fee: CheckoutFeeObservation) -> FeeType:
        text = self._fee_text(fee)
        if not text:
            return FeeType.UNKNOWN

        normalized = self._normalize_text(text)
        if self._contains_any(normalized, "delivery"):
            return FeeType.DELIVERY
        if self._contains_any(normalized, "platform"):
            return FeeType.PLATFORM
        if self._contains_any(normalized, "handling"):
            return FeeType.HANDLING
        if self._contains_any(normalized, "packaging"):
            return FeeType.PACKAGING
        if self._contains_any(normalized, "small cart", "small-cart", "smallcart"):
            return FeeType.SMALL_CART
        if self._contains_any(normalized, "surge"):
            return FeeType.SURGE
        return FeeType.UNKNOWN

    def _interpret_amount(self, fee: CheckoutFeeObservation) -> Money | None:
        if fee.amount is not None:
            return Money(currency=fee.amount.currency, minor_units=fee.amount.minor_units)

        text = self._fee_text(fee)
        if not text:
            return None

        normalized = self._normalize_text(text)
        amount = self._parse_rupee_amount(normalized)
        if amount is not None:
            return amount
        return None

    def _fee_text(self, fee: CheckoutFeeObservation) -> str:
        return (fee.raw_text or fee.label).strip()

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

    def _evaluation_id(self, context: CostContext, fee_reference: str) -> str:
        payload = json.dumps(
            {
                "context_id": context.context_id,
                "fee_reference": fee_reference,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
