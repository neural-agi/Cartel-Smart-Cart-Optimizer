from __future__ import annotations

from pydantic import BaseModel, Field

from app.product_intelligence.models import EvidenceReference


class EvidenceBundle(BaseModel):
    """Durable evidence assembled for matching and review."""

    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    parser_version: str | None = None
    source_artifact_reference: str | None = None
    capture_context_reference: str | None = None


class EvidenceRegistrationRequest(BaseModel):
    """Input for registering durable evidence references."""

    source_artifact_reference: str
    parser_version: str
    capture_context_reference: str | None = None


class EvidenceRegistrationResponse(BaseModel):
    """Registered evidence references for downstream consumers."""

    evidence_bundle: EvidenceBundle

