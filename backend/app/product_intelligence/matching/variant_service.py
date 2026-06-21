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


class _NullVariantCandidateEvaluator(VariantCandidateEvaluator):
    """Conservative default evaluator for the first executable slice."""

    async def evaluate(
        self,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
    ) -> CandidateEvaluationResult:
        return CandidateEvaluationResult(
            candidate_ids_considered=[
                variant.canonical_variant_id for variant in request.variant_candidates
            ],
            rationale=["candidate_evaluation=not_provided"],
        )


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
        self.candidate_evaluator = candidate_evaluator or _NullVariantCandidateEvaluator()
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
        if len(candidate_result.ambiguous_candidate_ids) > 1 or (
            len(candidate_result.viable_candidate_ids) > 1
            and candidate_result.selected_variant_id is None
        ):
            return MatchOutcome.ambiguous, None

        if (
            candidate_result.selected_variant_id is not None
            and len(candidate_result.viable_candidate_ids) == 1
            and candidate_result.selected_variant_id
            == candidate_result.viable_candidate_ids[0]
        ):
            return MatchOutcome.mapped, candidate_result.selected_variant_id

        if self._can_reject(validation=validation, candidate_result=candidate_result):
            return MatchOutcome.rejected, None

        if len(candidate_result.viable_candidate_ids) > 1:
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
            and validation.governance.coverage_validation.validation_state.value
            == "valid"
            and validation.governance.coverage_validation.declared_state
            == CoverageState.representative
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
