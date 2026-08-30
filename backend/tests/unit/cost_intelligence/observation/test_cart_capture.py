from app.cart_optimization.types import CandidateItemAllocation, CandidateListingProvenance
from app.cost_intelligence.observation.cart_capture import (
    CartOwnershipVerifier,
    CartVerificationStatus,
    RetailerCartIdentity,
    RetailerCartLine,
    RetailerCartSnapshot,
)
from app.cost_intelligence.shared.money import Money


def allocation() -> CandidateItemAllocation:
    return CandidateItemAllocation(
        item_id="item-1",
        canonical_variant_id="variant-1",
        quantity=2,
        retailer_id="blinkit-gurugram",
        checkout_group_id="group-1",
        listing_provenance=CandidateListingProvenance(
            platform="blinkit",
            platform_listing_id="obs-1",
            observation_id="observation-1",
            retailer_product_id="637879",
            observed_selling_price=Money(currency="INR", minor_units=5500),
        ),
    )


def snapshot(*, product_id="637879", quantity=2, available=True, request_id="request-1", plan_id="plan-1"):
    return RetailerCartSnapshot(
        identity=RetailerCartIdentity(
            retailer_id="blinkit-gurugram",
            request_id=request_id,
            plan_id=plan_id,
            retailer_cart_id="cart-1" if available else None,
            identity_available=available,
        ),
        lines=(RetailerCartLine(
            retailer_product_id=product_id,
            quantity=quantity,
            retailer_id="blinkit-gurugram",
            request_id=request_id,
            plan_id=plan_id,
            source_reference="fixture",
        ),),
    )


def test_exact_retailer_line_and_quantity_are_verified() -> None:
    result = CartOwnershipVerifier().verify(
        request_id="request-1", plan_id="plan-1", allocations=(allocation(),), snapshot=snapshot()
    )
    assert result.status is CartVerificationStatus.VERIFIED


def test_unavailable_cart_identity_is_not_verified() -> None:
    result = CartOwnershipVerifier().verify(
        request_id="request-1", plan_id="plan-1", allocations=(allocation(),), snapshot=snapshot(available=False)
    )
    assert result.status is CartVerificationStatus.UNVERIFIABLE


def test_unexpected_line_contaminates_capture() -> None:
    result = CartOwnershipVerifier().verify(
        request_id="request-1", plan_id="plan-1", allocations=(allocation(),), snapshot=snapshot(product_id="other")
    )
    assert result.status is CartVerificationStatus.CONTAMINATED


def test_correlation_mismatch_is_rejected() -> None:
    result = CartOwnershipVerifier().verify(
        request_id="request-1", plan_id="plan-1", allocations=(allocation(),), snapshot=snapshot(request_id="other")
    )
    assert result.status is CartVerificationStatus.MISMATCH


def test_line_reference_is_deterministic() -> None:
    first = snapshot().lines[0].deterministic_reference
    second = snapshot().lines[0].deterministic_reference
    assert first == second
