from __future__ import annotations

from dataclasses import dataclass

from app.product_intelligence.candidate_generation.strategies import CandidateSignal


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """A candidate with deterministic ranking evidence."""

    candidate_type: str
    candidate_id: str
    display_name: str
    signal: CandidateSignal
    rationale: tuple[str, ...]

    @property
    def sort_key(self) -> tuple[int, int, int, int, str]:
        return (
            self.signal.total,
            self.signal.brand_overlap,
            self.signal.family_overlap,
            self.signal.category_overlap + self.signal.quantity_overlap,
            self.display_name.lower(),
        )

