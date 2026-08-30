"""Deterministic checkout adapter for contract and integration testing.

This adapter is deliberately fixture-only. It never represents fixture data as
live retailer evidence and never mutates a retailer cart.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.cost_intelligence.observation.cart_capture import (
    CartOwnershipVerifier,
    CartVerificationStatus,
    RetailerCartSnapshot,
)
from app.cost_intelligence.observation.capture_contract import (
    CheckoutCaptureArtifact,
    CheckoutCaptureRequest,
)
from app.cost_intelligence.observation.capture_service import (
    CheckoutCaptureAdapterUnavailable,
)
from app.data_ingestion.enums import CaptureType
from app.product_intelligence.models import EvidenceReference


class FixtureCheckoutCaptureAdapter:
    """Return a verified, immutable checkout artifact from supplied fixture data."""

    def __init__(self, *, snapshot: RetailerCartSnapshot, checkout_payload: dict[str, Any]) -> None:
        self._snapshot = snapshot
        self._checkout_payload = checkout_payload

    def capture(self, request: CheckoutCaptureRequest) -> CheckoutCaptureArtifact:
        result = CartOwnershipVerifier().verify(
            request_id=request.request_id,
            plan_id=request.plan_id,
            allocations=request.candidate_allocations,
            snapshot=self._snapshot,
        )
        if result.status is not CartVerificationStatus.VERIFIED:
            raise CheckoutCaptureAdapterUnavailable(
                "fixture retailer cart is not verified: " + ", ".join(result.reasons)
            )
        payload = dict(self._checkout_payload)
        payload["platform"] = request.platform
        payload["capture_context_reference"] = self._snapshot.identity.retailer_cart_id
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        artifact_id = hashlib.sha256(
            request.request_id.encode() + b":" + request.plan_id.encode() + b":" + encoded
        ).hexdigest()
        return CheckoutCaptureArtifact(
            artifact_id=artifact_id,
            capture_type=CaptureType.CHECKOUT,
            platform=request.platform,
            capture_timestamp=datetime.now(timezone.utc),
            source_reference="fixture://checkout/" + artifact_id,
            capture_version="fixture-v1",
            parser_version="fixture-checkout-parser-v1",
            content_type="application/json",
            request_id=request.request_id,
            plan_id=request.plan_id,
            payload=encoded,
            evidence_references=(EvidenceReference(
                source_type="fixture_checkout",
                source_id=artifact_id,
                note="deterministic test fixture; not live retailer evidence",
            ),),
        )

    async def acapture(self, request: CheckoutCaptureRequest) -> CheckoutCaptureArtifact:
        return self.capture(request)
