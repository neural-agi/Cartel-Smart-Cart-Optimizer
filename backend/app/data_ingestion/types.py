"""Immutable contracts for scrape-job ingestion."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator
from app.product_intelligence.models import EvidenceReference

from app.data_ingestion.enums import (
    AttemptOutcome,
    CaptureType,
    CompletenessState,
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


class CaptureCoverage(_FrozenContract):
    evaluation_scope: str
    pages_evaluated: int = Field(ge=1)
    pagination_complete: bool | None
    termination_reason: str
    _validate_strings = field_validator("evaluation_scope", "termination_reason")(_non_empty)


class AcquisitionResult(_FrozenContract):
    payload: bytes
    source_reference: str
    content_type: str
    capture_timestamp: datetime
    evaluation_scope: str
    pages_evaluated: int = Field(ge=1)
    pagination_complete: bool | None
    termination_reason: str
    capture_type: CaptureType
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    capture_coverage: CaptureCoverage

    _validate_strings = field_validator("source_reference", "content_type", "evaluation_scope", "termination_reason")(_non_empty)

    @model_validator(mode="after")
    def _validate_coverage(self) -> Self:
        coverage = self.capture_coverage
        if (coverage.evaluation_scope, coverage.pages_evaluated, coverage.pagination_complete, coverage.termination_reason) != (self.evaluation_scope, self.pages_evaluated, self.pagination_complete, self.termination_reason):
            raise ValueError("capture coverage must match acquisition result metadata")
        if any(not item.strip() for item in self.warnings):
            raise ValueError("warnings must be non-empty")
        return self


class ObservationCompleteness(_FrozenContract):
    state: CompletenessState
    scope_reference: str | None = None
    basis: str
    missing_scope: tuple[str, ...] = Field(default_factory=tuple)
    _validate_basis = field_validator("basis")(_non_empty)

    @field_validator("scope_reference")
    @classmethod
    def _scope(cls, value: str | None) -> str | None:
        return None if value is None else _non_empty(value)

    @field_validator("missing_scope")
    @classmethod
    def _missing(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value) or value != tuple(sorted(value)) or len(value) != len(set(value)):
            raise ValueError("missing scope values must be unique, non-empty, and ordered")
        return value

    @model_validator(mode="after")
    def _state_rules(self) -> Self:
        if self.state in {CompletenessState.COMPLETE, CompletenessState.EMPTY} and (self.scope_reference is None or self.missing_scope):
            raise ValueError("complete and empty states require a complete scope")
        if self.state is CompletenessState.PARTIAL and (self.scope_reference is None or not self.missing_scope):
            raise ValueError("partial state requires missing scope")
        return self


class ObservationFieldReference(_FrozenContract):
    evidence_reference: EvidenceReference
    locator: str
    _validate_locator = field_validator("locator")(_non_empty)


class ParsedRetailObservation(_FrozenContract):
    source_record_id: str
    platform: Platform
    raw_title: str | None = None
    raw_quantity: str | None = None
    raw_category: str | None = None
    platform_identifiers: tuple[tuple[str, str], ...] = Field(default_factory=tuple)
    raw_price_text: str | None = None
    raw_mrp_text: str | None = None
    offer_text: str | None = None
    availability_signal: str | None = None
    field_references: tuple[ObservationFieldReference, ...]
    _validate_record = field_validator("source_record_id")(_non_empty)

    @field_validator("raw_title", "raw_quantity", "raw_category", "raw_price_text", "raw_mrp_text", "offer_text", "availability_signal")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _non_empty(value)

    @field_validator("platform_identifiers")
    @classmethod
    def _identifiers(cls, value: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
        return _canonical_pairs(value)


class ParsedRetailObservationBatch(_FrozenContract):
    raw_artifact_reference: RawArtifactReference
    parser_version: str
    observations: tuple[ParsedRetailObservation, ...]
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    completeness: ObservationCompleteness
    _validate_parser = field_validator("parser_version")(_non_empty)

    @field_validator("warnings")
    @classmethod
    def _warnings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("warnings must be non-empty")
        return value

    @model_validator(mode="after")
    def _records(self) -> Self:
        ids = tuple(item.source_record_id for item in self.observations)
        if len(ids) != len(set(ids)):
            raise ValueError("source record identifiers must be unique")
        if self.completeness.state is CompletenessState.EMPTY and self.observations:
            raise ValueError("empty completeness requires no observations")
        if self.completeness.state is not CompletenessState.EMPTY and not self.observations:
            raise ValueError("empty batches require EMPTY completeness")
        return self

    @property
    def batch_id(self) -> str:
        from app.data_ingestion.identity import ParsedObservationBatchIdentityBuilder
        return ParsedObservationBatchIdentityBuilder().batch_id(self)


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


class IngestionWorkerResult(_FrozenContract):
    job_id: str
    attempt: ScrapeAttempt
    artifact_reference: RawArtifactReference | None = None
    parsed_batch: ParsedRetailObservationBatch | None = None
    failed_stage: str | None = None

    _validate_job = field_validator("job_id")(_non_empty)

    @field_validator("failed_stage")
    @classmethod
    def _validate_stage(cls, value: str | None) -> str | None:
        return None if value is None else _non_empty(value)

    @model_validator(mode="after")
    def _validate_result(self) -> Self:
        if self.attempt.job_id != self.job_id:
            raise ValueError("attempt must belong to result job")
        if self.parsed_batch is not None and self.attempt.outcome is not AttemptOutcome.SUCCEEDED:
            raise ValueError("parsed batch requires successful attempt")
        if self.parsed_batch is not None and self.artifact_reference is None:
            raise ValueError("parsed batch requires artifact reference")
        if self.failed_stage is not None and self.parsed_batch is not None:
            raise ValueError("failed result cannot contain parsed batch")
        if self.failed_stage is None and self.parsed_batch is None and self.attempt.outcome is AttemptOutcome.SUCCEEDED:
            raise ValueError("successful result requires parsed batch")
        return self


class NormalizedObservation(_FrozenContract):
    platform: Platform
    source_record_id: str
    raw_artifact_reference: RawArtifactReference
    normalized_name: str | None = None
    normalized_quantity: str | None = None
    normalized_category: str | None = None
    platform_identifiers: tuple[tuple[str, str], ...] = Field(default_factory=tuple)
    observed_price_text: str | None = None
    observed_mrp_text: str | None = None
    observed_offer_text: str | None = None
    availability_signal: str | None = None
    evidence_references: tuple[EvidenceReference, ...]
    field_references: tuple[ObservationFieldReference, ...]
    completeness: ObservationCompleteness
    parser_version: str
    normalization_version: str

    _validate_source = field_validator("source_record_id", "parser_version", "normalization_version")(_non_empty)

    @field_validator(
        "normalized_name", "normalized_quantity", "normalized_category",
        "observed_price_text", "observed_mrp_text", "observed_offer_text",
        "availability_signal",
    )
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _non_empty(value)

    @field_validator("platform_identifiers")
    @classmethod
    def _identifiers(cls, value: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
        return _canonical_pairs(value)

    @property
    def observation_id(self) -> str:
        from app.data_ingestion.identity import NormalizedObservationIdentityBuilder

        return NormalizedObservationIdentityBuilder().observation_id(self)
