from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.v2.dependencies import ConsumerPrincipal, current_consumer
from app.services.product_search import ProductSearchRequest, ProductSearchResult


router = APIRouter(prefix="/products", tags=["consumer-products"])


@router.get("/search", response_model=ProductSearchResult)
def search_consumer_products(
    query: str,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    _principal: ConsumerPrincipal = Depends(current_consumer),
) -> ProductSearchResult:
    """Consumer search over the shared governed catalog and observations."""
    service = getattr(request.app.state, "product_search", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "product_search_unavailable"},
        )
    try:
        return service.search(ProductSearchRequest(query=query, limit=limit))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_product_search", "message": str(exc)},
        ) from exc
