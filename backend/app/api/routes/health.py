from fastapi import APIRouter, Request

from app.schemas.health import HealthResponse, ReadinessResponse


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


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness check")
async def readiness_check(request: Request) -> ReadinessResponse:
    settings = request.app.state.settings
    checks = {
        "product_intelligence_runtime": "ready" if hasattr(request.app.state, "product_intelligence_runtime") else "missing",
        "cart_planning": "ready" if hasattr(request.app.state, "cart_planning") else "missing",
        "product_search": "ready" if hasattr(request.app.state, "product_search") else "missing",
        "data_directory": "ready" if settings.data_dir.is_dir() else "missing",
        "checkout_capture": "configured" if hasattr(request.app.state, "checkout_capture") else "missing",
    }
    status = "ready" if all(value != "missing" for value in checks.values()) else "not_ready"
    return ReadinessResponse(
        status=status,
        service=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
        checks=checks,
    )
