from __future__ import annotations

from app.product_intelligence.canonical_source.providers import CanonicalEvidenceProvider
from app.product_intelligence.canonical_source.storage import CanonicalEvidenceFilesystemStore
from app.product_intelligence.canonical_source.types import (
    CanonicalEvidenceAdmission,
    CanonicalEvidenceReview,
    CanonicalEvidenceReviewStatus,
)
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.models import EvidenceReference


class CanonicalEvidenceIngestionService:
    """Ingest evidence, queue governance, and admit only explicit approvals."""

    def __init__(self, *, provider: CanonicalEvidenceProvider, store: CanonicalEvidenceFilesystemStore, catalog: FilesystemAuthoritativeCatalog) -> None:
        self.provider = provider
        self.store = store
        self.catalog = catalog

    async def ingest(self, source_record_id: str) -> CanonicalEvidenceReview:
        artifact = await self.provider.fetch(source_record_id)
        self.store.put_artifact(artifact)
        candidate = self.provider.normalize(artifact)
        existing = self.store.get_review(candidate.candidate_id)
        if existing is not None:
            if existing.candidate != candidate:
                raise ValueError("canonical evidence candidate identity conflict")
            return existing
        review = CanonicalEvidenceReview(candidate=candidate)
        self.store.put_review(review)
        return review

    def approve(self, candidate_id: str, *, approval_reference: str, rationale: str) -> CanonicalEvidenceReview:
        review = self.store.get_review(candidate_id)
        if review is None:
            raise KeyError(f"unknown canonical evidence candidate: {candidate_id}")
        if review.candidate.status not in {CanonicalEvidenceReviewStatus.pending, CanonicalEvidenceReviewStatus.approved}:
            raise ValueError("canonical evidence candidate is not approvable")
        approved = review.model_copy(update={"candidate": review.candidate.model_copy(update={"status": CanonicalEvidenceReviewStatus.approved}), "decision_reference": approval_reference, "rationale": rationale})
        return self.store.put_review(approved)

    def admit(self, admission: CanonicalEvidenceAdmission) -> tuple[object, object]:
        review = self.store.get_review(admission.candidate_id)
        if review is None or review.candidate.status is not CanonicalEvidenceReviewStatus.approved:
            raise ValueError("canonical evidence candidate requires explicit approval before admission")
        if not admission.approval_reference.strip() or admission.approval_reference != review.decision_reference:
            raise ValueError("admission approval reference does not match review decision")
        evidence = tuple(admission.evidence_references)
        if not evidence:
            evidence = (EvidenceReference(source_type=review.candidate.source, source_id=review.candidate.artifact_id),)
        product = admission.product.model_copy(update={"evidence_references": list(evidence), "brand_reference": admission.product.brand_reference.model_copy(update={"evidence_references": list(evidence)})})
        variant = admission.variant.model_copy(update={"evidence_references": list(evidence)})
        registered_product = self.catalog.register_product(product)
        registered_variant = self.catalog.register_variant(variant)
        self.store.put_review(review.model_copy(update={"candidate": review.candidate.model_copy(update={"status": CanonicalEvidenceReviewStatus.admitted})}))
        return registered_product, registered_variant
