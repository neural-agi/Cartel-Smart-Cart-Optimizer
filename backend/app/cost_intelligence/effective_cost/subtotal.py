from __future__ import annotations

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.shared.money import Money


class SubtotalExtractor:
    """Deterministically derive the checkout subtotal from structured observation data."""

    def extract(self, context: CostContext) -> Money | None:
        candidates: list[tuple[int, Money]] = []
        for total in context.checkout_observation.totals:
            if total.amount is None or not total.label:
                continue
                
            label_lower = total.label.lower().strip()
            
            if "grand total" in label_lower or label_lower == "total":
                continue
            if label_lower == "subtotal":
                candidates.append((0, total.amount))
            elif "subtotal" in label_lower:
                candidates.append((1, total.amount))
            elif label_lower == "item total":
                candidates.append((0, total.amount))
            elif "item total" in label_lower or "mrp total" in label_lower:
                candidates.append((1, total.amount))
                
        if not candidates:
            return None

        best_priority = min(priority for priority, _ in candidates)
        valid_subtotals = [amount for priority, amount in candidates if priority == best_priority]
        first = valid_subtotals[0]
        for other in valid_subtotals[1:]:
            if other.minor_units != first.minor_units or other.currency != first.currency:
                return None
                
        return Money(
            currency=first.currency,
            minor_units=first.minor_units,
        )
