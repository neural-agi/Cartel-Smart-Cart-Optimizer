"""Immutable contracts for scrape-job ingestion."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.data_ingestion.enums import (
    AttemptOutcome,
    CaptureType,
    DownstreamMode,
    FailureCategory,
    JobState,
    Platform,
)


def _non_empty(value: str) -> str:
    if not value.strip():
        raise ValueError("value must be non-empty")
    return value


def _canonical_pairs(value: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    keys = [key for key, _ in value]
    if any(not key.strip() for key in keys):
        raise ValueError("parameter keys must be non-empty")
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate parameter keys are invalid")
    if value != tuple(sorted(value, key=lambda item: item[0])):
        raise ValueError("parameter pairs must be in canonical key order")
    return value


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class CaptureContext(_FrozenContract):
    country_code: str
    currency_code: str
    locale: str
    location_scope: str
    session_scope: str
    additional_parameters: tuple[tuple[str, str], ...] = Field(default_factory=tuple)

    _validate_strings = field_validator(
        "country_code", "currency_code", "locale", "location_scope", "session_scope"
    )(_non_empty)

    @field_validator("additional_parameters")
    @classmethod
    def _validate_parameters(cls, value: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
        return _canonical_pairs(value)


class RequestParameters(_FrozenContract):
    values: tuple[tuple[str, str], ...]

    @field_validator("values")
    @classmethod
    def _validate_values(cls, value: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
        return _canonical_pairs(value)


class RawArtifactReference(_FrozenContract):
    artifact_id: str
    job_id: str
    attempt_id: str
    platform: Platform
    capture_type: CaptureType
    content_digest: str
    storage_reference: str
    content_type: str
    capture_timestamp: datetime
    source_reference: str

    _validate_strings = field_validator(
        "artifact_id",
        "job_id",
        "attempt_id",
        "content_digest",
        "storage_reference",
        "content_type",
        "source_reference",
    )(_non_empty)


class JobFailure(_FrozenContract):
    category: FailureCategory
    message: str
    source_reference: str | None = None
    artifact_reference: RawArtifactReference | None = None
    attempt_id: str
    retryable: bool

    _validate_strings = field_validator("message", "attempt_id")(_non_empty)

    @field_validator("source_reference")
    @classmethod
    def _validate_source(cls, value: str | None) -> str | None:
        return None if value is None else _non_empty(value)

    @model_validator(mode="after")
    def _validate_retryability(self) -> Self:
        retryable_categories = {
            FailureCategory.NETWORK_ERROR,
            FailureCategory.REQUEST_TIMEOUT,
            FailureCategory.BROWSER_TIMEOUT,
            FailureCategory.PARSER_RUNTIME_FAILURE,
            FailureCategory.NORMALIZATION_RUNTIME_FAILURE,
            FailureCategory.STORAGE_FAILURE,
            FailureCategory.OBSERVATION_REGISTRATION_FAILURE,
            FailureCategory.PIPELINE_PUBLICATION_FAILURE,
            FailureCategory.WORKER_CRASH,
            FailureCategory.QUEUE_LEASE_EXPIRY,
            FailureCategory.EXPIRED_RUNNING_LEASE,
        }
        if self.retryable != (self.category in retryable_categories):
            raise ValueError("retryable must match failure-category semantics")
        return self


class JobCancellation(_FrozenContract):
    reason: str
    requested_by: str
    requested_at: datetime
    job_id: str

    _validate_strings = field_validator("reason", "requested_by", "job_id")(_non_empty)


class LifecycleTransition(_FrozenContract):
    job_id: str
    previous_state: JobState | None
    current_state: JobState
    reason: str
    attempt_number: int | None = None
    failure: JobFailure | None = None
    cancellation: JobCancellation | None = None
    transition_timestamp: datetime

    _validate_strings = field_validator("job_id", "reason")(_non_empty)

    @field_validator("attempt_number")
    @classmethod
    def _validate_attempt(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("attempt number must be positive")
        return value

    @model_validator(mode="after")
    def _validate_payloads(self) -> Self:
        if self.cancellation is not None and self.current_state not in {
            JobState.CANCEL_REQUESTED,
            JobState.CANCELLED,
        }:
            raise ValueError("cancellation metadata requires a cancellation state")
        if self.failure is not None and self.current_state not in {
            JobState.FAILED,
            JobState.BLOCKED,
            JobState.INVALID,
            JobState.DEAD_LETTERED,
            JobState.EXPIRED,
            JobState.RETRY_SCHEDULED,
        }:
            raise ValueError("failure metadata requires a failure state")
        if self.failure is not None and self.failure.attempt_id and self.attempt_number is None:
            raise ValueError("failure transitions require an attempt number")
        return self


class ScrapeJob(_FrozenContract):
    platform: Platform
    capture_type: CaptureType
    request_parameters: RequestParameters
    capture_context: CaptureContext
    parser_policy_version: str
    normalization_policy_version: str
    downstream_mode: DownstreamMode
    job_contract_version: str

    _validate_versions = field_validator(
        "parser_policy_version", "normalization_policy_version", "job_contract_version"
    )(_non_empty)

    @computed_field
    @property
    def job_id(self) -> str:
        from app.data_ingestion.identity import ScrapeJobIdentityBuilder

        return ScrapeJobIdentityBuilder().job_id(self)


class ScrapeAttempt(_FrozenContract):
    job_id: str
    attempt_number: int
    outcome: AttemptOutcome | None = None
    failure: JobFailure | None = None
    artifact_references: tuple[RawArtifactReference, ...] = Field(default_factory=tuple)
    started_at: datetime
    finished_at: datetime | None = None

    _validate_job_id = field_validator("job_id")(_non_empty)

    @field_validator("attempt_number")
    @classmethod
    def _validate_attempt_number(cls, value: int) -> int:
        if value < 1:
            raise ValueError("attempt number must be 1-based")
        return value

    @field_validator("artifact_references")
    @classmethod
    def _validate_artifact_order(
        cls, value: tuple[RawArtifactReference, ...]
    ) -> tuple[RawArtifactReference, ...]:
        ids = tuple(item.artifact_id for item in value)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("artifact references must be unique and canonically ordered")
        return value

    @model_validator(mode="after")
    def _validate_finalization(self) -> Self:
        if self.outcome is None and self.finished_at is not None:
            raise ValueError("unfinished attempts cannot have a finish timestamp")
        if self.outcome is not None and self.finished_at is None:
            raise ValueError("finalized attempts require a finish timestamp")
        if self.failure is not None and self.outcome not in {
            AttemptOutcome.RETRY_SCHEDULED,
            AttemptOutcome.FAILED,
            AttemptOutcome.BLOCKED,
            AttemptOutcome.INVALID,
            AttemptOutcome.EXPIRED,
            AttemptOutcome.DEAD_LETTERED,
        }:
            raise ValueError("failure requires a failure outcome")
        return self

    @computed_field
    @property
    def attempt_id(self) -> str:
        from app.data_ingestion.identity import ScrapeAttemptIdentityBuilder

        return ScrapeAttemptIdentityBuilder().attempt_id(self.job_id, self.attempt_number)


class ReplayReference(_FrozenContract):
    original_job_id: str
    artifact_reference: RawArtifactReference | None = None
    replay_target: str
    parser_policy_version: str | None = None
    normalization_policy_version: str | None = None
    downstream_mode: DownstreamMode | None = None

    _validate_job_id = field_validator("original_job_id", "replay_target")(_non_empty)

    @field_validator("parser_policy_version", "normalization_policy_version")
    @classmethod
    def _validate_optional_versions(cls, value: str | None) -> str | None:
        return None if value is None else _non_empty(value)

    @model_validator(mode="after")
    def _validate_artifact_job(self) -> Self:
        if (
            self.artifact_reference is not None
            and self.artifact_reference.job_id != self.original_job_id
        ):
            raise ValueError("artifact reference must belong to the original job")
        return self

    @computed_field
    @property
    def replay_id(self) -> str:
        from app.data_ingestion.identity import ReplayReferenceIdentityBuilder

        return ReplayReferenceIdentityBuilder().replay_id(self)
