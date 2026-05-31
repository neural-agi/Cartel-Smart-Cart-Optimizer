from fastapi import APIRouter, Request

from app.schemas.health import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
    )
