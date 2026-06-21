from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.product_intelligence.models import (
    EvidenceReference,
    Measurement,
    PackComponent,
    PackKind,
    ListingObservation,
    PlatformListing,
    Product,
    ProductVariant,
)


class MatchOutcome(StrEnum):
    """High-level outcome of a matching decision."""

    mapped = "mapped"
    unresolved = "unresolved"
    ambiguous = "ambiguous"
    conflicting = "conflicting"
    rejected = "rejected"


class ProductMatchRequest(BaseModel):
    """Input for product-level matching."""

    platform_listing: PlatformListing
    listing_observation: ListingObservation
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    product_candidates: list[Product] = Field(default_factory=list)


class ProductMatchResponse(BaseModel):
    """Output of product-level matching."""

    outcome: MatchOutcome
    selected_product: Product | None = None
    rationale: list[str] = Field(default_factory=list)


class VariantMatchRequest(BaseModel):
    """Input for variant-level matching."""

    platform_listing: PlatformListing
    listing_observation: ListingObservation
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    product: Product | None = None
    variant_candidates: list[ProductVariant] = Field(default_factory=list)


class VariantMatchResponse(BaseModel):
    """Output of variant-level matching."""

    outcome: MatchOutcome
    selected_variant: ProductVariant | None = None
    rationale: list[str] = Field(default_factory=list)


class CoverageState(StrEnum):
    """Governed candidate-pool coverage states."""

    unknown = "unknown"
    partial = "partial"
    representative = "representative"
    invalid = "invalid"


class CoverageValidationState(StrEnum):
    """Independent validation results for a coverage declaration."""

    valid = "valid"
    unverifiable = "unverifiable"
    invalid = "invalid"
    contradictory = "contradictory"


class FreshnessState(StrEnum):
    """Governed freshness states for product context lineage."""

    fresh = "fresh"
    stale_compatible = "stale-compatible"
    stale_unresolved = "stale-unresolved"
    stale_conflicting = "stale-conflicting"
    missing = "missing"
    invalid = "invalid"


class UpstreamFailureState(StrEnum):
    """Deterministic states for upstream dependency failure handling."""

    missing = "missing"
    invalid = "invalid"
    contradictory = "contradictory"
    timeout = "timeout"
    partial = "partial"


class NormalizedPackEvidenceSnapshot(BaseModel):
    """Structured pack evidence consumed by Variant Matching."""

    raw_quantity_text: str | None = None
    pack_kind: PackKind = PackKind.unknown
    consumer_unit_count: int | None = None
    content_per_consumer_unit: Measurement | None = None
    total_declared_content: Measurement | None = None
    packaging_form: str | None = None
    component_set: list[PackComponent] = Field(default_factory=list)
    pack_configuration_status: str = "unknown"
    source_artifact_reference: str | None = None
    parser_version: str | None = None
    capture_context_reference: str | None = None


class CoverageValidationSnapshot(BaseModel):
    """Validated coverage declaration available to Variant Matching."""

    declaration_id: str | None = None
    coverage_scope_id: str | None = None
    declared_state: CoverageState = CoverageState.unknown
    validation_state: CoverageValidationState = CoverageValidationState.unverifiable
    rationale: list[str] = Field(default_factory=list)


class FreshnessSnapshot(BaseModel):
    """Validated freshness classification available to Variant Matching."""

    freshness_state: FreshnessState = FreshnessState.missing
    lineage_root_id: str | None = None
    revision_ids: list[str] = Field(default_factory=list)
    supersession_ids: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class UpstreamFailureSnapshot(BaseModel):
    """Deterministic record of an upstream dependency failure."""

    dependency_name: str
    failure_state: UpstreamFailureState
    record_id: str | None = None
    blocks_rejection: bool = False
    rationale: list[str] = Field(default_factory=list)


class VariantGovernanceContext(BaseModel):
    """Governed inputs consumed by the matcher orchestration layer."""

    coverage_validation: CoverageValidationSnapshot = Field(
        default_factory=CoverageValidationSnapshot
    )
    freshness: FreshnessSnapshot = Field(default_factory=FreshnessSnapshot)
    upstream_failures: list[UpstreamFailureSnapshot] = Field(default_factory=list)
    normalized_pack_evidence: NormalizedPackEvidenceSnapshot | None = None


class CandidateEvaluationResult(BaseModel):
    """Deterministic output of the internal candidate evaluation boundary."""

    candidate_ids_considered: list[str] = Field(default_factory=list)
    viable_candidate_ids: list[str] = Field(default_factory=list)
    eliminated_candidate_ids: list[str] = Field(default_factory=list)
    ambiguous_candidate_ids: list[str] = Field(default_factory=list)
    selected_variant_id: str | None = None
    all_candidates_disproved: bool = False
    rejection_rationale: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class VariantValidationResult(BaseModel):
    """Request validation result used by the variant orchestration slice."""

    blocking_outcome: MatchOutcome | None = None
    rationale: list[str] = Field(default_factory=list)
    governance: VariantGovernanceContext = Field(
        default_factory=VariantGovernanceContext
    )
    request_hash: str | None = None
    request_summary: list[str] = Field(default_factory=list)
    validated_at_utc: datetime | None = None
