"""Capture-timestamp integrity scenarios (1-4, 10-12)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.data_ingestion import (
    AcquisitionResult,
    CaptureCoverage,
    CaptureType,
    FilesystemObservationRegistry,
    InvalidCaptureTimestamp,
    Platform,
    RawArtifactReference,
)
from app.data_ingestion.operator_evidence import load_operator_evidence
from app.data_ingestion.timestamp_integrity import (
    CaptureTimestampRejectionReason,
    normalize_capture_timestamp,
)
from app.retailer_data.contracts import AcquisitionMethod, LocationScope, RetailerAcquisitionRequest
from app.retailer_data.providers import QuickCommerceRetailerDataProvider
from app.services.product_search import has_supported_retailer_evidence, is_explicit_fixture
from tests.unit.timestamp_support import FrozenClock, make_observation, write_stored_observation

FIXTURE_DIR = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "demo_journey"
    / "product_intelligence"
    / "observations"
)


def _artifact(timestamp: datetime, *, artifact_id: str = "artifact-1") -> RawArtifactReference:
    return RawArtifactReference(
        artifact_id=artifact_id,
        job_id="job-1",
        attempt_id="attempt-1",
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        content_digest="a" * 64,
        storage_reference="storage-1",
        content_type="application/json",
        capture_timestamp=timestamp,
        source_reference="https://blinkit.com/s/?q=milk",
    )


# Scenario 1
def test_scenario_1_valid_utc_aware_timestamp_is_preserved() -> None:
    instant = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    artifact = _artifact(instant)

    assert artifact.capture_timestamp == instant
    assert artifact.capture_timestamp.tzinfo is timezone.utc


# Scenario 2
@pytest.mark.parametrize(
    "offset, expected_utc",
    [
        (timedelta(hours=5, minutes=30), datetime(2025, 12, 31, 18, 30, tzinfo=timezone.utc)),
        (timedelta(hours=5, minutes=45), datetime(2025, 12, 31, 18, 15, tzinfo=timezone.utc)),
    ],
)
def test_scenario_2_non_utc_aware_timestamp_normalizes_to_same_instant_utc(
    offset: timedelta, expected_utc: datetime
) -> None:
    local = datetime(2026, 1, 1, 0, 0, tzinfo=timezone(offset))

    artifact = _artifact(local)

    assert artifact.capture_timestamp == expected_utc
    assert artifact.capture_timestamp.utcoffset() == timedelta(0)
    assert artifact.capture_timestamp.tzinfo is timezone.utc
    # Round-trip: normalized values serialize and deserialize identically.
    restored = RawArtifactReference.model_validate(artifact.model_dump(mode="json"))
    assert restored.capture_timestamp == artifact.capture_timestamp
    assert restored.capture_timestamp.tzinfo is timezone.utc


# Scenario 3
def test_scenario_3_naive_timestamp_is_rejected_at_construction_and_read(tmp_path) -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _artifact(datetime(2026, 1, 1, 12, 0))

    with pytest.raises(ValidationError, match="timezone-aware"):
        AcquisitionResult(
            payload=b"{}",
            source_reference="https://blinkit.com/s/?q=milk",
            content_type="application/json",
            capture_timestamp=datetime(2026, 1, 1, 12, 0),
            evaluation_scope="scope",
            pages_evaluated=1,
            pagination_complete=True,
            termination_reason="complete",
            capture_type=CaptureType.SEARCH_RESULTS,
            capture_coverage=CaptureCoverage(
                evaluation_scope="scope",
                pages_evaluated=1,
                pagination_complete=True,
                termination_reason="complete",
            ),
        )

    base = make_observation(
        artifact_id="artifact-naive",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        record_id="record-naive",
        retailer_product_id="naive-1",
    )
    write_stored_observation(
        tmp_path, base, capture_timestamp_value="2026-01-01T00:00:00"
    )
    registry = FilesystemObservationRegistry(
        tmp_path, clock=FrozenClock(datetime(2026, 6, 1, tzinfo=timezone.utc))
    )

    assert registry.get(base.observation_id) is None
    assert registry.rejections[0].reason is CaptureTimestampRejectionReason.naive
    assert registry.rejections[0].artifact_id == "artifact-naive"


# Scenario 4
def test_scenario_4_future_timestamp_is_rejected_and_equal_to_now_is_accepted(tmp_path) -> None:
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    clock = FrozenClock(now)

    assert normalize_capture_timestamp(now, artifact_id="a", clock=clock) == now
    with pytest.raises(InvalidCaptureTimestamp) as raised:
        normalize_capture_timestamp(now + timedelta(seconds=1), artifact_id="a", clock=clock)
    assert raised.value.rejection.reason is CaptureTimestampRejectionReason.future

    base = make_observation(
        artifact_id="artifact-future",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        record_id="record-future",
        retailer_product_id="future-1",
    )
    write_stored_observation(
        tmp_path, base, capture_timestamp_value="2099-01-01T00:00:00+00:00"
    )
    registry = FilesystemObservationRegistry(tmp_path, clock=clock)

    assert registry.get(base.observation_id) is None
    assert registry.rejections[0].reason is CaptureTimestampRejectionReason.future
    assert registry.rejections[0].artifact_id == "artifact-future"

    # The write boundary rejects a future-dated observation before persistence.
    future_observation = make_observation(
        artifact_id="artifact-future-write",
        timestamp=datetime(2099, 1, 1, tzinfo=timezone.utc),
        record_id="record-future-write",
        retailer_product_id="future-write-1",
    )
    with pytest.raises(InvalidCaptureTimestamp) as write_raised:
        registry.register(future_observation)
    assert write_raised.value.rejection.reason is CaptureTimestampRejectionReason.future
    assert registry.get(future_observation.observation_id) is None


# Scenario 10
SYNTHETIC_CAPTURE = b"""
<html><body><div role="button" id="test-retailer-id">
  <a href="/prn/synthetic-test-item/prid/test-retailer-id">Synthetic Test Item</a>
  <span>500 g</span><span>Rs. 42</span><span>ADD</span>
