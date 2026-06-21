from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.product_intelligence.matching.types import (
    CoverageValidationState,
    FreshnessState,
    MatchOutcome,
    UpstreamFailureState,
    VariantGovernanceContext,
    VariantMatchRequest,
    VariantValidationResult,
)
from app.product_intelligence.models import IdentityStatus


class VariantRequestValidator(ABC):
    """Validate variant matching requests against frozen governance boundaries."""

    @abstractmethod
    async def validate(
        self,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
    ) -> VariantValidationResult:
        """Validate a request before candidate evaluation."""


class DeterministicVariantRequestValidator(VariantRequestValidator):
    """Conservative request validator for the first executable slice."""

    async def validate(
        self,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
    ) -> VariantValidationResult:
        rationale: list[str] = []

        if request.product is None:
            rationale.append("product_context=missing")
            return VariantValidationResult(
                blocking_outcome=MatchOutcome.unresolved,
                rationale=rationale,
                governance=governance,
                request_summary=self._request_summary(request),
                validated_at_utc=datetime.now(timezone.utc),
            )

        if request.product.product_identity_status == IdentityStatus.ambiguous:
            rationale.append("product_context=ambiguous")
            return VariantValidationResult(
                blocking_outcome=MatchOutcome.unresolved,
                rationale=rationale,
                governance=governance,
                request_summary=self._request_summary(request),
                validated_at_utc=datetime.now(timezone.utc),
            )

        if not request.variant_candidates:
            rationale.append("variant_candidates=missing")
            return VariantValidationResult(
                blocking_outcome=MatchOutcome.unresolved,
                rationale=rationale,
                governance=governance,
                request_summary=self._request_summary(request),
                validated_at_utc=datetime.now(timezone.utc),
            )

        if governance.freshness.freshness_state == FreshnessState.stale_conflicting:
            rationale.append("freshness_state=stale-conflicting")
            return VariantValidationResult(
                blocking_outcome=MatchOutcome.conflicting,
                rationale=rationale,
                governance=governance,
                request_summary=self._request_summary(request),
                validated_at_utc=datetime.now(timezone.utc),
            )

        if self._has_conflicting_upstream_failure(governance):
            rationale.append("upstream_failure=contradictory")
            return VariantValidationResult(
                blocking_outcome=MatchOutcome.conflicting,
                rationale=rationale,
                governance=governance,
                request_summary=self._request_summary(request),
                validated_at_utc=datetime.now(timezone.utc),
            )

        if governance.coverage_validation.validation_state in {
            CoverageValidationState.invalid,
            CoverageValidationState.contradictory,
        }:
            rationale.append(
                f"coverage_validation={governance.coverage_validation.validation_state.value}"
            )

        if governance.freshness.freshness_state in {
            FreshnessState.missing,
            FreshnessState.invalid,
            FreshnessState.stale_unresolved,
        }:
            rationale.append(
                f"freshness_state={governance.freshness.freshness_state.value}"
            )

        if governance.coverage_validation.declared_state.value in {"unknown", "partial"}:
            rationale.append(
                f"coverage_state={governance.coverage_validation.declared_state.value}"
            )

        return VariantValidationResult(
            blocking_outcome=None,
            rationale=rationale,
            governance=governance,
            request_summary=self._request_summary(request),
            validated_at_utc=datetime.now(timezone.utc),
        )

    def _request_summary(self, request: VariantMatchRequest) -> list[str]:
        summary = [
            f"platform={request.platform_listing.platform}",
            f"platform_listing_id={request.platform_listing.platform_listing_id}",
            f"raw_title={request.platform_listing.raw_title}",
        ]
        if request.platform_listing.raw_quantity_text:
            summary.append(
                f"raw_quantity_text={request.platform_listing.raw_quantity_text}"
            )
        if request.platform_listing.raw_category_text:
            summary.append(
                f"raw_category_text={request.platform_listing.raw_category_text}"
            )
        if request.product is not None:
            summary.append(f"product_id={request.product.canonical_product_id}")
            summary.append(
                f"product_identity_status={request.product.product_identity_status.value}"
            )
        summary.append(f"variant_candidate_count={len(request.variant_candidates)}")
        return summary

    def _has_conflicting_upstream_failure(
        self,
        governance: VariantGovernanceContext,
    ) -> bool:
        for failure in governance.upstream_failures:
            if failure.failure_state != UpstreamFailureState.contradictory:
                continue
            if failure.dependency_name in {"product_context", "pack_identity"}:
                return True
        return False
