"""Phase J.1.1: Blinkit checkout capture is denied before probing.

Checkout capture previously inspected candidate allocations and launched a
browser probe. Both synchronous and asynchronous entry points now raise the
central policy denial before any retailer interaction.
"""

import asyncio

import pytest

from app.cart_optimization.types import (
    CandidateItemAllocation,
    CandidateListingProvenance,
    CartItemRequest,
)
from app.cost_intelligence.observation.capture_contract import CheckoutCaptureRequest
from app.cost_intelligence.shared.money import Money
from app.retailer_policy import RetailerPolicyBlocked
from app.scrapers.blinkit.checkout_capture import BlinkitCheckoutCaptureAdapter


def _allocation() -> CandidateItemAllocation:
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
            retailer_product_id="637879",
        ),
    )


def _request() -> CheckoutCaptureRequest:
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
        candidate_allocations=(_allocation(),),
    )


class _ExplodingProbe:
    async def probe(self, request):
        raise AssertionError("checkout probe must not be reached")


@pytest.mark.asyncio
async def test_blinkit_checkout_capture_denies_before_probe() -> None:
    adapter = BlinkitCheckoutCaptureAdapter(probe=_ExplodingProbe())

    with pytest.raises(RetailerPolicyBlocked) as error:
        await adapter.acapture(_request())

    assert error.value.reason_code == "blinkit_commercial_authorization_required"


def test_blinkit_checkout_sync_capture_denies_inside_running_loop() -> None:
    adapter = BlinkitCheckoutCaptureAdapter(probe=_ExplodingProbe())

    async def invoke() -> None:
        with pytest.raises(RetailerPolicyBlocked):
            adapter.capture(_request())

    asyncio.run(invoke())


def test_blinkit_checkout_capture_denies_with_default_adapter() -> None:
    adapter = BlinkitCheckoutCaptureAdapter()

    async def invoke() -> None:
        with pytest.raises(RetailerPolicyBlocked):
            await adapter.acapture(_request())

    asyncio.run(invoke())
