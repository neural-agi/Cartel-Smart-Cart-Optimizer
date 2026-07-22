from __future__ import annotations

from collections.abc import Iterable

from app.cost_intelligence.evaluation.types import (
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
    OfferType,
)
from app.cost_intelligence.fee.types import FeeType
from app.cost_intelligence.shared.money import Money


class EffectiveCostAggregation:
    """Collect and combine evaluator outputs using frozen deterministic rules."""

    def collect_immediate_discounts(
        self,
        offer_results: tuple[OfferEvaluationResult, ...],
        membership_results: tuple[MembershipEvaluationResult, ...],
    ) -> tuple[Money, ...]:
        discounts: list[Money] = []
        for offer in offer_results:
            if offer.offer_type is OfferType.UNKNOWN or offer.applicable is None:
                continue
            if offer.offer_type is OfferType.FIXED_DISCOUNT and offer.immediate_discount is not None:
                discounts.append(self._copy_money(offer.immediate_discount))
        for membership in membership_results:
            if membership.eligible is True and membership.benefit_value is not None:
                discounts.append(self._copy_money(membership.benefit_value))
        return tuple(discounts)

    def collect_fee_amounts(
        self,
        fee_results: tuple[FeeEvaluationResult, ...],
    ) -> tuple[Money, ...]:
        fee_amounts: list[Money] = []
        for fee in fee_results:
            if fee.fee_type is FeeType.UNKNOWN or fee.applicable is None:
                continue
            if fee.fee_amount is not None:
                fee_amounts.append(self._copy_money(fee.fee_amount))
        return tuple(fee_amounts)

    def collect_deferred_value(
        self,
        offer_results: tuple[OfferEvaluationResult, ...],
    ) -> Money | None:
        deferred_values: list[Money] = []
        for offer in offer_results:
            if offer.offer_type in (OfferType.CASHBACK, OfferType.WALLET_CREDIT) and offer.deferred_value is not None:
                deferred_values.append(self._copy_money(offer.deferred_value))
        return self._sum_money(deferred_values)

    def calculate_effective_cost(
        self,
        *,
        subtotal: Money | None,
        immediate_discounts: tuple[Money, ...],
        fee_amounts: tuple[Money, ...],
        has_blocking_unknowns: bool,
    ) -> Money | None:
        if subtotal is None:
            return None
        if has_blocking_unknowns:
            return None
        if not self._money_is_compatible((subtotal, *immediate_discounts, *fee_amounts)):
            return None

        minor_units = subtotal.minor_units
        minor_units -= sum(discount.minor_units for discount in immediate_discounts)
        minor_units += sum(fee_amount.minor_units for fee_amount in fee_amounts)
        return Money(currency=subtotal.currency, minor_units=minor_units)

    def _sum_money(self, values: Iterable[Money]) -> Money | None:
        items = [self._copy_money(value) for value in values]
        if not items:
            return None
        if not self._money_is_compatible(items):
            return None
        currency = items[0].currency
        total = sum(item.minor_units for item in items)
        return Money(currency=currency, minor_units=total)

    def _money_is_compatible(self, values: Iterable[Money]) -> bool:
        items = list(values)
        if not items:
            return True
        currency = items[0].currency
        return all(item.currency == currency for item in items)

    def _copy_money(self, value: Money) -> Money:
        return Money(currency=value.currency, minor_units=value.minor_units)
