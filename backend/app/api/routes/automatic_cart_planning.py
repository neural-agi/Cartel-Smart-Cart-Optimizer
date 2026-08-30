from fastapi import APIRouter, Request, status

from app.cart_optimization.automatic_planning import AutomaticPlanningRequest

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/optimize")
def optimize_cart(request: AutomaticPlanningRequest, http_request: Request):
    service = getattr(http_request.app.state, "automatic_cart_planning", None)
    if service is None:
        return {"request_id": request.cart_id, "status": "unresolved", "unresolved_reasons": ("automatic planning is not configured",)}
    return service.plan(request)
