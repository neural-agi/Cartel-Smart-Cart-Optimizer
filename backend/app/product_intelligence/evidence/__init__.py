"""Evidence contracts and filesystem registry for product intelligence."""

from app.product_intelligence.evidence.interfaces import EvidenceRegistry
from app.product_intelligence.evidence.service import FilesystemEvidenceRegistry
from app.product_intelligence.evidence.storage import EvidenceFilesystemStore, EvidenceRecord
from app.product_intelligence.evidence.types import (
    EvidenceBundle,
    EvidenceRegistrationRequest,
    EvidenceRegistrationResponse,
)

__all__ = [
    "EvidenceBundle",
    "EvidenceFilesystemStore",
    "EvidenceRecord",
    "EvidenceRegistry",
    "EvidenceRegistrationRequest",
    "EvidenceRegistrationResponse",
    "FilesystemEvidenceRegistry",
]
