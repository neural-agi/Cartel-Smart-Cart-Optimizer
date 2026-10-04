from contextlib import asynccontextmanager
from time import monotonic
from uuid import uuid4
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.responses import JSONResponse
import re
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import RateLimitBackendUnavailable, RedisRateLimiter
from app.core.metrics import metrics, normalized_route
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
    ProductionCheckoutObservationProvider,
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
from app.db.session import dispose_engines, get_engine, get_session_factory
from app.workers.background_jobs import DurableJobStore
from app.auth.email_delivery import FileEmailDelivery, SmtpEmailDelivery
from app.auth.email_delivery import EmailDelivery
from app.auth.service import resolve_session, require_csrf, AuthFailure
from sqlalchemy.exc import SQLAlchemyError
from app.api.v2.router import router as v2_router


logger = get_logger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = getattr(app.state, "settings", None) or get_settings()
    configure_logging(log_level=settings.log_level, json_logs=settings.log_json)
    app.state.settings = settings
    app.state.background_job_store = DurableJobStore(get_session_factory(settings), settings)

    if settings.database_required:
        try:
            with get_engine(settings).connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            logger.critical("database_startup_check_failed", extra={"component": "database"})
            raise
    if settings.app_env == "production":
        try:
            await app.state.rate_limiter.ping()
        except RateLimitBackendUnavailable:
            logger.critical("rate_limit_backend_startup_check_failed", extra={"component": "rate_limiter"})
            raise RuntimeError("Redis rate-limit backend is unavailable")

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
        await app.state.rate_limiter.close()
        dispose_engines()
        logger.info("Application shutdown complete: app=%s", settings.app_name)


