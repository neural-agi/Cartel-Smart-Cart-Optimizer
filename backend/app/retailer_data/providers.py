"""Provider implementations and compatibility bridge for governed ingestion."""

from __future__ import annotations

import json
from typing import Protocol

import httpx

from app.core.config import Settings
from app.data_ingestion import (
    AcquisitionResult,
    CaptureCoverage,
    CaptureType,
    ScrapeJob,
)
from app.data_ingestion.timestamp_integrity import Clock, SystemClock
from app.retailer_data.contracts import (
    AcquisitionMethod,
    EvidenceQuality,
    LocationScope,
    RequestExecutionState,
    RetailerAcquisitionOutcome,
    RetailerAcquisitionRequest,
    RetailerAcquisitionResult,
)
from app.retailer_policy import RetailerPolicyBlocked, ensure_retailer_allowed
from app.scrapers.base.exceptions import (
    ScraperAccessDeniedError,
    ScraperRequestError,
    ScraperUnavailableError,
)
from app.scrapers.blinkit.acquisition import BlinkitAcquisitionAdapter
from app.scrapers.quickcommerce.parser import QuickCommerceSearchParser


class RetailerDataProvider(Protocol):
    provider_id: str
    method: AcquisitionMethod

    async def acquire(self, request: RetailerAcquisitionRequest) -> RetailerAcquisitionResult: ...


def location_from_job(job: ScrapeJob) -> LocationScope:
    """Translate the existing capture context into a required provider scope."""
    return LocationScope(
        country_code=job.capture_context.country_code,
        locality=job.capture_context.location_scope,
        scope_id=job.capture_context.location_scope,
    )


class BlinkitRetailerDataProvider:
    """Wrap the existing Blinkit adapter without changing its network behavior."""

    provider_id = "blinkit-native"
    method = AcquisitionMethod.AUTHORIZED_BROWSER

    def __init__(self, adapter: BlinkitAcquisitionAdapter | None = None) -> None:
        self._adapter = adapter or BlinkitAcquisitionAdapter()

    async def acquire(self, request: RetailerAcquisitionRequest) -> RetailerAcquisitionResult:
        try:
            ensure_retailer_allowed(request.retailer, "retailer acquisition")
        except RetailerPolicyBlocked:
            return _failure(request, RetailerAcquisitionOutcome.POLICY_BLOCKED, "blinkit_commercial_authorization_required", None)
        try:
            acquisition = await self._adapter.acquire_search(
                query=dict(request.job.request_parameters.values).get("query"),
                evaluation_scope=f"{request.location.scope_id}:{request.job.job_id}",
            )
            acquisition = acquisition.model_copy(update={
                "provider_id": self.provider_id,
                "acquisition_method": self.method.value,
                "location_scope": request.location.scope_id,
                "evidence_quality": EvidenceQuality.AUTHORITATIVE.value,
            })
            return RetailerAcquisitionResult(
                outcome=RetailerAcquisitionOutcome.SUCCESS,
                retailer=request.retailer,
                provider_id=self.provider_id,
                method=self.method,
                location=request.location,
                evidence_quality=EvidenceQuality.AUTHORITATIVE,
                acquisition=acquisition,
                observed_at=acquisition.capture_timestamp,
            )
        except ScraperAccessDeniedError as exc:
            if exc.status_code == 429:
                outcome = RetailerAcquisitionOutcome.RATE_LIMITED
            elif exc.status_code == 401:
                outcome = RetailerAcquisitionOutcome.UNAUTHORIZED
            else:
                outcome = RetailerAcquisitionOutcome.ACCESS_DENIED
            return _failure(request, outcome, getattr(exc, "reason_code", "retailer_access_denied"), exc)
        except ScraperUnavailableError as exc:
            return _failure(request, RetailerAcquisitionOutcome.UNAVAILABLE, exc.reason_code, exc)
        except ScraperRequestError as exc:
            outcome = RetailerAcquisitionOutcome.TIMEOUT if exc.status_code == 408 else RetailerAcquisitionOutcome.PROVIDER_ERROR
            return _failure(request, outcome, "retailer_request_failed", exc)


