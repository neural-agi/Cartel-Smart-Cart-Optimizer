"""Application checkout-capture orchestration; acquisition remains adapter-owned."""

from __future__ import annotations

from typing import Protocol
import inspect
import hashlib

from app.cost_intelligence.observation.capture import (
    CheckoutCaptureRegistration,
    CheckoutCaptureRegistrationService,
)
from app.cost_intelligence.observation.capture_contract import (
    CheckoutCaptureArtifact,
    CheckoutCaptureParser,
    CheckoutCaptureRequest,
)
from app.cost_intelligence.observation.checkout_capture import CheckoutObservationCorrelation
from app.data_ingestion.artifact_store import ArtifactStore, ArtifactPublicationRequest
from app.product_intelligence.models import EvidenceReference
from app.core.logging import get_logger


logger = get_logger(__name__)


class CheckoutCaptureAdapterUnavailable(RuntimeError):
    """Raised when no authoritative retailer capture adapter is configured."""


class CheckoutCaptureAdapter(Protocol):
    def capture(self, request: CheckoutCaptureRequest) -> CheckoutCaptureArtifact: ...

    async def acapture(self, request: CheckoutCaptureRequest) -> CheckoutCaptureArtifact: ...


class UnavailableCheckoutCaptureAdapter:
    def capture(self, request: CheckoutCaptureRequest) -> CheckoutCaptureArtifact:
        raise CheckoutCaptureAdapterUnavailable("checkout capture adapter is unavailable")


class CheckoutCaptureService:
    """Validate, parse, and register externally captured checkout evidence."""

    def __init__(
        self,
        *,
        adapter: CheckoutCaptureAdapter,
        parser: CheckoutCaptureParser,
        registration: CheckoutCaptureRegistrationService,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self._adapter = adapter
        self._parser = parser
        self._registration = registration
        self._artifact_store = artifact_store

    def capture(self, request: CheckoutCaptureRequest) -> CheckoutObservationCorrelation:
        logger.info(
            "checkout_capture_started request_id=%s plan_id=%s platform=%s",
            request.request_id,
            request.plan_id,
            request.platform,
        )
        try:
            artifact = self._adapter.capture(request)
        except CheckoutCaptureAdapterUnavailable:
            logger.warning(
                "checkout_capture_adapter_unavailable request_id=%s plan_id=%s platform=%s",
                request.request_id,
                request.plan_id,
                request.platform,
            )
            raise
        except Exception:
            logger.exception(
                "checkout_capture_adapter_failed request_id=%s plan_id=%s platform=%s",
                request.request_id,
                request.plan_id,
                request.platform,
            )
            raise
        if artifact.request_id != request.request_id or artifact.plan_id != request.plan_id:
            raise ValueError("checkout artifact ownership does not match capture request")
        parse_artifact = artifact
        if self._artifact_store is not None:
            digest = hashlib.sha256(artifact.payload).hexdigest()
            try:
                stored = self._artifact_store.store(
                    ArtifactPublicationRequest(
                        artifact_id=artifact.artifact_id,
                        content_digest=digest,
                        content_type=artifact.content_type,
                    ),
                    artifact.payload,
                )
            except Exception:
                logger.exception(
                    "checkout_capture_artifact_publication_failed request_id=%s plan_id=%s artifact_id=%s",
                    request.request_id,
                    request.plan_id,
                    artifact.artifact_id,
                )
                raise
            logger.info(
                "checkout_capture_artifact_published request_id=%s plan_id=%s artifact_id=%s",
                request.request_id,
                request.plan_id,
                artifact.artifact_id,
            )
            evidence = artifact.evidence_references + (
                EvidenceReference(
                    source_type="checkout_capture_source",
                    source_id=artifact.source_reference,
                ),
                EvidenceReference(
                    source_type="checkout_artifact_store",
                    source_id=stored.storage_reference_id,
                ),
            )
            parse_artifact = artifact.model_copy(
                update={
                    "source_reference": stored.storage_reference_id,
                    "evidence_references": evidence,
                }
            )
        try:
            observation = self._parser.parse(parse_artifact)
        except Exception:
            logger.exception(
                "checkout_capture_parse_failed request_id=%s plan_id=%s artifact_id=%s",
                request.request_id,
                request.plan_id,
                artifact.artifact_id,
            )
            raise
        logger.info(
            "checkout_capture_parsed request_id=%s plan_id=%s artifact_id=%s",
            request.request_id,
            request.plan_id,
            artifact.artifact_id,
        )
        try:
            result = self._registration.register(
                CheckoutCaptureRegistration(
                    request_id=request.request_id,
                    plan_id=request.plan_id,
                    observation=observation,
                )
            )
        except Exception:
            logger.exception(
                "checkout_capture_registration_failed request_id=%s plan_id=%s artifact_id=%s",
                request.request_id,
                request.plan_id,
                artifact.artifact_id,
            )
            raise
        logger.info(
            "checkout_capture_registered request_id=%s plan_id=%s artifact_id=%s",
            request.request_id,
            request.plan_id,
            artifact.artifact_id,
        )
        return result

    async def capture_async(self, request: CheckoutCaptureRequest) -> CheckoutObservationCorrelation:
        """Capture through an async retailer adapter without blocking an event loop.

        Existing synchronous adapters remain supported for compatibility; an
        async adapter exposes ``acapture`` and is awaited directly.
        """
        adapter_method = getattr(self._adapter, "acapture", None)
        if adapter_method is None:
            return self.capture(request)
        artifact = adapter_method(request)
        if not inspect.isawaitable(artifact):
            raise TypeError("async checkout adapter acapture must return an awaitable")
        # Keep the established validation, publication, parsing, and
        # registration path in one place by using a temporary adapter.
        captured_artifact = await artifact

        class _CapturedAdapter:
            def capture(self, _request):
                return captured_artifact

        return CheckoutCaptureService(
            adapter=_CapturedAdapter(),
            parser=self._parser,
            registration=self._registration,
            artifact_store=self._artifact_store,
        ).capture(request)
