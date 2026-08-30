from contextlib import asynccontextmanager
from time import monotonic
from uuid import uuid4
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import JSONResponse
from time import time
from threading import Lock

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.core.security import AuthenticationError, authenticate_bearer
from app.workers.bootstrap import build_product_intelligence_runtime
from app.workers.product_intelligence_runtime import ProductIntelligenceRuntime
from app.data_ingestion.observation_registry.query import RetailObservationQueryService
from app.services.cart_resolution import CartResolutionService
from app.services.cart_candidate_discovery import CartCandidateDiscoveryService
from app.services.product_search import ProductSearchService
from app.cart_optimization.planning import CartPlanningService
from app.cart_optimization.automatic_planning import (
    AutomaticCartPlanningService,
)
from app.cart_optimization.enums import PlanFeasibility
from app.cart_optimization.providers import (
    ConfiguredCheckoutGroupProvider,
    ConfiguredPlanPolicyProvider,
    ConfiguredRetailerIdentityProvider,
    DeterministicPlanIdProvider,
    RegistryCheckoutObservationProvider,
    UnavailableCheckoutGroupProvider,
    UnavailableCheckoutObservationProvider,
    UnavailablePlanPolicyProvider,
    UnavailableRetailerIdentityProvider,
    parse_mapping,
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
from app.cost_intelligence.pipeline.service import CostIntelligencePipelineService
from app.scrapers.blinkit.checkout_capture import BlinkitCheckoutCaptureAdapter


logger = get_logger(__name__)


class _InMemoryRateLimiter:
    """Process-local guardrail; shared deployments should use a shared limiter."""

    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._entries: dict[tuple[str, str], list[float]] = {}
        self._lock = Lock()

    def allow(self, client: str, path: str) -> bool:
        now = time()
        key = (client, path)
        with self._lock:
            values = [value for value in self._entries.get(key, []) if now - value < self._window_seconds]
            allowed = len(values) < self._limit
            if allowed:
                values.append(now)
            self._entries[key] = values
            return allowed


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
            allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
        )

    @application.middleware("http")
    async def request_context_middleware(request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Request-ID", "").strip()
        request_id = incoming if 0 < len(incoming) <= 128 and incoming.isprintable() else str(uuid4())
        request.state.request_id = request_id
        request.state.user_id = "anonymous"
        protected = request.url.path.startswith(f"{app_settings.api_v1_prefix}/") and not request.url.path.endswith("/health") and not request.url.path.endswith("/ready")
        if protected and app_settings.auth_required:
            try:
                request.state.user_id = authenticate_bearer(
                    request.headers.get("Authorization", ""), app_settings
                )
            except AuthenticationError as exc:
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "authentication_required", "message": str(exc), "request_id": request_id}},
                    headers={"WWW-Authenticate": "Bearer", "X-Request-ID": request_id},
                )
        limiter = getattr(application.state, "rate_limiter", None)
        if protected and limiter is not None and not limiter.allow(request.client.host if request.client else "unknown", request.url.path):
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "request rate limit exceeded", "request_id": request_id}},
                headers={"Retry-After": str(app_settings.rate_limit_window_seconds), "X-Request-ID": request_id},
            )
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
    application.state.rate_limiter = _InMemoryRateLimiter(
        limit=app_settings.rate_limit_requests,
        window_seconds=app_settings.rate_limit_window_seconds,
    )
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
    checkout_capture_adapter = (
        BlinkitCheckoutCaptureAdapter(settings=app_settings)
        if app_settings.checkout_capture_adapter_mode == "blinkit"
        else UnavailableCheckoutCaptureAdapter()
    )
    application.state.checkout_capture = CheckoutCaptureService(
        adapter=checkout_capture_adapter,
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
    retailer_provider = (
        ConfiguredRetailerIdentityProvider(parse_mapping(app_settings.planning_retailer_identity_map))
        if app_settings.planning_retailer_identity_map.strip()
        else UnavailableRetailerIdentityProvider()
    )
    checkout_group_provider = (
        ConfiguredCheckoutGroupProvider(parse_mapping(app_settings.planning_checkout_group_map))
        if app_settings.planning_checkout_group_map.strip()
        else UnavailableCheckoutGroupProvider()
    )
    policy_provider = UnavailablePlanPolicyProvider()
    if (
        app_settings.planning_inconvenience_penalty_units is not None
        and app_settings.planning_retailer_preference_priority is not None
        and app_settings.planning_feasibility is not None
        and app_settings.configured_planning_feasibility_evidence
    ):
        try:
            policy_provider = ConfiguredPlanPolicyProvider(
                inconvenience_penalty_units=app_settings.planning_inconvenience_penalty_units,
                retailer_preference_priority=app_settings.planning_retailer_preference_priority,
                feasibility=PlanFeasibility(app_settings.planning_feasibility),
                evidence=app_settings.configured_planning_feasibility_evidence,
            )
        except ValueError:
            logger.exception("invalid configured planning policy; retaining fail-closed provider")

    application.state.automatic_cart_planning = AutomaticCartPlanningService(
        discovery=application.state.cart_candidate_discovery,
        planning=application.state.cart_planning,
        retailer_provider=retailer_provider,
        checkout_group_provider=checkout_group_provider,
        policy_provider=policy_provider,
        plan_id_provider=DeterministicPlanIdProvider(),
        checkout_observation_provider=checkout_provider,
        cost_intelligence=CostIntelligencePipelineService(),
        checkout_capture=application.state.checkout_capture,
        optimization_policy_version=app_settings.optimization_policy_version,
    )
    return application


app = create_application()
