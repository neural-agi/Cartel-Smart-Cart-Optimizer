from __future__ import annotations

from app.product_intelligence.matching.types import (
    CandidateEvaluationResult,
    MatchOutcome,
    VariantGovernanceContext,
    VariantMatchRequest,
    VariantValidationResult,
)


class DeterministicVariantRationaleBuilder:
    """Build deterministic rationale strings for variant matching decisions."""

    def build(
        self,
        *,
        request: VariantMatchRequest,
        validation: VariantValidationResult,
        candidate_result: CandidateEvaluationResult,
        outcome: MatchOutcome,
        selected_variant_id: str | None = None,
    ) -> list[str]:
        rationale: list[str] = [
            f"outcome={outcome.value}",
            f"platform={request.platform_listing.platform}",
            f"platform_listing_id={request.platform_listing.platform_listing_id}",
            f"raw_title={request.platform_listing.raw_title}",
            f"variant_candidate_count={len(request.variant_candidates)}",
        ]

        if request.platform_listing.raw_quantity_text:
            rationale.append(
                f"raw_quantity_text={request.platform_listing.raw_quantity_text}"
            )
        if request.platform_listing.raw_category_text:
            rationale.append(
                f"raw_category_text={request.platform_listing.raw_category_text}"
            )
        rationale.append(
            f"capture_timestamp={request.listing_observation.capture_timestamp.isoformat()}"
        )
        rationale.append(f"parser_version={request.listing_observation.parser_version}")
        rationale.append(
            "capture_context_reference="
            + str(request.listing_observation.capture_context_reference)
        )
        rationale.append(
            f"source_artifact_reference={request.listing_observation.source_artifact_reference}"
        )
        if request.product is None:
            rationale.append("product_context=missing")
        else:
            rationale.append(f"product_id={request.product.canonical_product_id}")
            rationale.append(
                f"product_identity_status={request.product.product_identity_status.value}"
            )

        rationale.extend(validation.rationale)
        rationale.extend(
            [
                f"coverage_state={validation.governance.coverage_validation.declared_state.value}",
                f"coverage_validation_state={validation.governance.coverage_validation.validation_state.value}",
                f"freshness_state={validation.governance.freshness.freshness_state.value}",
                f"candidate_ids_considered={len(candidate_result.candidate_ids_considered)}",
                f"candidate_ids_eliminated={len(candidate_result.eliminated_candidate_ids)}",
                f"viable_candidate_ids={len(candidate_result.viable_candidate_ids)}",
            ]
        )

        if validation.governance.coverage_validation.declaration_id:
            rationale.append(
                f"coverage_declaration_id={validation.governance.coverage_validation.declaration_id}"
            )
        if validation.governance.coverage_validation.coverage_scope_id:
            rationale.append(
                f"coverage_scope_id={validation.governance.coverage_validation.coverage_scope_id}"
            )
        if validation.governance.freshness.lineage_root_id:
            rationale.append(
                f"lineage_root_id={validation.governance.freshness.lineage_root_id}"
            )
        if validation.governance.freshness.revision_ids:
            rationale.append(
                "lineage_revision_ids="
                + ",".join(validation.governance.freshness.revision_ids)
            )
        if validation.governance.upstream_failures:
            rationale.extend(self._format_upstream_failures(validation.governance))

        rationale.extend(candidate_result.rationale)

        if selected_variant_id is not None:
            rationale.append(f"selected_variant_id={selected_variant_id}")

        if candidate_result.ambiguous_candidate_ids:
            rationale.append(
                "ambiguous_candidate_ids="
                + ",".join(candidate_result.ambiguous_candidate_ids)
            )
        if candidate_result.eliminated_candidate_ids:
            rationale.append(
                "eliminated_candidate_ids="
                + ",".join(candidate_result.eliminated_candidate_ids)
            )
        if candidate_result.rejection_rationale:
            rationale.extend(candidate_result.rejection_rationale)
        if candidate_result.viable_candidate_ids:
            rationale.append(
                "viable_candidate_ids="
                + ",".join(candidate_result.viable_candidate_ids)
            )

        return rationale

    def _format_upstream_failures(
        self,
        governance: VariantGovernanceContext,
    ) -> list[str]:
        lines: list[str] = []
        for failure in governance.upstream_failures:
            line = (
                f"upstream_failure={failure.dependency_name}"
                f"|state={failure.failure_state.value}"
            )
            if failure.record_id:
                line += f"|record_id={failure.record_id}"
            if failure.blocks_rejection:
                line += "|blocks_rejection=true"
            lines.append(line)
        return lines
