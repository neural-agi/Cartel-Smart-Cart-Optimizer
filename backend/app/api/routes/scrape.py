from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.data_ingestion.types import ScrapeJob
from app.workers.background_jobs import DurableJobStore
from app.workers.product_intelligence_runtime import (
    ProductIntelligenceRuntime,
    ProductIntelligenceRuntimeResult,
)


router = APIRouter()


class BackgroundJobResponse(BaseModel):
    id: UUID
    status: str
    created_at: str


def _job_store(request: Request) -> DurableJobStore:
    store = getattr(request.app.state, "background_job_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Background job runtime is not configured")
    return store


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


@router.post("/scrape/async", response_model=BackgroundJobResponse, status_code=202,
             summary="Queue one governed scrape job", tags=["scrape"])
async def queue_scrape_job(job: ScrapeJob, request: Request,
                           idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if idempotency_key is not None and (not idempotency_key.strip() or len(idempotency_key) > 128):
        raise HTTPException(status_code=422, detail="Idempotency-Key is invalid")
    owner_reference = str(getattr(request.state, "user_id", "anonymous"))[:128]
    owner_uuid = None
    try:
        owner_uuid = UUID(owner_reference)
    except ValueError:
        pass
    try:
        record = _job_store(request).create(
            job_type="scrape_ingestion", payload=job.model_dump(mode="json"),
            owner_user_id=owner_uuid, owner_reference=owner_reference,
            idempotency_key=idempotency_key.strip() if idempotency_key else None,
            request_id=getattr(request.state, "request_id", None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return BackgroundJobResponse(id=record.id, status=record.status, created_at=record.created_at.isoformat())


@router.get("/scrape/jobs/{job_id}", response_model=BackgroundJobResponse,
            summary="Read queued scrape job status", tags=["scrape"])
async def get_scrape_job(job_id: UUID, request: Request):
    record = _job_store(request).get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    requester = str(getattr(request.state, "user_id", "anonymous"))
    if record.owner_reference and record.owner_reference != requester:
        raise HTTPException(status_code=404, detail="Job not found")
    return BackgroundJobResponse(id=record.id, status=record.status, created_at=record.created_at.isoformat())
