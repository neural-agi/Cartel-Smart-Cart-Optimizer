from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.data_ingestion.observation_registry.query import (
    RetailObservationQueryRecord,
    RetailObservationQueryService,
)


router = APIRouter(prefix="/observations", tags=["observations"])


def _query_service(request: Request) -> RetailObservationQueryService:
    service = getattr(request.app.state, "retail_observation_query", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="retail observation query is not configured",
        )
    return service


@router.get("", response_model=tuple[RetailObservationQueryRecord, ...])
async def list_observations(
    request: Request,
    canonical_product_id: str | None = Query(default=None),
    canonical_variant_id: str | None = Query(default=None),
) -> tuple[RetailObservationQueryRecord, ...]:
    return _query_service(request).list_observations(
        canonical_product_id=canonical_product_id,
        canonical_variant_id=canonical_variant_id,
    )


@router.get("/{observation_id}", response_model=RetailObservationQueryRecord)
async def get_observation(
    observation_id: str,
    request: Request,
) -> RetailObservationQueryRecord:
    record = _query_service(request).get_observation(observation_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="observation not found")
    return record
