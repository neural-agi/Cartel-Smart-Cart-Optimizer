from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.data_ingestion.types import ScrapeJob
from app.workers.product_intelligence_runtime import (
    ProductIntelligenceRuntime,
    ProductIntelligenceRuntimeResult,
)


router = APIRouter()


def _runtime(request: Request) -> ProductIntelligenceRuntime:
    runtime = getattr(request.app.state, "product_intelligence_runtime", None)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product Intelligence runtime is not configured",
        )
    return runtime


@router.post(
    "/scrape",
    response_model=ProductIntelligenceRuntimeResult,
    status_code=status.HTTP_200_OK,
    summary="Execute one governed scrape job",
    tags=["scrape"],
)
async def submit_scrape_job(job: ScrapeJob, request: Request):
    """Adapt an HTTP request into the existing ScrapeJob runtime boundary."""

    return await _runtime(request).execute(job)
