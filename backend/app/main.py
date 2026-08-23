from contextlib import asynccontextmanager
from time import monotonic
from uuid import uuid4
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.workers.bootstrap import build_product_intelligence_runtime
from app.workers.product_intelligence_runtime import ProductIntelligenceRuntime
from app.data_ingestion.observation_registry.query import RetailObservationQueryService
from app.services.cart_resolution import CartResolutionService
from app.services.cart_candidate_discovery import CartCandidateDiscoveryService
from app.services.product_search import ProductSearchService
from app.cart_optimization.planning import CartPlanningService
from app.cart_optimization.providers import (
    RegistryCheckoutObservationProvider,
    UnavailableCheckoutObservationProvider,
)
from app.cost_intelligence.observation.capture import CheckoutCaptureRegistrationService
from app.cost_intelligence.observation.checkout_capture import (
    FilesystemCheckoutObservationCorrelationStore,
)
from app.cost_intelligence.observation.capture_contract import JsonCheckoutCaptureParser
from app.cost_intelligence.observation.capture_service import (
    CheckoutCaptureService,
    UnavailableCheckoutCaptureAdapter,
)
from app.data_ingestion.artifact_store import LocalFilesystemArtifactStore


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
    if app_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(app_settings.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-Request-ID"],
        )

    @application.middleware("http")
    async def request_context_middleware(request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Request-ID", "").strip()
        request_id = incoming if 0 < len(incoming) <= 128 and incoming.isprintable() else str(uuid4())
        request.state.request_id = request_id
        started = monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "http_request_failed method=%s path=%s",
                request.method,
                request.url.path,
                extra={"request_id": request_id},
            )
            raise
        duration_ms = round((monotonic() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        logger.info(
            "http_request_completed method=%s path=%s status=%s duration_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )
        return response
    application.include_router(health_router, tags=["health"])
    application.include_router(api_router, prefix=app_settings.api_v1_prefix)
    configured_runtime = runtime or build_product_intelligence_runtime(app_settings)
    application.state.product_intelligence_runtime = configured_runtime
    application.state.retail_observation_query = RetailObservationQueryService(
        observation_registry=configured_runtime.observation_registry,
        association_registry=configured_runtime.association_registry,
    )
    application.state.cart_resolution = CartResolutionService(
        catalog=configured_runtime.catalog,
        association_registry=configured_runtime.association_registry,
        observation_registry=configured_runtime.observation_registry,
    )
    application.state.cart_candidate_discovery = CartCandidateDiscoveryService(
        catalog=configured_runtime.catalog,
        association_registry=configured_runtime.association_registry,
        observation_registry=configured_runtime.observation_registry,
    )
    application.state.product_search = ProductSearchService(
        catalog=configured_runtime.catalog,
        association_registry=configured_runtime.association_registry,
        observation_registry=configured_runtime.observation_registry,
    )
    checkout_store = FilesystemCheckoutObservationCorrelationStore(
        app_settings.data_dir / "cost_intelligence" / "checkout_captures"
    )
    application.state.checkout_observation_correlation_store = checkout_store
    application.state.checkout_capture_registration = CheckoutCaptureRegistrationService(
        checkout_store
    )
    checkout_artifact_store = LocalFilesystemArtifactStore(
        root=app_settings.raw_data_dir,
        store_namespace="checkout",
    )
    application.state.checkout_artifact_store = checkout_artifact_store
    application.state.checkout_capture = CheckoutCaptureService(
        adapter=UnavailableCheckoutCaptureAdapter(),
        parser=JsonCheckoutCaptureParser(),
        registration=application.state.checkout_capture_registration,
        artifact_store=checkout_artifact_store,
    )
    if app_settings.checkout_observation_provider_mode == "registry":
        checkout_provider = RegistryCheckoutObservationProvider(checkout_store)
    else:
        checkout_provider = UnavailableCheckoutObservationProvider()

    application.state.cart_planning = CartPlanningService(
        discovery=application.state.cart_candidate_discovery,
        checkout_provider=checkout_provider,
        max_cart_items=app_settings.planning_max_cart_items,
        max_candidates_per_item=app_settings.planning_max_candidates_per_item,
        max_combinations=app_settings.planning_max_combinations,
        max_supplied_plans=app_settings.planning_max_supplied_plans,
    )
    return application


app = create_application()
