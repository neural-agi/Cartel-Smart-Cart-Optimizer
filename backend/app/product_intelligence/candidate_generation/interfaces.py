from __future__ import annotations

from abc import ABC, abstractmethod

from app.product_intelligence.candidate_generation.types import (
    CandidateGenerationRequest,
    CandidateGenerationResponse,
)


class CandidateGenerator(ABC):
    """Abstract contract for candidate generation."""

    @abstractmethod
    async def generate(
        self,
        request: CandidateGenerationRequest,
    ) -> CandidateGenerationResponse:
        """Return canonical product and variant candidates for a listing."""

