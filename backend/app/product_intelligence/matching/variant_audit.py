from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.product_intelligence.matching.types import (
    CandidateEvaluationResult,
    MatchOutcome,
    VariantMatchRequest,
    VariantValidationResult,
)


class VariantDecisionTrace(BaseModel):
    """Internal execution trace for a single variant matching decision."""

    trace_id: str
    decision_id: str
    matcher_version: str
    request_hash: str
    platform_listing_id: str
    raw_title: str
    raw_quantity_text: str | None = None
    raw_category_text: str | None = None
    capture_timestamp: datetime | None = None
    parser_version: str | None = None
    source_artifact_reference: str | None = None
    capture_context_reference: str | None = None
    request_summary: list[str] = Field(default_factory=list)
    evidence_reference_list: list[str] = Field(default_factory=list)
    candidate_ids_considered: list[str] = Field(default_factory=list)
    candidate_ids_eliminated: list[str] = Field(default_factory=list)
    rule_references: list[str] = Field(default_factory=list)
    decision_path: list[str] = Field(default_factory=list)
    final_outcome: MatchOutcome
    selected_variant_id: str | None = None
    coverage_declaration_id: str | None = None
    coverage_scope_id: str | None = None
    coverage_validation_result: str = "unverifiable"
    coverage_state: str = "unknown"
    freshness_classification_result: str = "missing"
    lineage_root_id: str | None = None
    lineage_revision_ids: list[str] = Field(default_factory=list)
    upstream_failure_states: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VariantDecisionAuditRecord(BaseModel):
    """Append-only audit record for a final variant decision."""

    audit_id: str
    decision_id: str
    matcher_version: str
    rule_document_references: list[str] = Field(default_factory=list)
    request_hash: str
    platform_listing_id: str
    raw_title: str
    raw_quantity_text: str | None = None
    raw_category_text: str | None = None
    capture_timestamp: datetime | None = None
    parser_version: str | None = None
    source_artifact_reference: str | None = None
    capture_context_reference: str | None = None
    evidence_reference_list: list[str] = Field(default_factory=list)
    candidate_ids_considered: list[str] = Field(default_factory=list)
    candidate_ids_eliminated: list[str] = Field(default_factory=list)
    selected_candidate_id: str | None = None
    coverage_declaration_id: str | None = None
    coverage_scope_id: str | None = None
    coverage_validation_result: str = "unverifiable"
    coverage_state: str = "unknown"
    freshness_classification_result: str = "missing"
    lineage_root_id: str | None = None
    lineage_revision_ids: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    upstream_failure_states: list[str] = Field(default_factory=list)
    trace_id: str | None = None


class VariantAuditRecorder(ABC):
    """Internal boundary for constructing deterministic audit artifacts."""

    @abstractmethod
    def build_trace(
        self,
        *,
        request: VariantMatchRequest,
        validation: VariantValidationResult,
        candidate_result: CandidateEvaluationResult,
        outcome: MatchOutcome,
        rationale: list[str],
        selected_variant_id: str | None,
        matcher_version: str,
    ) -> VariantDecisionTrace:
        """Build an immutable execution trace for the decision."""

    @abstractmethod
    def build_record(
        self,
        *,
        trace: VariantDecisionTrace,
        request: VariantMatchRequest,
        validation: VariantValidationResult,
        candidate_result: CandidateEvaluationResult,
        outcome: MatchOutcome,
        rationale: list[str],
        selected_variant_id: str | None,
        matcher_version: str,
    ) -> VariantDecisionAuditRecord:
        """Build an append-only audit record for the decision."""


