import pytest

from app.cart_optimization.types import (
    CartItemRequest,
    CandidateItemAllocation,
    CandidateListingProvenance,
)
from app.cost_intelligence.observation.capture_contract import CheckoutCaptureRequest
from app.cost_intelligence.shared.money import Money
from app.scrapers.blinkit.checkout_capture import (
    BlinkitCheckoutCaptureAdapter,
    BlinkitCheckoutCaptureUnavailable,
)
from app.scrapers.base.types import RawHttpResponse


def _allocation(*, retailer_product_id: str | None = "637879") -> CandidateItemAllocation:
    return CandidateItemAllocation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=1,
        retailer_id="blinkit-gurugram",
        checkout_group_id="blinkit-gurugram",
        listing_provenance=CandidateListingProvenance(
            platform="blinkit",
            platform_listing_id="source-index-1",
            observation_id="observation-1",
            observed_selling_price=Money(currency="INR", minor_units=5500),
            retailer_product_id=retailer_product_id,
        ),
    )


def _request(*, allocation: CandidateItemAllocation | None = None) -> CheckoutCaptureRequest:
    allocation = allocation or _allocation()
    return CheckoutCaptureRequest(
        request_id="request-1",
        plan_id="plan-1",
        platform="blinkit",
        cart_items=(
            CartItemRequest(
                item_id="item-1",
                canonical_variant_id="variant-1",
                quantity=1,
            ),
        ),
        candidate_allocations=(allocation,),
    )


class _Probe:
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        self.requests = []

    async def probe(self, request):
        self.requests.append(request)
        return self.diagnostics


@pytest.mark.asyncio
async def test_blinkit_checkout_requires_authoritative_retailer_product_id() -> None:
    adapter = BlinkitCheckoutCaptureAdapter(probe=_Probe({}))

    with pytest.raises(BlinkitCheckoutCaptureUnavailable) as exc:
        await adapter.acapture(_request(allocation=_allocation(retailer_product_id=None)))

    assert exc.value.reason_code == "missing_retailer_product_id"


@pytest.mark.asyncio
async def test_blinkit_checkout_classifies_cart_rate_limit_without_artifact() -> None:
    probe = _Probe({"cart_mutation_status": 429, "endpoint_path": "/v5/carts"})
    adapter = BlinkitCheckoutCaptureAdapter(probe=probe)

    with pytest.raises(BlinkitCheckoutCaptureUnavailable) as exc:
        await adapter.acapture(_request())

    assert exc.value.reason_code == "blinkit_cart_rate_limited"
    assert exc.value.diagnostics["endpoint_path"] == "/v5/carts"
    assert probe.requests[0].candidate_allocations[0].listing_provenance.retailer_product_id == "637879"


@pytest.mark.asyncio
async def test_blinkit_checkout_keeps_cart_identity_unverified_fail_closed() -> None:
    adapter = BlinkitCheckoutCaptureAdapter(
        probe=_Probe({
            "browser_session": "available",
            "cart_identity_available": False,
            "cart_line_identity_available": False,
        })
    )

    with pytest.raises(BlinkitCheckoutCaptureUnavailable) as exc:
        await adapter.acapture(_request())

    assert exc.value.reason_code == "blinkit_cart_identity_unverified"
    assert "637879" in exc.value.diagnostics["target_retailer_product_ids"]


def test_sync_capture_reports_async_requirement_inside_running_loop() -> None:
    adapter = BlinkitCheckoutCaptureAdapter(probe=_Probe({}))

    async def invoke():
        with pytest.raises(BlinkitCheckoutCaptureUnavailable) as exc:
            adapter.capture(_request())
        assert exc.value.reason_code == "async_capture_required"

    import asyncio

    asyncio.run(invoke())


@pytest.mark.asyncio
async def test_blinkit_browser_access_denial_is_preserved_as_typed_reason(monkeypatch) -> None:
    class BlockedScraper:
        def __init__(self, **kwargs):
            pass

        @staticmethod
        def _is_access_denied(response):
            return True

        async def _fetch_via_browser(self, product_id):
            return RawHttpResponse(
                url="https://blinkit.com/s/?q=milk", status_code=200, headers={},
                body=b"access denied - you have been blocked - Cloudflare Ray ID abc",
            )

    monkeypatch.setattr("app.scrapers.blinkit.checkout_capture.BlinkitScraper", BlockedScraper)
    adapter = BlinkitCheckoutCaptureAdapter()
    with pytest.raises(BlinkitCheckoutCaptureUnavailable) as exc:
        await adapter.acapture(_request())
    assert exc.value.reason_code == "retailer_access_denied"
    assert exc.value.diagnostics["browser_session"] == "blocked"
