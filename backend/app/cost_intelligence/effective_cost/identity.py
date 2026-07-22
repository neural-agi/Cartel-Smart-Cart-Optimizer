from __future__ import annotations

import hashlib
import json

from app.cost_intelligence.evaluation.types import (
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
)


class EffectiveCostIdentityGenerator:
    """Deterministically derive effective-cost evaluation identity."""

    def evaluation_id(
        self,
        context_id: str,
        offer_results: tuple[OfferEvaluationResult, ...],
        fee_results: tuple[FeeEvaluationResult, ...],
        membership_results: tuple[MembershipEvaluationResult, ...],
    ) -> str:
        payload = json.dumps(
            {
                "context_id": context_id,
                "offer_evaluation_ids": tuple(
                    result.evaluation_id for result in offer_results
                ),
                "fee_evaluation_ids": tuple(result.evaluation_id for result in fee_results),
                "membership_evaluation_ids": tuple(
                    result.evaluation_id for result in membership_results
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
