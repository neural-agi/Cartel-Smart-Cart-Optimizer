from __future__ import annotations

from app.cart_optimization.service import CartOptimizationService
from app.cart_optimization.types import CartOptimizationRequest, CartOptimizationResult


class CartOptimizationOrchestrator:
    """Thin deterministic coordinator for the Cart Optimization service."""

    def __init__(self, service: CartOptimizationService | None = None) -> None:
        self._service = service or CartOptimizationService()

    def optimize(self, request: CartOptimizationRequest) -> CartOptimizationResult:
        return self._service.optimize(request)
