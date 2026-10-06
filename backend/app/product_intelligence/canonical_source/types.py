from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.product_intelligence.models import EvidenceReference, Product, ProductVariant


class CanonicalEvidenceReviewStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    conflict = "conflict"
    admitted = "admitted"


class CanonicalEvidenceClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: str
    evidence_path: str


class CanonicalEvidenceArtifact(BaseModel):
    """Immutable, source-owned evidence; never a canonical catalog record."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    source: str
    source_record_id: str
    source_revision: str
    retrieved_at: datetime
    content_digest: str
    provider_version: str
    raw_payload: dict[str, Any]
    evidence_references: tuple[EvidenceReference, ...]


class CanonicalEvidenceCandidate(BaseModel):
    """Normalized source evidence awaiting an explicit governance decision."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str
    artifact_id: str
    source: str
    source_record_id: str
    source_revision: str
    claims: tuple[CanonicalEvidenceClaim, ...]
    status: CanonicalEvidenceReviewStatus = CanonicalEvidenceReviewStatus.pending


class CanonicalEvidenceReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate: CanonicalEvidenceCandidate
    decision_reference: str | None = None
    rationale: str | None = None


class CanonicalEvidenceAdmission(BaseModel):
    """Operator decision carrying explicit canonical entities to admit."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str
    approval_reference: str
    product: Product
    variant: ProductVariant
    evidence_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)
