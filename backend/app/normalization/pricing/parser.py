from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.cost_intelligence.shared.money import Money


class GovernedRetailPriceParser:
    """Parse only explicitly governed INR selling-price text."""

    _pattern = re.compile(r"^(?:₹|INR\s*)?([0-9]+(?:\.[0-9]+)?)$")

    def __init__(self, *, currency_precision: dict[str, int] | None = None) -> None:
        self.currency_precision = {
            currency.strip().upper(): precision
            for currency, precision in (currency_precision or {"INR": 2}).items()
        }
        if any(not currency or precision < 0 for currency, precision in self.currency_precision.items()):
            raise ValueError("currency precision configuration is invalid")

    def parse(self, text: str | None, *, currency_code: str | None) -> Money | None:
        if text is None or currency_code is None:
            return None
        currency = currency_code.strip().upper()
        precision = self.currency_precision.get(currency)
        if precision is None:
            return None
        match = self._pattern.fullmatch(text.strip())
        if match is None:
            return None
        try:
            amount = Decimal(match.group(1))
        except InvalidOperation:
            return None
        minor_units = amount * (10 ** precision)
        if minor_units != minor_units.to_integral_value():
            return None
        return Money(currency=currency, minor_units=int(minor_units))
