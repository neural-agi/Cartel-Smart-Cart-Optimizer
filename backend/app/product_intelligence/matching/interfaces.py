from __future__ import annotations

from abc import ABC, abstractmethod

from app.product_intelligence.matching.types import (
    ProductMatchRequest,
    ProductMatchResponse,
    VariantMatchRequest,
    VariantMatchResponse,
)


class ProductMatcher(ABC):
    """Abstract contract for product-level matching."""

    @abstractmethod
    async def match(self, request: ProductMatchRequest) -> ProductMatchResponse:
        """Evaluate whether a listing belongs to a canonical product."""


class VariantMatcher(ABC):
    """Abstract contract for variant-level matching."""

    @abstractmethod
    async def match(self, request: VariantMatchRequest) -> VariantMatchResponse:
        """Evaluate whether a listing belongs to a canonical product variant."""

