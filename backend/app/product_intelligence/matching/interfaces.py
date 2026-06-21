from __future__ import annotations

from abc import ABC, abstractmethod

from app.product_intelligence.matching.types import (
    CandidateEvaluationResult,
    VariantGovernanceContext,
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


class VariantGovernanceHooks(ABC):
    """Internal hook for collecting governed inputs for variant matching."""

    @abstractmethod
    async def collect(self, request: VariantMatchRequest) -> VariantGovernanceContext:
        """Collect governed inputs used by the orchestration slice."""


class VariantCandidateEvaluator(ABC):
    """Internal boundary for deterministic candidate evaluation."""

    @abstractmethod
    async def evaluate(
        self,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
    ) -> CandidateEvaluationResult:
        """Evaluate the governed candidate pool without performing matching policy."""
