from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.services.product_search import ProductSearchRequest, ProductSearchResult


router = APIRouter(prefix="/products", tags=["products"])


@router.get("/search", response_model=ProductSearchResult)
def search_products(
    query: str,
    request: Request,
    limit: int = 20,
) -> ProductSearchResult:
    service = getattr(request.app.state, "product_search", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="product search is not configured",
        )
    try:
        return service.search(ProductSearchRequest(query=query, limit=limit))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