def create_application(
    settings: Settings | None = None,
    runtime: ProductIntelligenceRuntime | None = None,
    email_delivery: EmailDelivery | None = None,
    rate_limiter: RedisRateLimiter | None = None,
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
    application.state.settings = app_settings
    application.state.background_job_store = DurableJobStore(get_session_factory(app_settings), app_settings)

    @application.exception_handler(RequestValidationError)
    async def sanitized_validation_error(request: Request, exc: RequestValidationError):
        errors = [
            {key: error[key] for key in ("loc", "msg", "type") if key in error}
            for error in exc.errors()
        ]
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=422,
            content={"detail": errors, "request_id": request_id},
            headers={REQUEST_ID_HEADER: request_id} if request_id else None,
        )

    @application.exception_handler(SQLAlchemyError)
    async def database_unavailable(request: Request, exc: SQLAlchemyError):
        logger.error("identity_or_application_database_unavailable", extra={"request_id": getattr(request.state, "request_id", None)})
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=503,
            content={"detail": {"code": "database_unavailable", "request_id": request_id}},
            headers={REQUEST_ID_HEADER: request_id} if request_id else None,
        )

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "unhandled_request_exception",
            extra={"request_id": request_id, "component": "http"},
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "internal_error",
                    "message": "Cartel could not complete the request.",
                    "request_id": request_id,
                }
            },
            headers={REQUEST_ID_HEADER: request_id} if request_id else None,
        )
    if app_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(app_settings.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "X-Request-ID", "Idempotency-Key"],
        )

    @application.middleware("http")
    async def request_context_middleware(request: Request, call_next) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "").strip()
        request_id = incoming if _SAFE_REQUEST_ID.fullmatch(incoming) else str(uuid4())
        request.state.request_id = request_id
        request.state.user_id = "anonymous"
        request.state.authenticated = False
        auth_path = request.url.path.startswith("/api/v2/auth/")
        oauth_path = auth_path and (request.url.path.endswith("/start") or request.url.path.endswith("/callback"))
        if auth_path and app_settings.auth_required and (request.method == "POST" or oauth_path):
            limiter = getattr(application.state, "rate_limiter", None)
            client = request.client.host if request.client else "unknown"
            try:
                decision = await limiter.allow(
                    category="auth",
                    identity=client,
                    path=request.url.path,
                    limit=app_settings.auth_rate_limit_requests,
                    window_seconds=app_settings.rate_limit_window_seconds,
                )
            except RateLimitBackendUnavailable:
                metrics.inc("cartel_rate_limit_requests_total", category="auth", outcome="redis_unavailable", route=normalized_route(request.url.path))
                logger.error("rate_limit_backend_unavailable", extra={"request_id": request_id, "component": "rate_limiter"})
                return JSONResponse(status_code=503, content={"error": {"code": "rate_limit_unavailable", "message": "Cartel cannot safely process this request right now.", "request_id": request_id}}, headers={REQUEST_ID_HEADER: request_id})
            if not decision.allowed:
                metrics.inc("cartel_rate_limit_requests_total", category="auth", outcome="limited", route=normalized_route(request.url.path))
                logger.info("request_rate_limited", extra={"request_id": request_id, "component": "rate_limiter", "http_method": request.method, "http_path": request.url.path, "status_code": 429})
                response = JSONResponse(
                    status_code=429,
                    content={"detail": {"code": "rate_limited"}},
                    headers={"Retry-After": str(app_settings.rate_limit_window_seconds), REQUEST_ID_HEADER: request_id},
                )
                return response
        protected = request.url.path.startswith(f"{app_settings.api_v1_prefix}/") and not request.url.path.endswith("/health") and not request.url.path.endswith("/ready")
        if protected and app_settings.auth_required:
            consumer_paths = {
                f"{app_settings.api_v1_prefix}/products/search",
                f"{app_settings.api_v1_prefix}/cart/resolve",
                f"{app_settings.api_v1_prefix}/cart/candidates",
                f"{app_settings.api_v1_prefix}/cart/plan",
            }
            authorization = request.headers.get("Authorization", "")
            cookie_token = request.cookies.get("cartel_session", "")
            try:
                if authorization:
                    request.state.user_id = authenticate_bearer(authorization, app_settings)
                    request.state.authenticated = True
                    request.state.auth_method = "operator_bearer"
                elif request.url.path in consumer_paths and cookie_token:
                    with application.state.db_session_factory() as db:
                        resolved = resolve_session(db, cookie_token, app_settings.auth_idle_days)
                        if resolved is None:
                            raise AuthenticationError("consumer session is invalid")
                        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                            origin = request.headers.get("Origin")
                            expected = urlsplit(app_settings.public_origin)
                            supplied = urlsplit(origin or "")
                            if (supplied.scheme, supplied.netloc) != (expected.scheme, expected.netloc):
                                return JSONResponse(status_code=403, content={"detail": {"code": "origin_rejected", "request_id": request_id}}, headers={REQUEST_ID_HEADER: request_id})
                            try:
                                require_csrf(resolved[0], request.headers.get("X-CSRF-Token"))
                            except AuthFailure:
                                return JSONResponse(status_code=403, content={"detail": {"code": "csrf_failed", "request_id": request_id}}, headers={REQUEST_ID_HEADER: request_id})
                        request.state.user_id = str(resolved[1].id)
                        request.state.authenticated = True
                        request.state.auth_method = "consumer_session"
                elif cookie_token and request.url.path not in consumer_paths:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": {"code": "operator_authentication_required", "request_id": request_id}},
                        headers={REQUEST_ID_HEADER: request_id},
                    )
                elif request.url.path not in consumer_paths:
                    request.state.user_id = authenticate_bearer(authorization, app_settings)
                    request.state.authenticated = True
                    request.state.auth_method = "operator_bearer"
                else:
                    raise AuthenticationError("consumer authentication is required")
            except SQLAlchemyError:
                return JSONResponse(status_code=503, content={"detail": {"code": "identity_store_unavailable", "request_id": request_id}}, headers={REQUEST_ID_HEADER: request_id})
            except AuthenticationError as exc:
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "authentication_required", "message": str(exc), "request_id": request_id}},
                    headers={"WWW-Authenticate": "Bearer", REQUEST_ID_HEADER: request_id},
                )
        limiter = getattr(application.state, "rate_limiter", None)
        if protected and app_settings.auth_required and limiter is not None:
            identity = request.state.user_id if request.state.authenticated else (request.client.host if request.client else "unknown")
            try:
                decision = await limiter.allow(
                    category="api",
                    identity=identity,
                    path=request.url.path,
                    limit=app_settings.rate_limit_requests,
                    window_seconds=app_settings.rate_limit_window_seconds,
                )
            except RateLimitBackendUnavailable:
                metrics.inc("cartel_rate_limit_requests_total", category="api", outcome="redis_unavailable", route=normalized_route(request.url.path))
                logger.error("rate_limit_backend_unavailable", extra={"request_id": request_id, "component": "rate_limiter"})
                return JSONResponse(status_code=503, content={"error": {"code": "rate_limit_unavailable", "message": "Cartel cannot safely process this request right now.", "request_id": request_id}}, headers={REQUEST_ID_HEADER: request_id})
            if not decision.allowed:
                metrics.inc("cartel_rate_limit_requests_total", category="api", outcome="limited", route=normalized_route(request.url.path))
                logger.info("request_rate_limited", extra={"request_id": request_id, "component": "rate_limiter", "http_method": request.method, "http_path": request.url.path, "status_code": 429})
                return JSONResponse(
                    status_code=429,
                    content={"error": {"code": "rate_limited", "message": "request rate limit exceeded", "request_id": request_id}},
                    headers={"Retry-After": str(app_settings.rate_limit_window_seconds), REQUEST_ID_HEADER: request_id},
                )
        started = monotonic()
        try:
            response = await call_next(request)
        except Exception:
            metrics.inc("cartel_http_requests_total", method=request.method, route=normalized_route(request.url.path), status_class="5xx", outcome="exception")
            logger.exception("http_request_failed", extra={
                "request_id": request_id, "component": "http",
                "http_method": request.method, "http_path": normalized_route(request.url.path),
            })
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": {
                        "code": "internal_error",
                        "message": "Cartel could not complete the request.",
                        "request_id": request_id,
                    }
                },
                headers={REQUEST_ID_HEADER: request_id},
            )
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            return response
        duration_ms = round((monotonic() - started) * 1000, 2)
        metrics.inc("cartel_http_requests_total", method=request.method, route=normalized_route(request.url.path), status_class=f"{response.status_code // 100}xx")
        metrics.observe("cartel_http_request_duration_ms", duration_ms, method=request.method, route=normalized_route(request.url.path))
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        logger.info(
            "http_request_completed method=%s path=%s status=%s duration_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id, "component": "http",
                "http_method": request.method, "http_path": normalized_route(request.url.path),
                "status_code": response.status_code, "duration_ms": duration_ms,
            },
        )
        return response
    application.include_router(health_router, tags=["health"])
    application.include_router(api_router, prefix=app_settings.api_v1_prefix)
    application.include_router(v2_router, prefix="/api/v2")
    application.state.db_session_factory = get_session_factory(app_settings)
    if email_delivery is not None:
        configured_email_delivery = email_delivery
    elif app_settings.email_delivery_mode == "file":
        configured_email_delivery = FileEmailDelivery(app_settings)
    else:
        configured_email_delivery = SmtpEmailDelivery(app_settings)
    application.state.email_delivery = configured_email_delivery
    application.state.logger = logger
    configured_runtime = runtime or build_product_intelligence_runtime(app_settings)
    application.state.product_intelligence_runtime = configured_runtime
    application.state.rate_limiter = rate_limiter or RedisRateLimiter(
        url=app_settings.redis_url,
        connect_timeout=app_settings.redis_connect_timeout_seconds,
        operation_timeout=app_settings.redis_operation_timeout_seconds,
        max_connections=app_settings.redis_max_connections,
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
    application.state.planning_retailer_provider = retailer_provider
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
    # Consumer optimization must never trigger retailer cart/checkout capture.
    application.state.consumer_automatic_planning = AutomaticCartPlanningService(
        discovery=application.state.cart_candidate_discovery,
        planning=application.state.cart_planning,
        retailer_provider=retailer_provider,
        checkout_group_provider=checkout_group_provider,
        policy_provider=policy_provider,
        plan_id_provider=DeterministicPlanIdProvider(),
        checkout_observation_provider=ProductionCheckoutObservationProvider(checkout_provider),
        cost_intelligence=CostIntelligencePipelineService(),
        checkout_capture=None,
        optimization_policy_version=app_settings.optimization_policy_version,
    )
    return application


app = create_application()
