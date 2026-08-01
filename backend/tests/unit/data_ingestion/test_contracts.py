from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.data_ingestion import (
    AttemptOutcome,
    CaptureContext,
    CaptureType,
    DownstreamMode,
    FailureCategory,
    JobState,
    LifecycleTransition,
    Platform,
    RawArtifactReference,
    ReplayReference,
    RequestParameters,
    ScrapeAttempt,
    ScrapeJob,
)


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _context() -> CaptureContext:
    return CaptureContext(
        country_code="IN",
        currency_code="INR",
        locale="en-IN",
        location_scope="blr-560001",
        session_scope="session-1",
        additional_parameters=(("mode", "local"),),
    )


def _job() -> ScrapeJob:
    return ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "milk"),)),
        capture_context=_context(),
        parser_policy_version="parser-v1",
        normalization_policy_version="normalizer-v1",
        downstream_mode=DownstreamMode.PRODUCT_INTELLIGENCE,
        job_contract_version="job-v1",
    )


def _artifact(job: ScrapeJob) -> RawArtifactReference:
    return RawArtifactReference(
        artifact_id="artifact-1",
        job_id=job.job_id,
        attempt_id=f"{job.job_id}:1",
        platform=job.platform,
        capture_type=job.capture_type,
        content_digest="digest-1",
        storage_reference="store/artifact-1",
        content_type="text/html",
        capture_timestamp=NOW,
        source_reference="https://example.test/search",
    )


def test_identity_is_deterministic_and_excludes_operational_metadata() -> None:
    first = _job()
    second = _job()
    assert first.job_id == second.job_id
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_models_are_immutable() -> None:
    job = _job()
    with pytest.raises((TypeError, ValidationError)):
        job.platform = Platform.ZEPTO  # type: ignore[misc]


def test_request_parameters_require_canonical_unique_keys() -> None:
    with pytest.raises(ValidationError):
        RequestParameters(values=(("z", "1"), ("a", "2")))
    with pytest.raises(ValidationError):
        RequestParameters(values=(("a", "1"), ("a", "2")))


def test_attempt_identity_is_stable_and_one_based() -> None:
    job = _job()
    attempt = ScrapeAttempt(job_id=job.job_id, attempt_number=1, started_at=NOW)
    assert attempt.attempt_id == f"{job.job_id}:1"
    with pytest.raises(ValidationError):
        ScrapeAttempt(job_id=job.job_id, attempt_number=0, started_at=NOW)


def test_finalized_attempt_requires_outcome_and_finish_time() -> None:
    job = _job()
    with pytest.raises(ValidationError):
        ScrapeAttempt(
            job_id=job.job_id,
            attempt_number=1,
            outcome=AttemptOutcome.SUCCEEDED,
            started_at=NOW,
        )


def test_failure_retryability_is_structurally_validated() -> None:
    from app.data_ingestion import JobFailure

    with pytest.raises(ValidationError):
        JobFailure(
            category=FailureCategory.NETWORK_ERROR,
            message="network failure",
            attempt_id="attempt-1",
            retryable=False,
        )


def test_lifecycle_transition_rejects_inconsistent_payloads() -> None:
    with pytest.raises(ValidationError):
        LifecycleTransition(
            job_id="job-1",
            previous_state=JobState.QUEUED,
            current_state=JobState.PARSING,
            reason="invalid payload",
            cancellation={"reason": "stop", "requested_by": "user", "requested_at": NOW, "job_id": "job-1"},
            transition_timestamp=NOW,
        )


def test_replay_identity_is_deterministic_and_validates_artifact_owner() -> None:
    job = _job()
    artifact = _artifact(job)
    first = ReplayReference(
        original_job_id=job.job_id,
        artifact_reference=artifact,
        replay_target="raw_artifact_to_parser",
        parser_policy_version="parser-v1",
    )
    second = ReplayReference.model_validate(first.model_dump())
    assert first.replay_id == second.replay_id
    with pytest.raises(ValidationError):
        ReplayReference(
            original_job_id="other-job",
            artifact_reference=artifact,
            replay_target="raw_artifact_to_parser",
        )


def test_artifact_references_are_canonically_ordered() -> None:
    job = _job()
    first = _artifact(job)
    second = first.model_copy(update={"artifact_id": "artifact-2"})
    with pytest.raises(ValidationError):
        ScrapeAttempt(
            job_id=job.job_id,
            attempt_number=1,
            artifact_references=(second, first),
            started_at=NOW,
        )
