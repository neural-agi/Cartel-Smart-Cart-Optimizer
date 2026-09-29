from fastapi import APIRouter, Request, status
from fastapi import HTTPException

from app.cart_optimization.automatic_planning import (
    AutomaticPlanningRequest,
    AutomaticPlanningResult,
    AutomaticPlanningStatus,
)
from app.cart_optimization.providers import PlanningProviderUnavailable
from app.cost_intelligence.observation.capture_service import CheckoutCaptureAdapterUnavailable

router = APIRouter(prefix="/cart", tags=["cart"])

_UNAVAILABLE_REASON_CODES = (
    "retailer_access_denied",
    "browser_timeout",
    "browser_runtime_failure",
    "blinkit_session_unavailable",
    "blinkit_cart_identity_unverified",
)


def _safe_unavailable_code(*reasons: str | None) -> str:
    for reason in reasons:
        if reason in _UNAVAILABLE_REASON_CODES:
            return reason
    tokens = {
        token
        for reason in reasons if reason
        for token in reason.replace(":", " ").replace(";", " ").replace(",", " ").split()
    }
    return next((code for code in _UNAVAILABLE_REASON_CODES if code in tokens), "checkout_capture_unavailable")


@router.post("/optimize", response_model=AutomaticPlanningResult)
def optimize_cart(request: AutomaticPlanningRequest, http_request: Request):
    service = getattr(http_request.app.state, "automatic_cart_planning", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="automatic planning is not configured",
        )
    try:
        result = service.plan(request)
        if result.status is AutomaticPlanningStatus.UNAVAILABLE:
            code = _safe_unavailable_code(*result.unresolved_reasons)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": code, "message": "checkout capture is unavailable"},
            )
        return result
    except PlanningProviderUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="required planning evidence or provider is unavailable",
        ) from exc
    except CheckoutCaptureAdapterUnavailable as exc:
        code = _safe_unavailable_code(getattr(exc, "reason_code", None))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": code, "message": "checkout capture is unavailable"},
        ) from exc
