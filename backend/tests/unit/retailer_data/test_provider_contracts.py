from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.data_ingestion import AcquisitionResult, CaptureContext, CaptureCoverage, CaptureType, DownstreamMode, Platform, RequestParameters, ScrapeJob
from app.retailer_data.contracts import AcquisitionMethod, EvidenceQuality, LocationScope, RetailerAcquisitionOutcome, RetailerAcquisitionRequest, RetailerAcquisitionResult
from app.retailer_data.providers import BlinkitRetailerDataProvider, location_from_job
from app.scrapers.base.exceptions import ScraperAccessDeniedError, ScraperRequestError


def job(location: str = "gurugram-1849") -> ScrapeJob:
    return ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "milk"),)),
        capture_context=CaptureContext(
            country_code="IN", currency_code="INR", locale="en-IN",
            location_scope=location, session_scope="authorized-session",
        ),
        parser_policy_version="blinkit-parser-v1",
        normalization_policy_version="normalizer-v1",
        downstream_mode=DownstreamMode.PRODUCT_INTELLIGENCE,
        job_contract_version="scrape-job-v1",
    )


def acquisition() -> AcquisitionResult:
    coverage = CaptureCoverage(
        evaluation_scope="scope", pages_evaluated=1, pagination_complete=True,
        termination_reason="complete",
    )
    return AcquisitionResult(
        payload=b"retailer-evidence", source_reference="https://blinkit.com/s/?q=milk",
        content_type="text/html", capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        evaluation_scope="scope", pages_evaluated=1, pagination_complete=True,
        termination_reason="complete", capture_type=CaptureType.SEARCH_RESULTS,
        capture_coverage=coverage,
    )


class ProviderAdapter:
    async def acquire_search(self, *, query: str | None, evaluation_scope: str):
        return acquisition()


class DeniedAdapter:
    async def acquire_search(self, *, query: str | None, evaluation_scope: str):
        raise ScraperAccessDeniedError("denied", status_code=403)


class RateLimitedAdapter:
    async def acquire_search(self, *, query: str | None, evaluation_scope: str):
        raise ScraperAccessDeniedError("limited", status_code=429)


class UnauthorizedAdapter:
    async def acquire_search(self, *, query: str | None, evaluation_scope: str):
        raise ScraperAccessDeniedError("unauthorized", status_code=401)


def request() -> RetailerAcquisitionRequest:
    current = job()
    return RetailerAcquisitionRequest(
        retailer=Platform.BLINKIT, provider_id="blinkit-native",
        method=AcquisitionMethod.AUTHORIZED_BROWSER,
        location=location_from_job(current), job=current,
    )


@pytest.mark.asyncio
async def test_provider_success_is_location_scoped_and_preserves_metadata() -> None:
    result = await BlinkitRetailerDataProvider(ProviderAdapter()).acquire(request())
    assert result.outcome is RetailerAcquisitionOutcome.SUCCESS
    assert result.location.scope_id == "gurugram-1849"
    assert result.acquisition is not None
    assert result.acquisition.provider_id == "blinkit-native"
    assert result.acquisition.location_scope == "gurugram-1849"
    assert result.evidence_quality is EvidenceQuality.AUTHORITATIVE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adapter", "outcome", "reason"),
    [
        (DeniedAdapter(), RetailerAcquisitionOutcome.ACCESS_DENIED, "retailer_access_denied"),
        (RateLimitedAdapter(), RetailerAcquisitionOutcome.RATE_LIMITED, "retailer_access_denied"),
        (UnauthorizedAdapter(), RetailerAcquisitionOutcome.UNAUTHORIZED, "retailer_access_denied"),
    ],
)
async def test_provider_failures_are_typed_and_carry_no_evidence(adapter, outcome, reason) -> None:
    result = await BlinkitRetailerDataProvider(adapter).acquire(request())
    assert result.outcome is outcome
    assert result.reason_code == reason
    assert result.acquisition is None


def test_location_scope_rejects_global_or_unlocated_observations() -> None:
    with pytest.raises(ValidationError):
        LocationScope(country_code="IN", scope_id="*", locality="Gurugram")
    with pytest.raises(ValidationError):
        LocationScope(country_code="IN", scope_id="unknown")


def test_request_rejects_location_conflation() -> None:
    current = job()
    with pytest.raises(ValidationError):
        RetailerAcquisitionRequest(
            retailer=Platform.BLINKIT, provider_id="blinkit-native",
            method=AcquisitionMethod.AUTHORIZED_BROWSER,
            location=LocationScope(country_code="IN", scope_id="delhi", locality="Delhi"),
            job=current,
        )


def test_failed_result_cannot_carry_evidence() -> None:
    with pytest.raises(ValidationError):
        RetailerAcquisitionResult(
            outcome=RetailerAcquisitionOutcome.INVALID_RESPONSE,
            retailer=Platform.BLINKIT, provider_id="blinkit-native",
            method=AcquisitionMethod.AUTHORIZED_BROWSER,
            location=location_from_job(job()), evidence_quality=EvidenceQuality.INSUFFICIENT,
            acquisition=acquisition(), reason_code="invalid_response",
        )
