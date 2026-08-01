from __future__ import annotations

from app.product_intelligence.models import EvidenceReference


def evidence_identity(reference: EvidenceReference) -> tuple[str, str]:
    """Return the immutable identity of an evidence reference."""
    return reference.source_type, reference.source_id
