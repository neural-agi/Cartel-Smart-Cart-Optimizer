from __future__ import annotations

from app.core.logging import get_logger
from app.product_intelligence.matching.interfaces import (
    VariantCandidateEvaluator,
    VariantGovernanceHooks,
    VariantMatcher,
)
from app.product_intelligence.matching.types import (
    CandidateEvaluationResult,
    CoverageState,
    CoverageValidationState,
    FreshnessState,
    MatchOutcome,
    VariantGovernanceContext,
    VariantMatchRequest,
    VariantMatchResponse,
    VariantValidationResult,
)
from app.product_intelligence.matching.variant_audit import (
    DeterministicVariantAuditRecorder,
    VariantDecisionAuditRecord,
    VariantDecisionTrace,
)
from app.product_intelligence.matching.variant_candidate_evaluation import (
    DeterministicVariantCandidateEvaluator,
)
from app.product_intelligence.matching.variant_governance import (
    DeterministicVariantGovernanceHooks,
)
from app.product_intelligence.matching.variant_rationale import (
    DeterministicVariantRationaleBuilder,
)
from app.product_intelligence.matching.variant_validation import (
    DeterministicVariantRequestValidator,
)
from app.product_intelligence.models import ProductVariant


logger = get_logger(__name__)


class DeterministicVariantMatcher(VariantMatcher):
    """First executable orchestration slice for variant matching."""

    def __init__(
        self,
        *,
        governance_hooks: VariantGovernanceHooks | None = None,
        candidate_evaluator: VariantCandidateEvaluator | None = None,
        validator: DeterministicVariantRequestValidator | None = None,
        rationale_builder: DeterministicVariantRationaleBuilder | None = None,
        audit_recorder: DeterministicVariantAuditRecorder | None = None,
        matcher_version: str = "variant-matcher-slice-1",
    ) -> None:
        self.governance_hooks = governance_hooks or DeterministicVariantGovernanceHooks()
        self.candidate_evaluator = (
            candidate_evaluator or DeterministicVariantCandidateEvaluator()
        )
        self.validator = validator or DeterministicVariantRequestValidator()
        self.rationale_builder = rationale_builder or DeterministicVariantRationaleBuilder()
        self.audit_recorder = audit_recorder or DeterministicVariantAuditRecorder()
        self.matcher_version = matcher_version
        self.last_trace: VariantDecisionTrace | None = None
        self.last_audit_record: VariantDecisionAuditRecord | None = None

    async def match(self, request: VariantMatchRequest) -> VariantMatchResponse:
        governance = await self.governance_hooks.collect(request)
        validation = await self.validator.validate(request=request, governance=governance)

        if validation.blocking_outcome is not None:
            outcome = validation.blocking_outcome
            candidate_result = self._empty_candidate_result(request)
            return self._finalize(
                request=request,
                validation=validation,
                candidate_result=candidate_result,
                outcome=outcome,
                selected_variant_id=None,
            )

        candidate_result = await self.candidate_evaluator.evaluate(
            request=request,
            governance=validation.governance,
        )
        outcome, selected_variant_id = self._classify(
            validation=validation,
            candidate_result=candidate_result,
        )
        return self._finalize(
            request=request,
            validation=validation,
            candidate_result=candidate_result,
            outcome=outcome,
            selected_variant_id=selected_variant_id,
        )

    def _classify(
        self,
        *,
        validation: VariantValidationResult,
        candidate_result: CandidateEvaluationResult,
    ) -> tuple[MatchOutcome, str | None]:
        coverage_validation_state = validation.governance.coverage_validation.validation_state
        coverage_state = validation.governance.coverage_validation.declared_state
        freshness_state = validation.governance.freshness.freshness_state

        if (
            candidate_result.selected_variant_id is not None
            and coverage_validation_state == CoverageValidationState.valid
            and coverage_state != CoverageState.invalid
            and freshness_state in {FreshnessState.fresh, FreshnessState.stale_compatible}
        ):
            return MatchOutcome.mapped, candidate_result.selected_variant_id

        if (
            candidate_result.ambiguous_candidate_ids
            and coverage_validation_state == CoverageValidationState.valid
            and coverage_state != CoverageState.invalid
            and freshness_state in {FreshnessState.fresh, FreshnessState.stale_compatible}
        ):
            return MatchOutcome.ambiguous, None

        if self._can_reject(validation=validation, candidate_result=candidate_result):
            return MatchOutcome.rejected, None

        if (
            len(candidate_result.viable_candidate_ids) > 1
            and coverage_validation_state == CoverageValidationState.valid
            and coverage_state == CoverageState.representative
            and freshness_state in {FreshnessState.fresh, FreshnessState.stale_compatible}
        ):
            return MatchOutcome.ambiguous, None

        return MatchOutcome.unresolved, None

    def _can_reject(
        self,
        *,
        validation: VariantValidationResult,
        candidate_result: CandidateEvaluationResult,
    ) -> bool:
        return (
            candidate_result.all_candidates_disproved
            and validation.governance.coverage_validation.validation_state
            == CoverageValidationState.valid
            and validation.governance.coverage_validation.declared_state
            == CoverageState.representative
            and validation.governance.freshness.freshness_state
            in {FreshnessState.fresh, FreshnessState.stale_compatible}
        )

    def _empty_candidate_result(
        self,
        request: VariantMatchRequest,
    ) -> CandidateEvaluationResult:
        return CandidateEvaluationResult(
            candidate_ids_considered=[
                variant.canonical_variant_id for variant in request.variant_candidates
            ],
            rationale=["candidate_evaluation_skipped"],
        )

    def _finalize(
        self,
        *,
        request: VariantMatchRequest,
        validation: VariantValidationResult,
        candidate_result: CandidateEvaluationResult,
        outcome: MatchOutcome,
        selected_variant_id: str | None,
    ) -> VariantMatchResponse:
        rationale = self.rationale_builder.build(
            request=request,
            validation=validation,
            candidate_result=candidate_result,
            outcome=outcome,
            selected_variant_id=selected_variant_id,
        )
        trace = self.audit_recorder.build_trace(
            request=request,
            validation=validation,
            candidate_result=candidate_result,
            outcome=outcome,
            rationale=rationale,
            selected_variant_id=selected_variant_id,
            matcher_version=self.matcher_version,
        )
        record = self.audit_recorder.build_record(
            trace=trace,
            request=request,
            validation=validation,
            candidate_result=candidate_result,
            outcome=outcome,
            rationale=rationale,
            selected_variant_id=selected_variant_id,
            matcher_version=self.matcher_version,
        )
        self.last_trace = trace
        self.last_audit_record = record
        logger.info(
            "variant_match_complete outcome=%s platform=%s platform_listing_id=%s",
            outcome.value,
            request.platform_listing.platform,
            request.platform_listing.platform_listing_id,
        )
        return VariantMatchResponse(
            outcome=outcome,
            selected_variant=self._selected_variant(
                request=request,
                selected_variant_id=selected_variant_id,
            ),
            rationale=rationale,
        )

    def _selected_variant(
        self,
        *,
        request: VariantMatchRequest,
        selected_variant_id: str | None,
    ) -> ProductVariant | None:
        if selected_variant_id is None:
            return None
        for variant in request.variant_candidates:
            if variant.canonical_variant_id == selected_variant_id:
                return variant
        return None
