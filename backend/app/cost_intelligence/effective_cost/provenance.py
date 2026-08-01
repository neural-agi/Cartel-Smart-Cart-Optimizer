from __future__ import annotations

from app.cost_intelligence.evaluation.types import (
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
)
from app.product_intelligence.models import EvidenceReference
from app.cost_intelligence.shared.evidence import evidence_identity


class EvidenceMerger:
    """Merge evidence references by exact structural identity while preserving order."""

    def merge(
        self,
        context_references: tuple[EvidenceReference, ...],
        offer_results: tuple[OfferEvaluationResult, ...],
        fee_results: tuple[FeeEvaluationResult, ...],
        membership_results: tuple[MembershipEvaluationResult, ...],
    ) -> tuple[EvidenceReference, ...]:
        merged: dict[tuple[str, str], EvidenceReference] = {}
        for evidence_reference in context_references:
            self._record(merged, evidence_reference)
        for result in offer_results:
            for evidence_reference in result.evidence_references:
                self._record(merged, evidence_reference)
        for result in fee_results:
            for evidence_reference in result.evidence_references:
                self._record(merged, evidence_reference)
        for result in membership_results:
            for evidence_reference in result.evidence_references:
                self._record(merged, evidence_reference)
        return tuple(merged[key] for key in merged)

    def _record(
        self,
        merged: dict[str, EvidenceReference],
        evidence_reference: EvidenceReference,
    ) -> None:
        key = evidence_identity(evidence_reference)
        if key not in merged:
            merged[key] = evidence_reference