class QuickCommerceRetailerDataProvider:
    """One bounded QuickCommerce search adapter for Blinkit data."""

    provider_id = "quickcommerce"
    method = AcquisitionMethod.AUTHORIZED_THIRD_PARTY

    def __init__(self, settings: Settings, *, clock: Clock | None = None) -> None:
        self._settings = settings
        self._parser = QuickCommerceSearchParser()
        self._clock = clock or SystemClock()

    async def acquire(self, request: RetailerAcquisitionRequest) -> RetailerAcquisitionResult:
        try:
            ensure_retailer_allowed(request.retailer, "QuickCommerce Blinkit acquisition")
        except RetailerPolicyBlocked:
            return _failure(request, RetailerAcquisitionOutcome.POLICY_BLOCKED, "blinkit_commercial_authorization_required", None)
        location = request.location
        query = dict(request.job.request_parameters.values).get("query")
        if location.latitude is None or location.longitude is None:
            return _failure(request, RetailerAcquisitionOutcome.LOCATION_UNAVAILABLE, "coordinates_required", None)
        if not query or not query.strip():
            return _failure(request, RetailerAcquisitionOutcome.INVALID_RESPONSE, "query_required", None)
        base_url = self._settings.quickcommerce_api_base_url.rstrip("/")
        api_key = self._settings.quickcommerce_api_key.get_secret_value()
        if not base_url or not api_key:
            return _failure(request, RetailerAcquisitionOutcome.UNAVAILABLE, "provider_not_configured", None)
        url = f"{base_url}/v1/search"
        params = {"q": query, "lat": location.latitude, "lon": location.longitude, "platform": "BlinkIt"}
        try:
            async with httpx.AsyncClient(timeout=self._settings.quickcommerce_timeout_seconds, follow_redirects=False) as client:
                response = await client.get(url, params=params, headers={"X-API-Key": api_key})
        except httpx.TimeoutException:
            return _failure(request, RetailerAcquisitionOutcome.TIMEOUT, "provider_timeout", None, RequestExecutionState.ATTEMPTED_NO_RESPONSE)
        except httpx.HTTPError:
            return _failure(request, RetailerAcquisitionOutcome.PROVIDER_ERROR, "provider_connection_error", None, RequestExecutionState.ATTEMPTED_NO_RESPONSE)

        outcome = {
            401: (RetailerAcquisitionOutcome.UNAUTHORIZED, "invalid_api_key"),
            402: (RetailerAcquisitionOutcome.UNAVAILABLE, "credits_exhausted"),
            404: (RetailerAcquisitionOutcome.UNAVAILABLE, "item_or_platform_unavailable"),
            422: (RetailerAcquisitionOutcome.INVALID_RESPONSE, "invalid_provider_request"),
            429: (RetailerAcquisitionOutcome.RATE_LIMITED, "provider_rate_limited"),
            500: (RetailerAcquisitionOutcome.PROVIDER_ERROR, "provider_error"),
            502: (RetailerAcquisitionOutcome.PROVIDER_ERROR, "provider_upstream_error"),
            504: (RetailerAcquisitionOutcome.TIMEOUT, "provider_gateway_timeout"),
        }.get(response.status_code)
        if outcome is not None:
            return _failure(request, *outcome, None, RequestExecutionState.HTTP_RESPONSE_RECEIVED)
        if response.status_code < 200 or response.status_code >= 300:
            return _failure(request, RetailerAcquisitionOutcome.PROVIDER_ERROR, "unexpected_provider_status", None, RequestExecutionState.HTTP_RESPONSE_RECEIVED)

        try:
            self._parser.parse(response.content, query=query, source_reference=str(response.url), evaluation_scope=f"{location.scope_id}:{request.job.job_id}")
        except (ValueError, json.JSONDecodeError):
            return _failure(request, RetailerAcquisitionOutcome.INVALID_RESPONSE, "malformed_provider_response", None, RequestExecutionState.HTTP_RESPONSE_RECEIVED)
        coverage = CaptureCoverage(
            evaluation_scope=f"{location.scope_id}:{request.job.job_id}", pages_evaluated=1,
            pagination_complete=True, termination_reason="provider_response_complete",
        )
        acquisition = AcquisitionResult(
            payload=response.content, source_reference=str(response.url),
            content_type=response.headers.get("content-type", "application/json").split(";", 1)[0],
            capture_timestamp=self._clock.now(), evaluation_scope=coverage.evaluation_scope,
            pages_evaluated=1, pagination_complete=True,
            termination_reason=coverage.termination_reason, capture_type=CaptureType.SEARCH_RESULTS,
            capture_coverage=coverage, provider_id=self.provider_id,
            acquisition_method=self.method.value, location_scope=location.scope_id,
            evidence_quality=EvidenceQuality.AUTHORITATIVE.value,
            provider_request_id=self._request_id(response.content),
            location_latitude=location.latitude,
            location_longitude=location.longitude,
        )
        return RetailerAcquisitionResult(
            outcome=RetailerAcquisitionOutcome.SUCCESS, retailer=request.retailer,
            provider_id=self.provider_id, method=self.method, location=location,
            evidence_quality=EvidenceQuality.AUTHORITATIVE, acquisition=acquisition,
            observed_at=acquisition.capture_timestamp,
            request_state=RequestExecutionState.HTTP_RESPONSE_RECEIVED,
        )

    @staticmethod
    def _request_id(payload: bytes) -> str | None:
        try:
            value = json.loads(payload).get("request_id")
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            return None
        return value.strip() if isinstance(value, str) and value.strip() else None


