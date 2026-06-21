"""Candidate generation contracts and deterministic service layer."""

from app.product_intelligence.candidate_generation.interfaces import CandidateGenerator
from app.product_intelligence.candidate_generation.service import (
    CandidateCatalogSnapshot,
    DeterministicCandidateGenerationService,
)
from app.product_intelligence.candidate_generation.types import (
    CandidateGenerationRequest,
    CandidateGenerationResponse,
)

__all__ = [
    "CandidateCatalogSnapshot",
    "CandidateGenerationRequest",
    "CandidateGenerationResponse",
    "CandidateGenerator",
    "DeterministicCandidateGenerationService",
]
