from __future__ import annotations

from app.core.logging import get_logger
from app.product_intelligence.evidence.interfaces import EvidenceRegistry
from app.product_intelligence.evidence.storage import EvidenceFilesystemStore
from app.product_intelligence.evidence.types import (
    EvidenceBundle,
    EvidenceRegistrationRequest,
    EvidenceRegistrationResponse,
)


logger = get_logger(__name__)


class FilesystemEvidenceRegistry(EvidenceRegistry):
    """Concrete append-only evidence registry backed by the local filesystem."""

    def __init__(self, store: EvidenceFilesystemStore | None = None) -> None:
        self.store = store or EvidenceFilesystemStore()

    async def register(
        self,
        request: EvidenceRegistrationRequest,
    ) -> EvidenceRegistrationResponse:
        record = self.store.register(request)
        bundle = record.to_bundle()
        logger.info(
            "evidence_bundle_registered platform=%s evidence_id=%s source_artifact_reference=%s",
            request.platform,
            record.evidence_id,
            request.source_artifact_reference,
        )
        return EvidenceRegistrationResponse(evidence_bundle=bundle)

    async def assemble(self, request: EvidenceBundle) -> EvidenceBundle:
        stored_request = EvidenceRegistrationRequest(
            platform=request.platform,
            source_artifact_reference=request.source_artifact_reference,
            parser_version=request.parser_version or "unknown",
            capture_timestamp=request.capture_timestamp,
            capture_context_reference=request.capture_context_reference,
        )
        bundle = self.store.load_bundle(stored_request)
        logger.info(
            "evidence_bundle_assembled platform=%s source_artifact_reference=%s",
            bundle.platform,
            bundle.source_artifact_reference,
        )
        return bundle

