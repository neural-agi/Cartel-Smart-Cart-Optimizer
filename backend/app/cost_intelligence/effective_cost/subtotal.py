from __future__ import annotations

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.shared.money import Money


class SubtotalExtractor:
    """Deterministically derive the checkout subtotal from structured observation data."""

    def extract(self, context: CostContext) -> Money | None:
        for total in context.checkout_observation.totals:
            if total.amount is not None:
                return Money(
                    currency=total.amount.currency,
                    minor_units=total.amount.minor_units,
                )
        return None