class UnavailableRetailerDataProvider:
    """Explicit provider for environments without authorized retailer access."""

    provider_id = "unconfigured"
    method = AcquisitionMethod.AUTHORIZED_THIRD_PARTY

    async def acquire(self, request: RetailerAcquisitionRequest) -> RetailerAcquisitionResult:
        return _failure(request, RetailerAcquisitionOutcome.UNAVAILABLE, "provider_not_configured", None)


class ProviderAcquisitionAdapter:
    """Adapt the provider result to the existing LocalIngestionWorker boundary."""

    def __init__(self, provider: RetailerDataProvider, *, location: LocationScope | None = None) -> None:
        self._provider = provider
        self._location = location

    async def acquire_for_job(self, *, job: ScrapeJob, query: str | None, evaluation_scope: str) -> AcquisitionResult:
        ensure_retailer_allowed(job.platform, "provider acquisition")
        request = RetailerAcquisitionRequest(
            retailer=job.platform,
            provider_id=self._provider.provider_id,
            method=self._provider.method,
            location=self._location or location_from_job(job),
            job=job,
        )
        result = await self._provider.acquire(request)
        if result.outcome is not RetailerAcquisitionOutcome.SUCCESS or result.acquisition is None:
            from app.scrapers.base.exceptions import ScraperUnavailableError
            raise ScraperUnavailableError(
                result.diagnostic or result.reason_code or result.outcome.value,
                reason_code=result.reason_code or result.outcome.value,
            )
        return result.acquisition


def _failure(request, outcome, reason_code, exc, request_state=RequestExecutionState.NOT_ATTEMPTED):
    return RetailerAcquisitionResult(
        outcome=outcome,
        retailer=request.retailer,
        provider_id=request.provider_id,
        method=request.method,
        location=request.location,
        evidence_quality=EvidenceQuality.INSUFFICIENT,
        reason_code=reason_code,
        diagnostic=None if exc is None else exc.__class__.__name__,
        request_state=request_state,
    )
