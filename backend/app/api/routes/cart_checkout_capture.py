from fastapi import APIRouter, HTTPException, Request, status

from app.cost_intelligence.observation.capture_contract import CheckoutCaptureRequest
from app.cost_intelligence.observation.capture_service import CheckoutCaptureAdapterUnavailable
from app.data_ingestion.artifact_store import ArtifactStorageError

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/checkout-capture")
def capture_checkout(request: CheckoutCaptureRequest, http_request: Request):
    service = getattr(http_request.app.state, "checkout_capture", None)
    if service is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="checkout capture is not configured")
    try:
        return service.capture(request)
    except CheckoutCaptureAdapterUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ArtifactStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="checkout artifact publication is unavailable",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
