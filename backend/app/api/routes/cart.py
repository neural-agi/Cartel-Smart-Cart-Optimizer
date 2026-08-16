from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.services.cart_resolution import (
    CartResolutionRequest,
    CartResolutionResult,
    CartResolutionService,
)


router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/resolve", response_model=CartResolutionResult)
def resolve_cart(request: CartResolutionRequest, http_request: Request) -> CartResolutionResult:
    service = getattr(http_request.app.state, "cart_resolution", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="cart resolution is not configured",
        )
    return service.resolve(request)
