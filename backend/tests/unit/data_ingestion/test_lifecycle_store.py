from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.data_ingestion import (
    AttemptOutcome,
    CaptureContext,
    CaptureType,
    DownstreamMode,
    FailureCategory,
    FilesystemScrapeJobLifecycleStore,
    JobFailure,
    JobState,
    LifecycleStoreConflict,
    Platform,
    RequestParameters,
    ScrapeAttempt,
    ScrapeJob,
    LifecycleTransition,
)
from app.data_ingestion.lifecycle_store import LifecycleStoreCorruption


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _job() -> ScrapeJob:
    return ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "milk"),)),
        capture_context=CaptureContext(
            country_code="IN",
            currency_code="INR",
            locale="en-IN",
            location_scope="blr-560001",
            session_scope="session-1",
            additional_parameters=(("mode", "local"),),
        ),
        parser_policy_version="parser-v1",
        normalization_policy_version="normalizer-v1",
        downstream_mode=DownstreamMode.PRODUCT_INTELLIGENCE,
        job_contract_version="job-v1",
    )


def _transition(job_id: str, previous_state: JobState | None, current_state: JobState, reason: str, *, seconds: int = 0) -> LifecycleTransition:
    return LifecycleTransition(
        job_id=job_id,
        previous_state=previous_state,
        current_state=current_state,
        reason=reason,
        transition_timestamp=NOW.replace(second=seconds),
    )


def _attempt(job_id: str, attempt_number: int, *, outcome: AttemptOutcome, seconds: int = 0) -> ScrapeAttempt:
    failure = None
    if outcome is AttemptOutcome.FAILED:
        failure = JobFailure(
            category=FailureCategory.NETWORK_ERROR,
            message="network failed",
            attempt_id=f"{job_id}:{attempt_number}",
            retryable=True,
        )
    return ScrapeAttempt(
        job_id=job_id,
        attempt_number=attempt_number,
        outcome=outcome,
        failure=failure,
        started_at=NOW.replace(second=seconds),
        finished_at=NOW.replace(second=seconds + 1),
    )


def test_transition_persistence_and_current_state(tmp_path) -> None:
    store = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    job = _job()
    created = _transition(job.job_id, None, JobState.CREATED, "job accepted")
    queued = _transition(job.job_id, JobState.CREATED, JobState.QUEUED, "job queued", seconds=1)
    dequeued = _transition(job.job_id, JobState.QUEUED, JobState.DEQUEUED, "worker leased job", seconds=2)

    first = store.append_transition(created)
    second = store.append_transition(queued)
    third = store.append_transition(dequeued)

    assert first.sequence_number == 1
    assert second.sequence_number == 2
    assert third.sequence_number == 3
    assert store.get_current_state(job.job_id) is JobState.DEQUEUED
    assert tuple(record.transition.current_state for record in store.get_transitions(job.job_id)) == (
        JobState.CREATED,
        JobState.QUEUED,
        JobState.DEQUEUED,
    )


def test_invalid_transition_fails_closed(tmp_path) -> None:
    store = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    job = _job()
    store.append_transition(_transition(job.job_id, None, JobState.CREATED, "job accepted"))
    with pytest.raises(LifecycleStoreConflict):
        store.append_transition(_transition(job.job_id, JobState.CREATED, JobState.PARSING, "invalid"))


def test_sequence_numbers_survive_restart_and_duplicates_are_idempotent(tmp_path) -> None:
    job = _job()
    store_a = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    created = _transition(job.job_id, None, JobState.CREATED, "job accepted")
    queued = _transition(job.job_id, JobState.CREATED, JobState.QUEUED, "job queued", seconds=1)
    store_a.append_transition(created)
    store_a.append_transition(queued)

    store_b = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    duplicate = store_b.append_transition(created)

    assert duplicate.sequence_number == 1
    assert store_b.get_current_state(job.job_id) is JobState.QUEUED
    assert tuple(record.sequence_number for record in store_b.get_transitions(job.job_id)) == (1, 2)


def test_conflicting_transition_payload_is_rejected(tmp_path) -> None:
    store = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    job = _job()
    created = _transition(job.job_id, None, JobState.CREATED, "job accepted")
    store.append_transition(created)

    job_path = tmp_path / job.job_id / "job.json"
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    payload["transitions"][0]["transition"]["reason"] = "tampered"
    job_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    store_b = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    with pytest.raises(LifecycleStoreConflict):
        store_b.append_transition(created)


def test_attempt_persistence_and_restart_lookup(tmp_path) -> None:
    store_a = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    job = _job()
    store_a.append_transition(_transition(job.job_id, None, JobState.CREATED, "job accepted"))
    attempt1 = _attempt(job.job_id, 1, outcome=AttemptOutcome.SUCCEEDED)
    persisted = store_a.record_attempt(attempt1)
    assert persisted == attempt1

    store_b = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    assert store_b.get_attempt(job.job_id, attempt1.attempt_id) == attempt1
    assert store_b.list_attempts(job.job_id) == (attempt1,)


def test_attempt_idempotency_and_conflict(tmp_path) -> None:
    store = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    job = _job()
    store.append_transition(_transition(job.job_id, None, JobState.CREATED, "job accepted"))
    attempt1 = _attempt(job.job_id, 1, outcome=AttemptOutcome.SUCCEEDED)
    store.record_attempt(attempt1)
    assert store.record_attempt(attempt1) == attempt1

    conflicting = _attempt(job.job_id, 1, outcome=AttemptOutcome.FAILED)
    with pytest.raises(LifecycleStoreConflict):
        store.record_attempt(conflicting)


def test_restart_reconstructs_same_state(tmp_path) -> None:
    job = _job()
    store_a = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    store_a.append_transition(_transition(job.job_id, None, JobState.CREATED, "job accepted"))
    store_a.append_transition(_transition(job.job_id, JobState.CREATED, JobState.QUEUED, "job queued", seconds=1))
    store_a.append_transition(_transition(job.job_id, JobState.QUEUED, JobState.DEQUEUED, "worker leased job", seconds=2))
    attempt = _attempt(job.job_id, 1, outcome=AttemptOutcome.FAILED, seconds=3)
    store_a.record_attempt(attempt)

    store_b = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    assert store_b.get_current_state(job.job_id) is JobState.DEQUEUED
    assert store_b.get_attempt(job.job_id, attempt.attempt_id) == attempt
    assert tuple(record.transition.current_state for record in store_b.get_transitions(job.job_id)) == (
        JobState.CREATED,
        JobState.QUEUED,
        JobState.DEQUEUED,
    )


def test_empty_job_lookup_returns_none(tmp_path) -> None:
    store = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    assert store.get_current_state("missing-job") is None
    assert store.get_attempt("missing-job", "missing-job:1") is None
    assert store.get_transitions("missing-job") == tuple()


def test_corrupt_transition_sequence_is_rejected(tmp_path) -> None:
    store = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    job = _job()
    store.append_transition(_transition(job.job_id, None, JobState.CREATED, "job accepted"))
    job_path = tmp_path / job.job_id / "job.json"
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    payload["transitions"][0]["sequence_number"] = 2
    job_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    store_b = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path)
    with pytest.raises(LifecycleStoreCorruption):
        store_b.get_current_state(job.job_id)
