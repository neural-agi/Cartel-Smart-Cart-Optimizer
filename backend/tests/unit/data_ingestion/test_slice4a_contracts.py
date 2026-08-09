from datetime import datetime, timezone

import hashlib
import pytest
from pydantic import ValidationError

from app.data_ingestion import (
    AcquisitionResult,
    CaptureContext,
    CaptureCoverage,
    CaptureType,
    CompletenessState,
    DownstreamMode,
    ObservationCompleteness,
    Platform,
    RequestParameters,
    ScrapeJob,
)
from app.data_ingestion.artifact_store import ArtifactPublicationRequest
from app.data_ingestion.identity import ArtifactIdentityBuilder


def _job() -> ScrapeJob:
    return ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "milk"),)),
        capture_context=CaptureContext(country_code="IN", currency_code="INR", locale="en-IN", location_scope="blr", session_scope="s"),
        parser_policy_version="p1", normalization_policy_version="n1", downstream_mode=DownstreamMode.NONE, job_contract_version="j1",
    )


def test_publication_request_is_immutable_and_pre_storage_only() -> None:
    request = ArtifactPublicationRequest(artifact_id="a1", content_digest=hashlib.sha256(b"x").hexdigest(), content_type="text/html")
    with pytest.raises((TypeError, ValidationError)):
        request.artifact_id = "changed"  # type: ignore[misc]
    assert "storage_reference" not in request.model_dump()


def test_artifact_identity_is_deterministic_and_uses_frozen_inputs() -> None:
    builder = ArtifactIdentityBuilder()
    first = builder.artifact_id(job_id="job", attempt_id="attempt:1", capture_type="SEARCH_RESULTS", content_digest="digest")
    second = builder.artifact_id(job_id="job", attempt_id="attempt:1", capture_type="SEARCH_RESULTS", content_digest="digest")
    assert first == second
    assert first != builder.artifact_id(job_id="job", attempt_id="attempt:2", capture_type="SEARCH_RESULTS", content_digest="digest")
    assert first != builder.artifact_id(job_id="job", attempt_id="attempt:1", capture_type="CART", content_digest="digest")


def test_acquisition_result_preserves_completeness_metadata() -> None:
    coverage = CaptureCoverage(evaluation_scope="search:milk", pages_evaluated=1, pagination_complete=None, termination_reason="unknown")
    result = AcquisitionResult(
        payload=b"html", source_reference="https://blinkit.test/s/milk", content_type="text/html",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), evaluation_scope="search:milk",
        pages_evaluated=1, pagination_complete=None, termination_reason="unknown", capture_type=CaptureType.SEARCH_RESULTS,
        capture_coverage=coverage,
    )
    assert result.capture_coverage == coverage
    with pytest.raises((TypeError, ValidationError)):
        result.payload = b"changed"  # type: ignore[misc]


def test_completeness_contract_distinguishes_empty_and_partial() -> None:
    empty = ObservationCompleteness(state=CompletenessState.EMPTY, scope_reference="search:milk", basis="no_next_page")
    partial = ObservationCompleteness(state=CompletenessState.PARTIAL, scope_reference="search:milk", basis="page_limit", missing_scope=("remaining-pagination",))
    assert empty.state is CompletenessState.EMPTY
    assert partial.state is CompletenessState.PARTIAL
