from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.core.logging import get_logger
from app.product_intelligence.matching.interfaces import VariantCandidateEvaluator
from app.product_intelligence.matching.types import (
    CandidateEvaluationResult,
    CandidateEliminationRecord,
    FreshnessState,
    NormalizedPackEvidenceSnapshot,
    VariantGovernanceContext,
    VariantMatchRequest,
)
from app.product_intelligence.models import (
    EvidenceReference,
    Measurement,
    PackComponent,
    PackConfiguration,
    PackKind,
)


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _CandidateSupportSummary:
    exact_support_candidate_ids: list[str]
    partial_support_candidate_ids: list[str]
    none_support_candidate_ids: list[str]
    contradicted_candidate_ids: list[str]


@dataclass(frozen=True, slots=True)
class _CandidateAssessment:
    candidate_id: str
    support_state: str
    eliminated: bool
    rule_id: str | None = None
    rule_name: str | None = None
    evidence_reference: str | None = None
    elimination_reason: str | None = None


class DeterministicVariantCandidateEvaluator(VariantCandidateEvaluator):
    """Deterministic evaluator for the frozen candidate-evaluation boundary."""

    async def evaluate(
        self,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
    ) -> CandidateEvaluationResult:
        evaluation_timestamp = datetime.now(timezone.utc)
        considered_candidates = self._canonicalize_candidates(request.variant_candidates)
        assessments = [
            self._assess_candidate(
                request=request,
                governance=governance,
                candidate=candidate,
            )
            for candidate in considered_candidates
        ]

        exact_ids = [
            assessment.candidate_id
            for assessment in assessments
            if assessment.support_state == "exact"
        ]
        partial_ids = [
            assessment.candidate_id
            for assessment in assessments
            if assessment.support_state == "partial"
        ]
        none_ids = [
            assessment.candidate_id
            for assessment in assessments
            if assessment.support_state == "none"
        ]
        contradicted_ids = [
            assessment.candidate_id
            for assessment in assessments
            if assessment.support_state == "contradicted"
        ]

        viable_ids = [
            assessment.candidate_id for assessment in assessments if not assessment.eliminated
        ]
        eliminated_ids = [
            assessment.candidate_id for assessment in assessments if assessment.eliminated
        ]
        elimination_records = [
            self._elimination_record(
                request=request,
                governance=governance,
                assessment=assessment,
                timestamp=evaluation_timestamp,
            )
            for assessment in assessments
            if assessment.eliminated
        ]

        selected_variant_id: str | None = None
        if len(exact_ids) == 1:
            selected_variant_id = exact_ids[0]

        ambiguous_ids: list[str] = []
        if selected_variant_id is None and len(viable_ids) > 1:
            ambiguous_ids = viable_ids.copy()
        if len(exact_ids) > 1:
            ambiguous_ids = viable_ids.copy()

        support_summary = _CandidateSupportSummary(
            exact_support_candidate_ids=exact_ids,
            partial_support_candidate_ids=partial_ids,
            none_support_candidate_ids=none_ids,
            contradicted_candidate_ids=contradicted_ids,
        )

        rationale = self._build_rationale(
            request=request,
            governance=governance,
            considered_candidates=considered_candidates,
            assessments=assessments,
            support_summary=support_summary,
            selected_variant_id=selected_variant_id,
            ambiguous_candidate_ids=ambiguous_ids,
        )

        all_candidates_disproved = bool(considered_candidates) and not viable_ids

        logger.debug(
            "variant_candidate_evaluation_complete platform=%s listing_id=%s candidates=%s viable=%s eliminated=%s",
            request.platform_listing.platform,
            request.platform_listing.platform_listing_id,
            len(considered_candidates),
            len(viable_ids),
            len(eliminated_ids),
        )

        return CandidateEvaluationResult(
            candidate_ids_considered=[
                candidate.canonical_variant_id for candidate in considered_candidates
            ],
            viable_candidate_ids=viable_ids,
            eliminated_candidate_ids=eliminated_ids,
            elimination_records=elimination_records,
            ambiguous_candidate_ids=ambiguous_ids,
            selected_variant_id=selected_variant_id,
            all_candidates_disproved=all_candidates_disproved,
            rejection_rationale=[],
            rationale=rationale,
        )

    def _canonicalize_candidates(self, candidates: list) -> list:
        seen: set[str] = set()
        canonical_candidates: list = []
        for candidate in candidates:
            candidate_id = candidate.canonical_variant_id
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            canonical_candidates.append(candidate)
        return canonical_candidates

    def _assess_candidate(
        self,
        *,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
        candidate,
    ) -> _CandidateAssessment:
        if self._is_directly_contradicted(
            request=request,
            governance=governance,
            candidate=candidate,
        ):
            return _CandidateAssessment(
                candidate_id=candidate.canonical_variant_id,
                support_state="contradicted",
                eliminated=True,
                rule_id="CE-02",
                rule_name="direct_contradiction_elimination",
                elimination_reason=self._contradiction_reason(
                    request=request,
                    governance=governance,
                    candidate=candidate,
                ),
            )

        if self._is_exact_supported(
            request=request,
            governance=governance,
            candidate=candidate,
        ):
            return _CandidateAssessment(
                candidate_id=candidate.canonical_variant_id,
                support_state="exact",
                eliminated=False,
            )

        if self._has_partial_support(
            request=request,
            governance=governance,
            candidate=candidate,
        ):
            return _CandidateAssessment(
                candidate_id=candidate.canonical_variant_id,
                support_state="partial",
                eliminated=False,
            )

        return _CandidateAssessment(
            candidate_id=candidate.canonical_variant_id,
            support_state="none",
            eliminated=False,
        )

    def _elimination_record(
        self,
        *,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
        assessment: _CandidateAssessment,
        timestamp: datetime,
    ) -> CandidateEliminationRecord:
        return CandidateEliminationRecord(
            candidate_id=assessment.candidate_id,
            rule_id=assessment.rule_id or "CE-02",
            rule_name=assessment.rule_name or "direct_contradiction_elimination",
            evidence_reference=self._candidate_evidence_reference(
                request=request,
                governance=governance,
                assessment=assessment,
            ),
            elimination_reason=assessment.elimination_reason
            or "candidate_directly_contradicted_by_governed_inputs",
            timestamp=timestamp,
        )

    def _is_directly_contradicted(
        self,
        *,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
        candidate,
    ) -> bool:
        if request.product is not None and (
            candidate.canonical_product_id != request.product.canonical_product_id
        ):
            return True

        normalized_pack = governance.normalized_pack_evidence
        if normalized_pack is None:
            return False

        return self._pack_conflicts(candidate.pack_configuration, normalized_pack)

    def _is_exact_supported(
        self,
        *,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
        candidate,
    ) -> bool:
        if request.product is None:
            return False
        if candidate.canonical_product_id != request.product.canonical_product_id:
            return False

        if governance.freshness.freshness_state not in {
            FreshnessState.fresh,
            FreshnessState.stale_compatible,
        }:
            return False

        normalized_pack = governance.normalized_pack_evidence
        if normalized_pack is None:
            return False

        if self._pack_conflicts(candidate.pack_configuration, normalized_pack):
            return False

        if not self._pack_exact_match(candidate.pack_configuration, normalized_pack):
            return False

        if request.platform_listing.raw_quantity_text and normalized_pack.raw_quantity_text:
            if request.platform_listing.raw_quantity_text.strip() != normalized_pack.raw_quantity_text.strip():
                return False

        return True

    def _has_partial_support(
        self,
        *,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
        candidate,
    ) -> bool:
        if request.product is None:
            return False
        if candidate.canonical_product_id != request.product.canonical_product_id:
            return False
        if governance.freshness.freshness_state in {
            FreshnessState.missing,
            FreshnessState.invalid,
            FreshnessState.stale_unresolved,
            FreshnessState.stale_conflicting,
        }:
            return False

        normalized_pack = governance.normalized_pack_evidence
        if normalized_pack is None:
            return True

        if self._pack_conflicts(candidate.pack_configuration, normalized_pack):
            return False

        if self._pack_overlap(candidate.pack_configuration, normalized_pack):
            return True

        if request.platform_listing.raw_quantity_text:
            return True

        return (
            candidate.pack_configuration.pack_kind != PackKind.unknown
            or candidate.pack_configuration.consumer_unit_count is not None
            or candidate.pack_configuration.content_per_consumer_unit is not None
            or candidate.pack_configuration.total_declared_content is not None
            or candidate.pack_configuration.packaging_form is not None
            or bool(candidate.pack_configuration.component_set)
        )

    def _pack_conflicts(
        self,
        candidate_pack: PackConfiguration,
        governed_pack: NormalizedPackEvidenceSnapshot,
    ) -> bool:
        if (
            governed_pack.pack_kind != PackKind.unknown
            and candidate_pack.pack_kind != PackKind.unknown
            and candidate_pack.pack_kind != governed_pack.pack_kind
        ):
            return True

        if (
            governed_pack.consumer_unit_count is not None
            and candidate_pack.consumer_unit_count is not None
            and candidate_pack.consumer_unit_count != governed_pack.consumer_unit_count
        ):
            return True

        if self._measurement_conflicts(
            candidate_pack.content_per_consumer_unit,
            governed_pack.content_per_consumer_unit,
        ):
            return True

        if self._measurement_conflicts(
            candidate_pack.total_declared_content,
            governed_pack.total_declared_content,
        ):
            return True

        if self._text_conflicts(candidate_pack.packaging_form, governed_pack.packaging_form):
            return True

        if governed_pack.component_set and candidate_pack.component_set:
            if self._component_signatures(candidate_pack.component_set) != self._component_signatures(
                governed_pack.component_set
            ):
                return True

        return False

    def _pack_exact_match(
        self,
        candidate_pack: PackConfiguration,
        governed_pack: NormalizedPackEvidenceSnapshot,
    ) -> bool:
        matched_any = False
        if (
            governed_pack.pack_kind != PackKind.unknown
            and candidate_pack.pack_kind != governed_pack.pack_kind
        ):
            return False
        if (
            governed_pack.pack_kind != PackKind.unknown
            and candidate_pack.pack_kind == governed_pack.pack_kind
        ):
            matched_any = True

        if (
            governed_pack.consumer_unit_count is not None
            and candidate_pack.consumer_unit_count != governed_pack.consumer_unit_count
        ):
            return False
        if (
            governed_pack.consumer_unit_count is not None
            and candidate_pack.consumer_unit_count == governed_pack.consumer_unit_count
        ):
            matched_any = True

        if not self._measurement_matches(
            candidate_pack.content_per_consumer_unit,
            governed_pack.content_per_consumer_unit,
        ):
            return False
        if (
            candidate_pack.content_per_consumer_unit is not None
            and governed_pack.content_per_consumer_unit is not None
        ):
            matched_any = True

        if not self._measurement_matches(
            candidate_pack.total_declared_content,
            governed_pack.total_declared_content,
        ):
            return False
        if (
            candidate_pack.total_declared_content is not None
            and governed_pack.total_declared_content is not None
        ):
            matched_any = True

        if not self._text_matches(candidate_pack.packaging_form, governed_pack.packaging_form):
            return False
        if candidate_pack.packaging_form is not None and governed_pack.packaging_form is not None:
            matched_any = True

        if governed_pack.component_set:
            if self._component_signatures(candidate_pack.component_set) != self._component_signatures(
                governed_pack.component_set
            ):
                return False
            if candidate_pack.component_set:
                matched_any = True

        return matched_any

    def _pack_overlap(
        self,
        candidate_pack: PackConfiguration,
        governed_pack: NormalizedPackEvidenceSnapshot,
    ) -> bool:
        if governed_pack.pack_kind != PackKind.unknown:
            if candidate_pack.pack_kind == governed_pack.pack_kind:
                return True
        if (
            governed_pack.consumer_unit_count is not None
            and candidate_pack.consumer_unit_count == governed_pack.consumer_unit_count
        ):
            return True
        if self._measurement_matches(
            candidate_pack.content_per_consumer_unit,
            governed_pack.content_per_consumer_unit,
        ):
            return True
        if self._measurement_matches(
            candidate_pack.total_declared_content,
            governed_pack.total_declared_content,
        ):
            return True
        if self._text_matches(candidate_pack.packaging_form, governed_pack.packaging_form):
            return True
        if governed_pack.component_set and candidate_pack.component_set:
            return self._component_signatures(candidate_pack.component_set) == self._component_signatures(
                governed_pack.component_set
            )
        return False

    def _measurement_matches(
        self,
        candidate_measurement: Measurement | None,
        governed_measurement: Measurement | None,
    ) -> bool:
        if candidate_measurement is None or governed_measurement is None:
            return False
        return self._measurement_signature(candidate_measurement) == self._measurement_signature(
            governed_measurement
        )

    def _measurement_conflicts(
        self,
        candidate_measurement: Measurement | None,
        governed_measurement: Measurement | None,
    ) -> bool:
        if candidate_measurement is None or governed_measurement is None:
            return False
        return self._measurement_signature(candidate_measurement) != self._measurement_signature(
            governed_measurement
        )

    def _measurement_signature(self, measurement: Measurement) -> tuple[str, str, str, str]:
        return (
            self._decimal_signature(measurement.value),
            measurement.unit.strip(),
            measurement.dimension.value,
            measurement.content_basis,
        )

    def _component_signatures(self, components: list[PackComponent]) -> list[tuple[str, str | None, tuple[str, str, str, str] | None]]:
        signatures: list[tuple[str, str | None, tuple[str, str, str, str] | None]] = []
        for component in components:
            signatures.append(
                (
                    component.label.strip(),
                    component.quantity_text.strip() if component.quantity_text else None,
                    self._measurement_signature(component.quantity)
                    if component.quantity is not None
                    else None,
                )
            )
        return signatures

    def _text_matches(self, candidate_text: str | None, governed_text: str | None) -> bool:
        if candidate_text is None or governed_text is None:
            return False
        return candidate_text.strip() == governed_text.strip()

    def _text_conflicts(self, candidate_text: str | None, governed_text: str | None) -> bool:
        if candidate_text is None or governed_text is None:
            return False
        return candidate_text.strip() != governed_text.strip()

    def _decimal_signature(self, value: Decimal) -> str:
        normalized = value.normalize()
        if normalized == normalized.to_integral():
            return f"{normalized.to_integral()}"
        return format(normalized, "f").rstrip("0").rstrip(".")

    def _contradiction_reason(
        self,
        *,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
        candidate,
    ) -> str:
        if request.product is not None and (
            candidate.canonical_product_id != request.product.canonical_product_id
        ):
            return "candidate_product_id_conflicts_with_governed_product_context"

        normalized_pack = governance.normalized_pack_evidence
        if normalized_pack is not None:
            return "candidate_pack_configuration_conflicts_with_governed_pack_evidence"
        return "candidate_directly_contradicted_by_governed_inputs"

    def _candidate_evidence_reference(
        self,
        *,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
        assessment: _CandidateAssessment,
    ) -> EvidenceReference:
        if request.product is not None and assessment.rule_id == "CE-02":
            return EvidenceReference(
                source_type="product_context",
                source_id=request.product.canonical_product_id,
                capture_timestamp=request.listing_observation.capture_timestamp,
                note=assessment.elimination_reason,
            )

        normalized_pack = governance.normalized_pack_evidence
        if normalized_pack is not None and normalized_pack.source_artifact_reference is not None:
            return EvidenceReference(
                source_type="normalized_pack_evidence",
                source_id=normalized_pack.source_artifact_reference,
                capture_timestamp=request.listing_observation.capture_timestamp,
                note=assessment.elimination_reason,
            )

        return EvidenceReference(
            source_type="governed_inputs",
            source_id=request.platform_listing.platform_listing_id,
            capture_timestamp=request.listing_observation.capture_timestamp,
            note=assessment.elimination_reason,
        )

    def _pack_evidence_reference(self, pack: NormalizedPackEvidenceSnapshot) -> str:
        parts = ["normalized_pack_evidence"]
        if pack.source_artifact_reference:
            parts.append(f"source_artifact_reference={pack.source_artifact_reference}")
        if pack.capture_context_reference:
            parts.append(f"capture_context_reference={pack.capture_context_reference}")
        if pack.parser_version:
            parts.append(f"parser_version={pack.parser_version}")
        if pack.raw_quantity_text:
            parts.append(f"raw_quantity_text={pack.raw_quantity_text}")
        return "|".join(parts)

    def _build_rationale(
        self,
        *,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
        considered_candidates,
        assessments: list[_CandidateAssessment],
        support_summary: _CandidateSupportSummary,
        selected_variant_id: str | None,
        ambiguous_candidate_ids: list[str],
    ) -> list[str]:
        rationale: list[str] = [
            "candidate_evaluation=deterministic",
            "candidate_rule_order=CE-01,CE-02,CE-03,CE-04,CE-05,CE-06,CE-07,CE-08",
            f"candidate_ids_considered={','.join(candidate.canonical_variant_id for candidate in considered_candidates)}",
            f"viable_candidate_ids={','.join(assessment.candidate_id for assessment in assessments if not assessment.eliminated)}",
            f"eliminated_candidate_ids={','.join(assessment.candidate_id for assessment in assessments if assessment.eliminated)}",
            f"exact_support_candidate_ids={','.join(support_summary.exact_support_candidate_ids)}",
            f"partial_support_candidate_ids={','.join(support_summary.partial_support_candidate_ids)}",
            f"none_support_candidate_ids={','.join(support_summary.none_support_candidate_ids)}",
            f"contradicted_candidate_ids={','.join(support_summary.contradicted_candidate_ids)}",
            f"all_candidates_disproved={bool(considered_candidates) and not any(not assessment.eliminated for assessment in assessments)}",
            f"freshness_state={governance.freshness.freshness_state.value}",
            f"coverage_state={governance.coverage_validation.declared_state.value}",
            f"coverage_validation_state={governance.coverage_validation.validation_state.value}",
            f"product_context={request.product.canonical_product_id if request.product else 'missing'}",
        ]

        if request.platform_listing.raw_quantity_text:
            rationale.append(
                f"raw_quantity_text={request.platform_listing.raw_quantity_text}"
            )
        if request.platform_listing.raw_category_text:
            rationale.append(
                f"raw_category_text={request.platform_listing.raw_category_text}"
            )
        if governance.normalized_pack_evidence is not None:
            rationale.append(
                "normalized_pack_evidence="
                + self._pack_evidence_reference(governance.normalized_pack_evidence)
            )

        for assessment in assessments:
            if assessment.eliminated:
                rationale.append(
                    "|".join(
                        part
                        for part in (
                            f"elimination_record",
                            f"candidate_id={assessment.candidate_id}",
                            f"rule_id={assessment.rule_id}",
                            f"rule_name={assessment.rule_name}",
                            f"evidence_reference={assessment.evidence_reference}",
                            f"elimination_reason={assessment.elimination_reason}",
                        )
                        if part is not None
                    )
                )
            else:
                rationale.append(
                    f"candidate_state={assessment.candidate_id}|support={assessment.support_state}"
                )

        if selected_variant_id is not None:
            rationale.append(f"selected_variant_id={selected_variant_id}")
        if ambiguous_candidate_ids:
            rationale.append(
                f"ambiguous_candidate_ids={','.join(ambiguous_candidate_ids)}"
            )
        return rationale
