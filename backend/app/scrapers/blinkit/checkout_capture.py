"""Blinkit checkout capture adapter.

The adapter uses the existing Blinkit browser/session stack and remains
fail-closed until Blinkit exposes enough verifiable cart state for a plan.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.cost_intelligence.observation.capture_contract import (
    CheckoutCaptureArtifact,
    CheckoutCaptureRequest,
)
from app.cost_intelligence.observation.capture_service import (
    CheckoutCaptureAdapterUnavailable,
)
from app.scrapers.blinkit.scraper import BlinkitScraper


class BlinkitCheckoutCaptureUnavailable(CheckoutCaptureAdapterUnavailable):
    """Typed Blinkit checkout failure with sanitized diagnostic context."""

    def __init__(self, message: str, *, reason_code: str, diagnostics: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.diagnostics = dict(diagnostics or {})


class BlinkitCheckoutProbe(Protocol):
    async def probe(self, request: CheckoutCaptureRequest) -> Mapping[str, Any]: ...


class BlinkitCheckoutCaptureAdapter:
    """Concrete Blinkit adapter up to the verified live cart boundary.

    Cartel has authoritative Blinkit product IDs, but live cart identity and
    cart-line identity remain unavailable when Blinkit rejects ``POST
    /v5/carts`` or does not expose verifiable cart state. This adapter validates
    all Cartel-owned inputs, establishes the existing Blinkit browser/session
    context, and refuses to emit checkout evidence unless cart verification can
    become authoritative.
    """

    platform = "blinkit"

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        probe: BlinkitCheckoutProbe | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._probe = probe

    def capture(self, request: CheckoutCaptureRequest) -> CheckoutCaptureArtifact:
        """Compatibility entry point for synchronous capture callers."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.acapture(request))
        raise BlinkitCheckoutCaptureUnavailable(
            "Blinkit checkout capture is asynchronous; call capture_async from an async context",
            reason_code="async_capture_required",
        )

    async def acapture(self, request: CheckoutCaptureRequest) -> CheckoutCaptureArtifact:
        self._validate_request(request)
        diagnostics = dict(await self._probe_request(request))
        reason = diagnostics.get("reason_code") or "blinkit_cart_identity_unverified"
        if diagnostics.get("cart_mutation_status") == 429:
            reason = "blinkit_cart_rate_limited"
        raise BlinkitCheckoutCaptureUnavailable(
            "Blinkit checkout capture is unavailable: " + reason,
            reason_code=str(reason),
            diagnostics=diagnostics,
        )

    def _validate_request(self, request: CheckoutCaptureRequest) -> None:
        if request.platform.lower() != self.platform:
            raise BlinkitCheckoutCaptureUnavailable(
                "Blinkit checkout adapter received a non-Blinkit capture request",
                reason_code="platform_mismatch",
            )
        if not request.candidate_allocations:
            raise BlinkitCheckoutCaptureUnavailable(
                "Blinkit checkout capture requires candidate allocations",
                reason_code="missing_candidate_allocations",
            )
        for allocation in request.candidate_allocations:
            provenance = allocation.listing_provenance
            if provenance.platform.lower() != self.platform:
                raise BlinkitCheckoutCaptureUnavailable(
                    "Blinkit checkout capture cannot mix non-Blinkit allocations",
                    reason_code="platform_mismatch",
                )
            if not provenance.retailer_product_id:
                raise BlinkitCheckoutCaptureUnavailable(
                    "Blinkit checkout capture requires authoritative retailer_product_id",
                    reason_code="missing_retailer_product_id",
                )

    async def _probe_request(self, request: CheckoutCaptureRequest) -> Mapping[str, Any]:
        if self._probe is not None:
            return await self._probe.probe(request)
        # Reuse the existing browser/session implementation. The known live
        # blocker is after product/session readiness, at cart mutation and
        # authoritative cart-state verification.
        first_product = request.candidate_allocations[0].listing_provenance.retailer_product_id
        scraper = BlinkitScraper(settings=self.settings)
        diagnostics: dict[str, Any] = {
            "platform": self.platform,
            "request_id": request.request_id,
            "plan_id": request.plan_id,
            "target_retailer_product_ids": tuple(
                allocation.listing_provenance.retailer_product_id
                for allocation in request.candidate_allocations
            ),
            "reason_code": "blinkit_cart_identity_unverified",
        }
        try:
            # This intentionally stops at the existing acquisition/readiness
            # boundary. It does not mutate cart state or visit checkout.
            response = await scraper._fetch_via_browser(str(first_product))
            diagnostics.update(
                {
                    "browser_session": "available",
                    "navigation_status": response.status_code,
                    "product_page_probe": "completed",
                    "cart_identity_available": False,
                    "cart_line_identity_available": False,
                }
            )
        except Exception as exc:
            diagnostics.update(
                {
                    "browser_session": "unavailable",
                    "error_type": exc.__class__.__name__,
                    "reason_code": "blinkit_session_unavailable",
                }
            )
        return diagnostics
