"""Strict parsing of natural Blinkit cart mutation responses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.cost_intelligence.observation.cart_capture import (
    RetailerCartIdentity,
    RetailerCartLine,
    RetailerCartSnapshot,
)


class BlinkitCartResponseError(ValueError):
    """Raised when a natural cart response lacks authoritative identity."""


class BlinkitCartResponseParser:
    """Convert an explicit retailer cart payload into the existing snapshot."""

    def parse(
        self,
        payload: Mapping[str, Any],
        *,
        request_id: str,
        plan_id: str,
        retailer_id: str,
        source_reference: str,
    ) -> RetailerCartSnapshot:
        cart_id = payload.get("cart_id")
        if not isinstance(cart_id, str) or not cart_id.strip():
            raise BlinkitCartResponseError("Blinkit cart response has no authoritative cart ID")
        raw_lines = payload.get("lines") or payload.get("items")
        if not isinstance(raw_lines, list):
            raise BlinkitCartResponseError("Blinkit cart response has no structured cart lines")
        lines: list[RetailerCartLine] = []
        for raw_line in raw_lines:
            if not isinstance(raw_line, Mapping):
                raise BlinkitCartResponseError("Blinkit cart line is malformed")
            product_id = raw_line.get("product_id") or raw_line.get("retailer_product_id")
            # ``line_id`` and array position are not sufficient evidence of a
            # retailer cart-line identity. Only an explicitly named retailer
            # field is accepted here.
            line_id = raw_line.get("retailer_cart_line_id")
            quantity = raw_line.get("quantity")
            if not isinstance(product_id, str) or not product_id.strip():
                raise BlinkitCartResponseError("Blinkit cart line has no retailer product ID")
            if not isinstance(line_id, str) or not line_id.strip():
                raise BlinkitCartResponseError("Blinkit cart line has no authoritative line ID")
            if not isinstance(quantity, int) or quantity < 1:
                raise BlinkitCartResponseError("Blinkit cart line has invalid quantity")
            lines.append(RetailerCartLine(
                retailer_product_id=product_id.strip(),
                quantity=quantity,
                retailer_cart_line_id=line_id.strip(),
                retailer_id=retailer_id,
                request_id=request_id,
                plan_id=plan_id,
                source_reference=source_reference,
            ))
        return RetailerCartSnapshot(
            identity=RetailerCartIdentity(
                retailer_id=retailer_id,
                request_id=request_id,
                plan_id=plan_id,
                retailer_cart_id=cart_id.strip(),
                identity_available=True,
            ),
            lines=tuple(lines),
        )
