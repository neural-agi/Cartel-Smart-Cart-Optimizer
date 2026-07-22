from __future__ import annotations

from app.cost_intelligence.evaluation.types import (
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
    OfferType,
)
from app.cost_intelligence.fee.types import FeeType
from app.cost_intelligence.shared.money import Money


class UnknownPropagationPolicy:
    """Make one deterministic pass to collect unknowns and blocking state."""

    def evaluate(
        self,
        subtotal: Money | None,
        offer_results: tuple[OfferEvaluationResult, ...],
        fee_results: tuple[FeeEvaluationResult, ...],
        membership_results: tuple[MembershipEvaluationResult, ...],
    ) -> tuple[tuple[str, ...], bool]:
        unknown_components: list[str] = []
        if subtotal is None:
            unknown_components.append("subtotal")

        has_blocking_unknowns = subtotal is None

        for offer in offer_results:
            offer_unknowns, offer_blocking = self._offer_state(offer)
            unknown_components.extend(offer_unknowns)
            has_blocking_unknowns = has_blocking_unknowns or offer_blocking

        for fee in fee_results:
            fee_unknowns, fee_blocking = self._fee_state(fee)
            unknown_components.extend(fee_unknowns)
            has_blocking_unknowns = has_blocking_unknowns or fee_blocking

        for membership in membership_results:
            membership_unknowns, membership_blocking = self._membership_state(membership)
            unknown_components.extend(membership_unknowns)
            has_blocking_unknowns = has_blocking_unknowns or membership_blocking

        return tuple(unknown_components), has_blocking_unknowns

    def _offer_state(self, offer: OfferEvaluationResult) -> tuple[list[str], bool]:
        reference = f"offer:{offer.offer_reference}"
        if offer.offer_type is OfferType.UNKNOWN:
            return [f"{reference}:unresolved"], True
        if offer.offer_type is OfferType.FIXED_DISCOUNT and (
            offer.applicable is None or offer.immediate_discount is None
        ):
            return [f"{reference}:immediate_discount"], True
        if offer.offer_type in (OfferType.CASHBACK, OfferType.WALLET_CREDIT):
            if offer.deferred_value is None:
                return [f"{reference}:deferred_value"], False
            return [], False
        if offer.applicable is None:
            return [f"{reference}:unresolved"], True
        return [], False

    def _fee_state(self, fee: FeeEvaluationResult) -> tuple[list[str], bool]:
        reference = f"fee:{fee.fee_reference}"
        if fee.fee_type is FeeType.UNKNOWN or fee.applicable is None:
            return [f"{reference}:unresolved"], True
        if fee.fee_amount is None:
            return [f"{reference}:fee_amount"], True
        return [], False

    def _membership_state(self, membership: MembershipEvaluationResult) -> tuple[list[str], bool]:
        reference = f"membership:{membership.membership_reference}"
        if membership.eligible is None:
            return [f"{reference}:unresolved"], True
        if membership.eligible is True and membership.benefit_value is None:
            return [f"{reference}:benefit_value"], True
        return [], False
