from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import get_settings
from app.data_ingestion.enums import JobState
from app.data_ingestion.types import LifecycleTransition, ScrapeAttempt


LIFECYCLE_ROOT_DIRNAME = "data_ingestion"
LIFECYCLE_SUBDIR = "lifecycle"
LIFECYCLE_FILENAME = "job.json"
LIFECYCLE_SCHEMA_VERSION = 1


class LifecycleStoreConflict(ValueError):
    """Raised when persisted lifecycle state conflicts with a new write."""


class LifecycleStoreCorruption(ValueError):
    """Raised when persisted lifecycle state cannot be reconstructed."""


class LifecycleTransitionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence_number: int
    transition_identity: str
    transition: LifecycleTransition


class ScrapeAttemptRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempt_identity: str
    attempt: ScrapeAttempt


class PersistedScrapeJobLifecycle(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = LIFECYCLE_SCHEMA_VERSION
    job_id: str
    transitions: list[LifecycleTransitionRecord] = Field(default_factory=list)
    attempts: list[ScrapeAttemptRecord] = Field(default_factory=list)
    allocated_attempt_numbers: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> "PersistedScrapeJobLifecycle":
        transition_sequences = [item.sequence_number for item in self.transitions]
        if transition_sequences != list(range(1, len(transition_sequences) + 1)):
            raise LifecycleStoreCorruption("persisted lifecycle transition sequence is invalid")
        attempt_ids = [item.attempt_identity for item in self.attempts]
        if len(attempt_ids) != len(set(attempt_ids)):
            raise LifecycleStoreCorruption("persisted lifecycle attempts contain duplicates")
        if self.allocated_attempt_numbers != sorted(set(self.allocated_attempt_numbers)):
            raise LifecycleStoreCorruption("persisted attempt allocation is invalid")
        return self


_VALID_NEXT_STATES: dict[JobState, set[JobState]] = {
    JobState.CREATED: {JobState.QUEUED, JobState.INVALID, JobState.CANCEL_REQUESTED, JobState.EXPIRED},
    JobState.QUEUED: {JobState.DEQUEUED, JobState.CANCEL_REQUESTED, JobState.EXPIRED},
    JobState.DEQUEUED: {JobState.ACQUIRING, JobState.RETRY_SCHEDULED, JobState.CANCEL_REQUESTED, JobState.FAILED, JobState.INVALID, JobState.EXPIRED},
    JobState.ACQUIRING: {JobState.ARTIFACT_CAPTURED, JobState.RETRY_SCHEDULED, JobState.BLOCKED, JobState.FAILED, JobState.CANCEL_REQUESTED, JobState.DEAD_LETTERED},
    JobState.ARTIFACT_CAPTURED: {JobState.PARSING, JobState.CANCEL_REQUESTED, JobState.FAILED, JobState.DEAD_LETTERED},
    JobState.PARSING: {JobState.PARSED, JobState.RETRY_SCHEDULED, JobState.FAILED, JobState.DEAD_LETTERED, JobState.CANCEL_REQUESTED},
    JobState.PARSED: {JobState.NORMALIZING, JobState.CANCEL_REQUESTED, JobState.FAILED, JobState.DEAD_LETTERED},
    JobState.NORMALIZING: {JobState.NORMALIZED, JobState.RETRY_SCHEDULED, JobState.FAILED, JobState.DEAD_LETTERED, JobState.CANCEL_REQUESTED},
    JobState.NORMALIZED: {JobState.REGISTERING_OBSERVATION, JobState.CANCEL_REQUESTED, JobState.FAILED, JobState.DEAD_LETTERED},
    JobState.REGISTERING_OBSERVATION: {JobState.REGISTERED, JobState.RETRY_SCHEDULED, JobState.FAILED, JobState.DEAD_LETTERED, JobState.CANCEL_REQUESTED},
    JobState.REGISTERED: {JobState.PUBLISHING_PIPELINE_EVENT, JobState.COMPLETED, JobState.CANCEL_REQUESTED},
    JobState.PUBLISHING_PIPELINE_EVENT: {JobState.COMPLETED, JobState.RETRY_SCHEDULED, JobState.FAILED, JobState.DEAD_LETTERED},
    JobState.RETRY_SCHEDULED: {JobState.QUEUED, JobState.DEAD_LETTERED, JobState.CANCEL_REQUESTED, JobState.EXPIRED},
    JobState.CANCEL_REQUESTED: {JobState.CANCELLED},
    JobState.COMPLETED: set(),
    JobState.CANCELLED: set(),
    JobState.EXPIRED: set(),
    JobState.DEAD_LETTERED: set(),
    JobState.FAILED: set(),
    JobState.BLOCKED: set(),
    JobState.INVALID: set(),
}

_TERMINAL_STATES = {
    JobState.COMPLETED,
    JobState.CANCELLED,
    JobState.EXPIRED,
    JobState.DEAD_LETTERED,
    JobState.FAILED,
    JobState.BLOCKED,
    JobState.INVALID,
}


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _transition_payload(transition: LifecycleTransition) -> dict[str, object]:
    return transition.model_dump(mode="json", exclude={"transition_timestamp"})


def _transition_identity(transition: LifecycleTransition) -> str:
    payload = _transition_payload(transition)
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _attempt_identity(attempt: ScrapeAttempt) -> str:
    return attempt.attempt_id


class FilesystemScrapeJobLifecycleStore:
    """Append-only filesystem lifecycle store for one scrape job."""

    def __init__(self, root_dir: Path | None = None) -> None:
        settings = get_settings()
        self.root_dir = root_dir or (settings.data_dir / LIFECYCLE_ROOT_DIRNAME / LIFECYCLE_SUBDIR)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def append_transition(self, transition: LifecycleTransition) -> LifecycleTransitionRecord:
        record = self._load_or_empty(transition.job_id)
        identity = _transition_identity(transition)
        with self._lock:
            record = self._validate_record(record)
            for existing in record.transitions:
                if existing.transition_identity == identity:
                    if _transition_payload(existing.transition) != _transition_payload(transition):
                        raise LifecycleStoreConflict("conflicting lifecycle transition write")
                    return existing

            self._validate_new_transition(record.transitions, transition)
            persisted = LifecycleTransitionRecord(
                sequence_number=len(record.transitions) + 1,
                transition_identity=identity,
                transition=transition.model_copy(deep=True),
            )
            updated = record.model_copy(
                update={"transitions": [*record.transitions, persisted]},
            )
            self._save(updated)
            return persisted

    def record_attempt(self, attempt: ScrapeAttempt) -> ScrapeAttempt:
        record = self._load_or_empty(attempt.job_id)
        identity = _attempt_identity(attempt)
        with self._lock:
            record = self._validate_record(record)
            for existing in record.attempts:
                if existing.attempt_identity == identity:
                    if existing.attempt != attempt:
                        raise LifecycleStoreConflict("conflicting scrape attempt write")
                    return existing.attempt

            self._validate_attempt(record, attempt)
            persisted = ScrapeAttemptRecord(
                attempt_identity=identity,
                attempt=attempt.model_copy(deep=True),
            )
            updated = record.model_copy(
                update={"attempts": [*record.attempts, persisted]},
            )
            self._save(updated)
            return persisted.attempt

    def allocate_attempt_number(self, job_id: str) -> int:
        record = self._load_or_empty(job_id)
        with self._lock:
            record = self._validate_record(record)
            allocated = set(record.allocated_attempt_numbers)
            allocated.update(item.attempt.attempt_number for item in record.attempts)
            next_number = max(allocated, default=0) + 1
            if next_number > 3:
                raise LifecycleStoreConflict("maximum scrape attempts exhausted")
            updated = record.model_copy(update={
                "allocated_attempt_numbers": [*record.allocated_attempt_numbers, next_number],
            })
            self._save(updated)
            return next_number

    def has_unfinalized_allocation(self, job_id: str) -> bool:
        record = self._load_optional(job_id)
        if record is None:
            return False
        record = self._validate_record(record)
        finalized = {item.attempt.attempt_number for item in record.attempts}
        return any(number not in finalized for number in record.allocated_attempt_numbers)

    def latest_allocated_attempt_number(self, job_id: str) -> int | None:
        record = self._load_optional(job_id)
        if record is None or not record.allocated_attempt_numbers:
            return None
        return record.allocated_attempt_numbers[-1]

    @staticmethod
    def transition_allowed(previous_state: JobState, current_state: JobState) -> bool:
        """Return whether the frozen lifecycle graph permits this edge."""
        return current_state in _VALID_NEXT_STATES[previous_state]

    def get_current_state(self, job_id: str) -> JobState | None:
        record = self._load_optional(job_id)
        if record is None:
            return None
        record = self._validate_record(record)
        if not record.transitions:
            raise LifecycleStoreCorruption("persisted lifecycle contains no transitions")
        return record.transitions[-1].transition.current_state

    def get_transitions(self, job_id: str) -> tuple[LifecycleTransitionRecord, ...]:
        record = self._load_optional(job_id)
        if record is None:
            return tuple()
        record = self._validate_record(record)
        return tuple(record.transitions)

    def get_attempt(self, job_id: str, attempt_id: str) -> ScrapeAttempt | None:
        record = self._load_optional(job_id)
        if record is None:
            return None
        record = self._validate_record(record)
        for existing in record.attempts:
            if existing.attempt.attempt_id == attempt_id:
                return existing.attempt.model_copy(deep=True)
        return None

    def list_attempts(self, job_id: str) -> tuple[ScrapeAttempt, ...]:
        record = self._load_optional(job_id)
        if record is None:
            return tuple()
        record = self._validate_record(record)
        return tuple(item.attempt.model_copy(deep=True) for item in sorted(record.attempts, key=lambda item: item.attempt.attempt_number))

    def _job_path(self, job_id: str) -> Path:
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError("job_id must be non-empty")
        if any(char in job_id for char in ("/", "\\", ":")) or ".." in job_id:
            raise ValueError("job_id is not a valid storage path segment")
        return self.root_dir / job_id / LIFECYCLE_FILENAME

    def _load_optional(self, job_id: str) -> PersistedScrapeJobLifecycle | None:
        path = self._job_path(job_id)
        if not path.exists():
            return None
        return self._read(path)

    def _load_or_empty(self, job_id: str) -> PersistedScrapeJobLifecycle:
        record = self._load_optional(job_id)
        return record if record is not None else PersistedScrapeJobLifecycle(job_id=job_id)

    @staticmethod
    def _validate_record(record: PersistedScrapeJobLifecycle) -> PersistedScrapeJobLifecycle:
        if not record.transitions:
            return record
        if record.transitions[0].transition.current_state is not JobState.CREATED:
            raise LifecycleStoreCorruption("first persisted transition must be CREATED")

        current_state: JobState | None = None
        for index, persisted in enumerate(record.transitions, start=1):
            transition = persisted.transition
            if persisted.sequence_number != index:
                raise LifecycleStoreCorruption("persisted lifecycle sequence is not monotonic")
            if index == 1:
                if transition.previous_state is not None:
                    raise LifecycleStoreCorruption("initial transition must not have a previous state")
                if transition.current_state is not JobState.CREATED:
                    raise LifecycleStoreCorruption("initial transition must be CREATED")
            else:
                if transition.previous_state is not current_state:
                    raise LifecycleStoreCorruption("persisted lifecycle transition chain is inconsistent")
                if current_state in _TERMINAL_STATES:
                    raise LifecycleStoreCorruption("terminal states are immutable")
                expected = _VALID_NEXT_STATES[current_state]
                if transition.current_state not in expected:
                    raise LifecycleStoreCorruption("persisted lifecycle transition violates the state graph")
            current_state = transition.current_state
        return record

    @staticmethod
    def _validate_new_transition(
        transitions: list[LifecycleTransitionRecord],
        transition: LifecycleTransition,
    ) -> None:
        if not transitions:
            if transition.current_state is not JobState.CREATED:
                raise LifecycleStoreConflict("first persisted transition must be CREATED")
            if transition.previous_state is not None:
                raise LifecycleStoreConflict("first persisted transition must not have a previous state")
            return

        current_state = transitions[-1].transition.current_state
        if current_state in _TERMINAL_STATES:
            raise LifecycleStoreConflict("terminal states cannot transition")
        if transition.previous_state is not current_state:
            raise LifecycleStoreConflict("transition previous state does not match current state")
        if transition.current_state not in _VALID_NEXT_STATES[current_state]:
            raise LifecycleStoreConflict("transition violates frozen state graph")

    @staticmethod
    def _validate_attempt(
        record: PersistedScrapeJobLifecycle,
        attempt: ScrapeAttempt,
    ) -> None:
        if attempt.job_id != record.job_id:
            raise LifecycleStoreConflict("attempt belongs to another job")
        if record.attempts and attempt.attempt_number < record.attempts[-1].attempt.attempt_number:
            raise LifecycleStoreConflict("attempt ordering must be monotonic")

    def _save(self, record: PersistedScrapeJobLifecycle) -> None:
        path = self._job_path(record.job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".json.tmp")
        payload = _canonical_json(record.model_dump(mode="json"))
        tmp_path.write_text(payload, encoding="utf-8")
        os.replace(tmp_path, path)

    @staticmethod
    def _read(path: Path) -> PersistedScrapeJobLifecycle:
        try:
            return PersistedScrapeJobLifecycle.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise LifecycleStoreCorruption("persisted lifecycle record is malformed") from exc
