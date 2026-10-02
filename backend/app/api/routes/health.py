from fastapi import APIRouter, Request, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

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
async def readiness_check(request: Request, response: Response) -> ReadinessResponse:
    settings = request.app.state.settings
    checks = {
        "product_intelligence_runtime": "ready" if hasattr(request.app.state, "product_intelligence_runtime") else "missing",
        "cart_planning": "ready" if hasattr(request.app.state, "cart_planning") else "missing",
        "product_search": "ready" if hasattr(request.app.state, "product_search") else "missing",
        "data_directory": "ready" if settings.data_dir.is_dir() else "missing",
        "checkout_capture": (
            "configured" if settings.checkout_capture_adapter_mode != "unavailable" else "unavailable"
        ) if hasattr(request.app.state, "checkout_capture") else "missing",
        "authentication": (
            "ready" if not settings.auth_required or settings.configured_auth_tokens else "missing"
        ),
        "database": "not_required",
        "rate_limiter": "ready" if hasattr(request.app.state, "rate_limiter") else "missing",
    }
    if settings.database_required:
        try:
            with request.app.state.db_session_factory() as db:
                db.execute(text("SELECT 1"))
            checks["database"] = "ready"
        except SQLAlchemyError:
            checks["database"] = "unavailable"
    status = (
        "ready"
        if all(value != "missing" for value in checks.values())
        and checks["database"] != "unavailable"
        else "not_ready"
    )
    if status != "ready":
        response.status_code = 503
    return ReadinessResponse(
        status=status,
        service=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
        checks=checks,
    )
