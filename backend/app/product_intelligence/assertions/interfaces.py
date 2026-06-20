from __future__ import annotations

from abc import ABC, abstractmethod

from app.product_intelligence.assertions.types import (
    AssertionUpdateRequest,
    AssertionUpdateResponse,
)


class AssertionManager(ABC):
    """Abstract contract for applying canonical assertions."""

    @abstractmethod
    async def apply(
        self,
        request: AssertionUpdateRequest,
    ) -> AssertionUpdateResponse:
        """Apply an approved product-intelligence assertion update."""

