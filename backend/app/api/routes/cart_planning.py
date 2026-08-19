from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.cart_optimization.planning import CartPlanningRequest
from app.cart_optimization.providers import PlanningProviderUnavailable


router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/plan")
def plan_cart(request: CartPlanningRequest, http_request: Request):
    service = getattr(http_request.app.state, "cart_planning", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="cart planning is not configured",
        )
    try:
        return service.plan(request)
    except PlanningProviderUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