</div></body></html>
"""


def _operator_manifest(tmp_path: Path, *, captured_at: str) -> Path:
    (tmp_path / "capture.html").write_bytes(SYNTHETIC_CAPTURE)
    payload = {
        "schema_version": 1,
        "retailer": "BLINKIT",
        "sanitized_capture": True,
        "source_reference": "https://blinkit.com/s/?q=Synthetic%20Test%20Item",
        "captured_at": captured_at,
        "capture_type": "SEARCH_RESULTS",
        "content_type": "text/html",
        "payload_file": "capture.html",
        "payload_sha256": hashlib.sha256(SYNTHETIC_CAPTURE).hexdigest(),
        "location_scope": "synthetic test locality",
        "query": "Synthetic Test Item",
        "coverage": {
            "evaluation_scope": "synthetic test capture scope",
            "pages_evaluated": 1,
            "pagination_complete": None,
            "termination_reason": "operator supplied single-page capture",
        },
    }
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_scenario_10_operator_evidence_validation_remains_consistent(tmp_path) -> None:
    clock = FrozenClock(datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc))

    valid = load_operator_evidence(
        _operator_manifest(tmp_path, captured_at="2026-09-01T12:00:00+00:00"),
        clock=clock,
    )
    assert valid.manifest.captured_at == clock.now()

    with pytest.raises(ValidationError, match="timezone"):
        load_operator_evidence(
            _operator_manifest(tmp_path, captured_at="2026-09-01T12:00:00"),
            clock=clock,
        )

    with pytest.raises(InvalidCaptureTimestamp) as raised:
        load_operator_evidence(
            _operator_manifest(tmp_path, captured_at="2026-09-02T12:00:00+00:00"),
            clock=clock,
        )
    assert raised.value.rejection.reason is CaptureTimestampRejectionReason.future

    # Normalization is explicit: same instant, canonical UTC tzinfo.
    assert valid.manifest.captured_at.tzinfo is timezone.utc


# Scenario 11
def _settings() -> Settings:
    return Settings(
        _env_file=None,
        quickcommerce_api_base_url="https://provider.example",
        quickcommerce_api_key="test-only-secret",
        quickcommerce_timeout_seconds=1,
    )


def _request() -> RetailerAcquisitionRequest:
    from app.data_ingestion import (
        CaptureContext,
        DownstreamMode,
        RequestParameters,
        ScrapeJob,
    )

    job = ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "amul taza"),)),
        capture_context=CaptureContext(
            country_code="IN",
            currency_code="INR",
            locale="en-IN",
            location_scope="test-location",
            session_scope="provider-test",
        ),
        parser_policy_version="quickcommerce-parser-v1",
        normalization_policy_version="normalizer-v1",
        downstream_mode=DownstreamMode.PRODUCT_INTELLIGENCE,
        job_contract_version="scrape-job-v1",
    )
    return RetailerAcquisitionRequest(
        retailer=Platform.BLINKIT,
        provider_id="quickcommerce",
        method=AcquisitionMethod.AUTHORIZED_THIRD_PARTY,
        location=LocationScope(
            country_code="IN",
            locality="test",
            scope_id="test-location",
            latitude=12.9,
            longitude=77.6,
        ),
        job=job,
    )


class _Response:
    status_code = 200
    content = json.dumps(
        {"results": [{"id": "1", "name": "Amul Taaza", "available": True, "offer_price": 70}]}
    ).encode()
    headers = {"content-type": "application/json"}
    url = "https://provider.example/v1/search?q=amul+taza"


class _Client:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def get(self, url, *, params, headers):
        return _Response()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "clock_instant, expected_utc",
    [
        (
            datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 6, 1, 17, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))),
            datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        ),
    ],
)
async def test_scenario_11_quickcommerce_provider_uses_injected_clock(
    monkeypatch, clock_instant: datetime, expected_utc: datetime
) -> None:
    import app.retailer_data.providers as module

    monkeypatch.setattr(module.httpx, "AsyncClient", _Client)
    provider = QuickCommerceRetailerDataProvider(
        _settings(), clock=FrozenClock(clock_instant)
    )

    result = await provider.acquire(_request())

    assert result.outcome.value == "policy_blocked"
    assert result.acquisition is None


# Scenario 12
def test_scenario_12_demo_fixtures_load_unchanged_and_guards_hold() -> None:
    registry = FilesystemObservationRegistry(
        FIXTURE_DIR, clock=FrozenClock(datetime(2026, 11, 8, tzinfo=timezone.utc))
    )
    observation_id = next(FIXTURE_DIR.glob("*.json")).stem

    observation = registry.get(observation_id)

    assert observation is not None
    assert observation.raw_artifact_reference.capture_timestamp == datetime(
        2026, 1, 1, tzinfo=timezone.utc
    )
    assert is_explicit_fixture(observation) is True
    assert has_supported_retailer_evidence("BLINKIT", observation) is False
    assert registry.rejections == ()
