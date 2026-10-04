import json
from datetime import datetime, timezone

import pytest

from app.core.config import Settings
from app.data_ingestion import CaptureContext, CaptureType, DownstreamMode, Platform, RequestParameters, ScrapeJob
from app.retailer_data.contracts import AcquisitionMethod, LocationScope, RetailerAcquisitionOutcome, RetailerAcquisitionRequest, RequestExecutionState
from app.retailer_data.providers import QuickCommerceRetailerDataProvider
from app.scrapers.quickcommerce.parser import QuickCommerceSearchParser
from app.data_ingestion import RawArtifactReference
from app.scrapers.blinkit.bridge import BlinkitParserBridge
from app.normalization.ingestion import DeterministicIngestionNormalizer
from app.services.product_search import has_supported_retailer_evidence


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        quickcommerce_api_base_url="https://provider.example",
        quickcommerce_api_key="test-only-secret",
        quickcommerce_timeout_seconds=1,
    )


def _request() -> RetailerAcquisitionRequest:
    job = ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "amul taza"),)),
        capture_context=CaptureContext(
            country_code="IN", currency_code="INR", locale="en-IN",
            location_scope="test-location", session_scope="provider-test",
        ),
        parser_policy_version="quickcommerce-parser-v1",
        normalization_policy_version="normalizer-v1",
        downstream_mode=DownstreamMode.PRODUCT_INTELLIGENCE,
        job_contract_version="scrape-job-v1",
    )
    return RetailerAcquisitionRequest(
        retailer=Platform.BLINKIT, provider_id="quickcommerce",
        method=AcquisitionMethod.AUTHORIZED_THIRD_PARTY,
        location=LocationScope(country_code="IN", locality="test", scope_id="test-location", latitude=12.9, longitude=77.6),
        job=job,
    )


def test_parser_preserves_explicit_fields_and_missing_identity_fields() -> None:
    result = QuickCommerceSearchParser().parse(
        json.dumps({"results": [
            {"id": "blinkit-1", "name": "Amul Taaza", "brand": "Amul", "quantity": "1 L", "offer_price": 70, "mrp": 75, "available": True, "deeplink": "https://blinkit.com/prn/amul-taaza/prid/blinkit-1"},
            {"name": "Incomplete listing", "available": None},
        ]}).encode(),
        query="amul taza", source_reference="https://api.quickcommerceapi.com/v1/search", evaluation_scope="scope",
    )
    assert result.products[0].retailer_product_id == "blinkit-1"
    assert result.products[0].brand == "Amul"
    assert result.products[0].availability_status.value == "available"
    assert result.products[1].retailer_product_id is None
    assert result.products[1].quantity is None


def test_real_provider_envelope_replays_through_bridge_and_normalizer() -> None:
    payload = json.dumps({
        "status": "success", "request_id": "provider-request",
        "credits_remaining": 99,
        "data": {
            "query": "amul taza", "platform": "BlinkIt", "lat": 22.4, "lon": 88.4,
            "total_results": 1,
            "products": [{
                "id": "19512", "name": "Taaza Toned Milk", "brand": "Amul",
                "available": True, "inventory": 12, "mrp": 30, "offer_price": 30,
                "quantity": "500 ml", "deeplink": "https://blinkit.com/prn/x/prid/19512",
                "images": ["https://cdn.example/image.jpg"], "store_id": 38720,
                "platform": {"name": "BlinkIt", "open": True}, "rank": 1,
            }],
        },
    }).encode()
    extracted = QuickCommerceSearchParser().parse(
        payload, query="amul taza", source_reference="https://api.quickcommerceapi.com/v1/search", evaluation_scope="scope"
    )
    artifact = RawArtifactReference(
        artifact_id="artifact-qc", job_id="job-qc", attempt_id="attempt-qc",
        platform=Platform.BLINKIT, capture_type=CaptureType.SEARCH_RESULTS,
        content_digest="a" * 64, storage_reference="storage-qc", content_type="application/json",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_reference="https://api.quickcommerceapi.com/v1/search",
        provider_id="quickcommerce", acquisition_method="authorized_third_party",
        location_scope="test-location", evidence_quality="authoritative",
        provider_request_id="provider-request", location_latitude=22.4, location_longitude=88.4,
    )
    batch = BlinkitParserBridge().build_batch(extracted, artifact)
    observations = DeterministicIngestionNormalizer().normalize(batch, currency_code="INR")
    assert observations[0].platform_identifiers
    identifiers = dict(observations[0].platform_identifiers)
    assert identifiers["retailer_product_id"] == "19512"
    assert identifiers["brand"] == "Amul"
    assert identifiers["provider_request_id"] == "provider-request"
    assert identifiers["location_latitude"] == "22.4"
    assert observations[0].normalized_quantity == "500 ml"
    assert observations[0].observed_selling_price is not None
    assert has_supported_retailer_evidence("BLINKIT", observations[0])


class _Response:
    status_code = 200
    content = json.dumps({"results": [{"id": "1", "name": "Amul Taaza", "brand": "Amul", "quantity": "1 L", "available": True, "offer_price": 70}]}).encode()
    headers = {"content-type": "application/json"}
    url = "https://provider.example/v1/search?q=amul+taza"


class _Client:
    def __init__(self, *args, **kwargs):
        self.headers = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, *, params, headers):
        assert url == "https://provider.example/v1/search"
        assert params["platform"] == "BlinkIt"
        assert params["lat"] == 12.9
        assert params["lon"] == 77.6
        assert headers == {"X-API-Key": "test-only-secret"}
        return _Response()


@pytest.mark.asyncio
async def test_provider_maps_success_without_logging_or_leaking_secret(monkeypatch) -> None:
    import app.retailer_data.providers as module
    monkeypatch.setattr(module.httpx, "AsyncClient", _Client)
    result = await QuickCommerceRetailerDataProvider(_settings()).acquire(_request())
    assert result.outcome is RetailerAcquisitionOutcome.SUCCESS
    assert result.acquisition is not None
    assert result.acquisition.provider_id == "quickcommerce"
    assert result.acquisition.location_scope == "test-location"
    assert b"test-only-secret" not in result.acquisition.payload
    assert result.request_state is RequestExecutionState.HTTP_RESPONSE_RECEIVED


@pytest.mark.asyncio
@pytest.mark.parametrize("status, outcome", [
    (401, RetailerAcquisitionOutcome.UNAUTHORIZED),
    (402, RetailerAcquisitionOutcome.UNAVAILABLE),
    (422, RetailerAcquisitionOutcome.INVALID_RESPONSE),
    (429, RetailerAcquisitionOutcome.RATE_LIMITED),
    (500, RetailerAcquisitionOutcome.PROVIDER_ERROR),
    (504, RetailerAcquisitionOutcome.TIMEOUT),
])
async def test_provider_maps_documented_http_failures(monkeypatch, status, outcome) -> None:
    class Response(_Response):
        status_code = status
        content = b"{}"

    class Client(_Client):
        async def get(self, url, *, params, headers):
            return Response()

    import app.retailer_data.providers as module
    monkeypatch.setattr(module.httpx, "AsyncClient", Client)
    result = await QuickCommerceRetailerDataProvider(_settings()).acquire(_request())
    assert result.outcome is outcome
    assert result.acquisition is None
    assert result.request_state is RequestExecutionState.HTTP_RESPONSE_RECEIVED
