from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.workers.bootstrap import build_product_intelligence_runtime
from app.workers.product_intelligence_runtime import ProductIntelligenceRuntime
from app.data_ingestion.observation_registry.query import RetailObservationQueryService


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(log_level=settings.log_level, json_logs=settings.log_json)
    app.state.settings = settings

    logger.info(
        "Application startup complete: app=%s env=%s version=%s",
        settings.app_name,
        settings.app_env,
        settings.app_version,
    )
    logger.info(
        "Runtime configuration: app=%s version=%s env=%s debug=%s api_prefix=%s "
        "docs_enabled=%s postgres_host=%s redis_host=%s",
        settings.app_name,
        settings.app_version,
        settings.app_env,
        settings.app_debug,
        settings.api_v1_prefix,
        settings.docs_enabled,
        settings.postgres_host,
        urlsplit(settings.redis_url).hostname,
    )
    try:
        yield
    finally:
        logger.info("Application shutdown complete: app=%s", settings.app_name)


def create_application(
    settings: Settings | None = None,
    runtime: ProductIntelligenceRuntime | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    docs_url = "/docs" if app_settings.docs_enabled else None
    redoc_url = "/redoc" if app_settings.docs_enabled else None
    openapi_url = f"{app_settings.api_v1_prefix}/openapi.json"

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.app_debug,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    application.include_router(health_router, tags=["health"])
    application.include_router(api_router, prefix=app_settings.api_v1_prefix)
    configured_runtime = runtime or build_product_intelligence_runtime(app_settings)
    application.state.product_intelligence_runtime = configured_runtime
    application.state.retail_observation_query = RetailObservationQueryService(
        observation_registry=configured_runtime.observation_registry,
        association_registry=configured_runtime.association_registry,
    )
    return application


app = create_application()