class DeterministicVariantAuditRecorder(VariantAuditRecorder):
    """Deterministic in-memory audit artifact builder for the variant slice."""

    def build_trace(
        self,
        *,
        request: VariantMatchRequest,
        validation: VariantValidationResult,
        candidate_result: CandidateEvaluationResult,
        outcome: MatchOutcome,
        rationale: list[str],
        selected_variant_id: str | None,
        matcher_version: str,
    ) -> VariantDecisionTrace:
        request_hash = self._request_hash(request, candidate_result)
        trace_id = self._stable_id("trace", request_hash, matcher_version, outcome.value)
        decision_id = self._stable_id("decision", request_hash, matcher_version, outcome.value)
        return VariantDecisionTrace(
            trace_id=trace_id,
            decision_id=decision_id,
            matcher_version=matcher_version,
            request_hash=request_hash,
            platform_listing_id=request.platform_listing.platform_listing_id,
            raw_title=request.platform_listing.raw_title,
            raw_quantity_text=request.platform_listing.raw_quantity_text,
            raw_category_text=request.platform_listing.raw_category_text,
            capture_timestamp=request.listing_observation.capture_timestamp,
            parser_version=request.listing_observation.parser_version,
            source_artifact_reference=request.listing_observation.source_artifact_reference,
            capture_context_reference=request.listing_observation.capture_context_reference,
            request_summary=validation.request_summary,
            evidence_reference_list=self._evidence_reference_list(request),
            candidate_ids_considered=candidate_result.candidate_ids_considered,
            candidate_ids_eliminated=candidate_result.eliminated_candidate_ids,
            rule_references=self._rule_references(),
            decision_path=self._decision_path(validation, candidate_result, outcome),
            final_outcome=outcome,
            selected_variant_id=selected_variant_id,
            coverage_declaration_id=validation.governance.coverage_validation.declaration_id,
            coverage_scope_id=validation.governance.coverage_validation.coverage_scope_id,
            coverage_validation_result=validation.governance.coverage_validation.validation_state.value,
            coverage_state=validation.governance.coverage_validation.declared_state.value,
            freshness_classification_result=validation.governance.freshness.freshness_state.value,
            lineage_root_id=validation.governance.freshness.lineage_root_id,
            lineage_revision_ids=validation.governance.freshness.revision_ids,
            upstream_failure_states=[
                failure.failure_state.value
                for failure in validation.governance.upstream_failures
            ],
            rationale=rationale,
        )

    def build_record(
        self,
        *,
        trace: VariantDecisionTrace,
        request: VariantMatchRequest,
        validation: VariantValidationResult,
        candidate_result: CandidateEvaluationResult,
        outcome: MatchOutcome,
        rationale: list[str],
        selected_variant_id: str | None,
        matcher_version: str,
    ) -> VariantDecisionAuditRecord:
        request_hash = trace.request_hash or self._request_hash(request, candidate_result)
        audit_id = self._stable_id("audit", request_hash, matcher_version, outcome.value)
        return VariantDecisionAuditRecord(
            audit_id=audit_id,
            decision_id=trace.decision_id,
            matcher_version=matcher_version,
            rule_document_references=self._rule_references(),
            request_hash=request_hash,
            platform_listing_id=request.platform_listing.platform_listing_id,
            raw_title=request.platform_listing.raw_title,
            raw_quantity_text=request.platform_listing.raw_quantity_text,
            raw_category_text=request.platform_listing.raw_category_text,
            capture_timestamp=request.listing_observation.capture_timestamp,
            parser_version=request.listing_observation.parser_version,
            source_artifact_reference=request.listing_observation.source_artifact_reference,
            capture_context_reference=request.listing_observation.capture_context_reference,
            evidence_reference_list=trace.evidence_reference_list,
            candidate_ids_considered=candidate_result.candidate_ids_considered,
            candidate_ids_eliminated=candidate_result.eliminated_candidate_ids,
            selected_candidate_id=selected_variant_id,
            coverage_declaration_id=validation.governance.coverage_validation.declaration_id,
            coverage_scope_id=validation.governance.coverage_validation.coverage_scope_id,
            coverage_validation_result=validation.governance.coverage_validation.validation_state.value,
            coverage_state=validation.governance.coverage_validation.declared_state.value,
            freshness_classification_result=validation.governance.freshness.freshness_state.value,
            lineage_root_id=validation.governance.freshness.lineage_root_id,
            lineage_revision_ids=validation.governance.freshness.revision_ids,
            rationale=rationale,
            upstream_failure_states=[
                failure.failure_state.value
                for failure in validation.governance.upstream_failures
            ],
            trace_id=trace.trace_id,
        )

    def _decision_path(
        self,
        validation: VariantValidationResult,
        candidate_result: CandidateEvaluationResult,
        outcome: MatchOutcome,
    ) -> list[str]:
        path = ["validate_request"]
        if validation.blocking_outcome is not None:
            path.append(f"validation_blocked={validation.blocking_outcome.value}")
        else:
            path.append("validation_passed")
        path.append(f"candidate_count={len(candidate_result.candidate_ids_considered)}")
        if outcome == MatchOutcome.conflicting:
            path.append("outcome=conflicting")
        elif outcome == MatchOutcome.ambiguous:
            path.append("outcome=ambiguous")
        elif outcome == MatchOutcome.mapped:
            path.append("outcome=mapped")
        elif outcome == MatchOutcome.rejected:
            path.append("outcome=rejected")
        else:
            path.append("outcome=unresolved")
        return path

    def _evidence_reference_list(self, request: VariantMatchRequest) -> list[str]:
        evidence_refs: list[str] = []
        for reference in request.evidence_references:
            evidence_refs.append(
                "|".join(
                    (
                        f"source_type={reference.source_type}",
                        f"source_id={reference.source_id}",
                    )
                )
            )
        return evidence_refs

    def _request_hash(
        self,
        request: VariantMatchRequest,
        candidate_result: CandidateEvaluationResult,
    ) -> str:
        payload = {
            "platform": request.platform_listing.platform,
            "platform_listing_id": request.platform_listing.platform_listing_id,
            "raw_title": request.platform_listing.raw_title,
            "raw_quantity_text": request.platform_listing.raw_quantity_text,
            "raw_category_text": request.platform_listing.raw_category_text,
            "product_id": request.product.canonical_product_id if request.product else None,
            "candidate_ids_considered": candidate_result.candidate_ids_considered,
            "evidence_references": [
                {"source_type": reference.source_type, "source_id": reference.source_id}
                for reference in request.evidence_references
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _rule_references(self) -> list[str]:
        return [
            "docs/outcome_boundary_clarification.md",
            "docs/coverage_validation_contract.md",
            "docs/coverage_qualification_contract.md",
            "docs/freshness_classification_contract.md",
            "docs/freshness_lineage_model.md",
            "docs/upstream_failure_governance.md",
            "docs/variant_boundary_review.md",
            "docs/variant_quantity_normalization_contract.md",
            "docs/variant_evidence_extraction_spec.md",
        ]

    def _stable_id(self, prefix: str, *parts: str) -> str:
        payload = "|".join((prefix, *parts))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{prefix}_{digest[:24]}"
