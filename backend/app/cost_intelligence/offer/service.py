"""Deterministic interpretation of observed checkout offers."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.evaluation.types import OfferEvaluationResult
from app.cost_intelligence.observation.types import CheckoutOfferObservation
from app.cost_intelligence.offer.types import OfferType
from app.cost_intelligence.shared.money import Money


class OfferEvaluationService:
    """Pure evaluator for the explicitly supported offer text forms."""

    def evaluate(
        self,
        context: CostContext,
        offer: CheckoutOfferObservation,
    ) -> OfferEvaluationResult:
        text = self._offer_text(offer)
        offer_type, amount, percentage = self._interpret(text)
        offer_reference = offer.offer_id
        evaluation_id = self._evaluation_id(
            context, offer_reference
        )

        return OfferEvaluationResult(
            evaluation_id=evaluation_id,
            offer_reference=offer_reference,
            offer_type=offer_type,
            applicable=None if offer_type is OfferType.UNKNOWN else True,
            immediate_discount=(
                amount if offer_type is OfferType.FIXED_DISCOUNT else None
            ),
            percentage_discount=(
                percentage if offer_type is OfferType.PERCENTAGE_DISCOUNT else None
            ),
            deferred_value=(
                amount
                if offer_type in (OfferType.CASHBACK, OfferType.WALLET_CREDIT)
                else None
            ),
            evidence_references=tuple(context.evidence_references),
        )

    def _offer_text(self, offer: CheckoutOfferObservation) -> str:
        return (offer.raw_text or offer.label).strip()

    def _interpret(
        self, text: str
    ) -> tuple[OfferType, Money | None, Decimal | None]:
        if not text:
            return OfferType.UNKNOWN, None, None

        normalized = " ".join(text.upper().split())
        if normalized.endswith("% OFF"):
            percentage = self._parse_percentage(normalized[:-5].strip())
            if percentage is not None:
                return OfferType.PERCENTAGE_DISCOUNT, None, percentage
            return OfferType.UNKNOWN, None, None

        for suffix, offer_type in (
            (" OFF", OfferType.FIXED_DISCOUNT),
            (" CASHBACK", OfferType.CASHBACK),
            (" WALLET CREDIT", OfferType.WALLET_CREDIT),
        ):
            if normalized.endswith(suffix):
                amount = self._parse_rupee_amount(normalized[: -len(suffix)].strip())
                if amount is not None:
                    return offer_type, amount, None
                return OfferType.UNKNOWN, None, None

        return OfferType.UNKNOWN, None, None

    def _parse_percentage(self, value: str) -> Decimal | None:
        if not value or value.endswith("%"):
            return None
        try:
            percentage = Decimal(value)
        except InvalidOperation:
            return None
        if percentage < 0 or percentage > 100:
            return None
        return percentage

    def _parse_rupee_amount(self, value: str) -> Money | None:
        if not value.startswith("₹"):
            return None
        numeric = value[1:].strip().replace(",", "")
        if not numeric:
            return None
        try:
            amount = Decimal(numeric)
        except InvalidOperation:
            return None
        if amount < 0 or amount != amount.quantize(Decimal("0.01")):
            return None
        return Money(currency="INR", minor_units=int(amount * 100))

    def _evaluation_id(
        self,
        context: CostContext,
        offer_reference: str,
    ) -> str:
        payload = json.dumps(
            {
                "context_id": context.context_id,
                "offer_reference": offer_reference,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
