from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.data_ingestion.observation_registry.comparison import (
    RetailPriceComparisonQueryService,
    RetailPriceComparisonResult,
)


router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.get(
    "/variants/{canonical_variant_id}/displayed-price",
    response_model=RetailPriceComparisonResult,
)
async def compare_variant_displayed_price(
    canonical_variant_id: str,
    request: Request,
) -> RetailPriceComparisonResult:
    observation_query = getattr(request.app.state, "retail_observation_query", None)
    if observation_query is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="retail observation query is not configured",
        )
    return RetailPriceComparisonQueryService(observation_query).compare(
        canonical_variant_id
    )
