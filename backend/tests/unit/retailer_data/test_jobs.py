import pytest

from app.data_ingestion.enums import DownstreamMode, Platform
from app.retailer_data.jobs import (
    FilesystemRetailerAcquisitionSubmissionStore,
    RetailerAcquisitionIdempotencyConflict,
    RetailerAcquisitionRequest,
    build_retailer_acquisition_job,
)


def test_retailer_acquisition_job_uses_existing_deterministic_scrape_job_contract():
    request = RetailerAcquisitionRequest(
        provider=Platform.BLINKIT,
        query="milk",
        country_code="IN",
        currency_code="INR",
        locale="en-IN",
        location_scope="operator-location",
        session_scope="operator-session",
        idempotency_key="request-1",
    )
    first = build_retailer_acquisition_job(request)
    second = build_retailer_acquisition_job(request)
    assert first.job_id == second.job_id
    assert first.downstream_mode is DownstreamMode.PRODUCT_INTELLIGENCE
    assert first.request_parameters.values == (
        ("idempotency_key", "request-1"), ("query", "milk"), ("retailer_only", "true")
    )


def test_submission_idempotency_replays_and_rejects_conflicting_payload(tmp_path):
    store = FilesystemRetailerAcquisitionSubmissionStore(tmp_path)
    request = RetailerAcquisitionRequest(
        provider=Platform.BLINKIT,
        query="milk",
        country_code="IN",
        currency_code="INR",
        locale="en-IN",
        location_scope="operator-location",
        session_scope="operator-session",
        idempotency_key="request-1",
    )
    first = store.submit(request)
    replay = store.submit(request.model_copy(deep=True))
    assert replay.job_id == first.job_id

    with pytest.raises(RetailerAcquisitionIdempotencyConflict):
        store.submit(request.model_copy(update={"query": "bread"}))
