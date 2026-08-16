from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryRequest,
    CartCandidateDiscoveryResult,
)


router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/candidates", response_model=CartCandidateDiscoveryResult)
def discover_cart_candidates(
    request: CartCandidateDiscoveryRequest,
    http_request: Request,
) -> CartCandidateDiscoveryResult:
    service = getattr(http_request.app.state, "cart_candidate_discovery", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="cart candidate discovery is not configured",
        )
    return service.discover(request)
