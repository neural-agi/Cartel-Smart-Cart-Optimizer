from __future__ import annotations

import json

from app.cost_intelligence.evaluation.types import (
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
)
from app.product_intelligence.models import EvidenceReference


class EvidenceMerger:
    """Merge evidence references by exact structural identity while preserving order."""

    def merge(
        self,
        context_references: tuple[EvidenceReference, ...],
        offer_results: tuple[OfferEvaluationResult, ...],
        fee_results: tuple[FeeEvaluationResult, ...],
        membership_results: tuple[MembershipEvaluationResult, ...],
    ) -> tuple[EvidenceReference, ...]:
        merged: dict[str, EvidenceReference] = {}
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
        payload = json.dumps(
            evidence_reference.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        if payload not in merged:
            merged[payload] = evidence_reference
