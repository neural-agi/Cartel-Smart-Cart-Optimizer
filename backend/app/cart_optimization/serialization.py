"""Deterministic serialization boundaries for cart planning contracts.

This module deliberately does not persist records or assign lifecycle semantics.
It only provides validated, canonical JSON round-trips for existing immutable
planning models so future storage adapters cannot silently drop fields.
"""

from __future__ import annotations

from app.cart_optimization.planning import CartPlanningRequest
from app.cart_optimization.types import CartOptimizationResult


class CartPlanningSerialization:
    """Pure serialization helpers for existing planning contracts."""

    @staticmethod
    def request_json(request: CartPlanningRequest) -> str:
        return request.model_dump_json(round_trip=True)

    @staticmethod
    def request_from_json(payload: str) -> CartPlanningRequest:
        return CartPlanningRequest.model_validate_json(payload)

    @staticmethod
    def result_json(result: CartOptimizationResult) -> str:
        return result.model_dump_json(round_trip=True)

    @staticmethod
    def result_from_json(payload: str) -> CartOptimizationResult:
        return CartOptimizationResult.model_validate_json(payload)
