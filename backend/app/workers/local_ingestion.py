"""Local single-job ingestion orchestration."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Protocol

from app.data_ingestion import (
    AttemptOutcome,
    IngestionWorkerResult,
    JobFailure,
    JobState,
    RawArtifactReference,
    ScrapeAttempt,
    ScrapeJob,
)
from app.data_ingestion.enums import FailureCategory
from app.data_ingestion.artifact_store import ArtifactStore
from app.data_ingestion.artifact_store import ArtifactPublicationRequest
from app.data_ingestion.identity import ArtifactIdentityBuilder
from app.schemas.extraction import RawExtractionResult
from app.scrapers.blinkit.acquisition import BlinkitAcquisitionAdapter
from app.scrapers.blinkit.bridge import BlinkitParserBridge
from app.scrapers.blinkit.parser import BlinkitProductParser


class AcquisitionBoundary(Protocol):
    async def acquire_search(self, *, query: str, evaluation_scope: str): ...


class ParserBoundary(Protocol):
    def parse_content(self, payload: bytes, *, query: str | None, source_reference: str): ...


class LocalIngestionWorker:
    """Execute one Blinkit search job through the existing immutable boundaries."""

    def __init__(
        self,
        *,
        acquisition: AcquisitionBoundary | None = None,
        artifact_store: ArtifactStore,
        parser: ParserBoundary | None = None,
        bridge: BlinkitParserBridge | None = None,
        lifecycle_reporter=None,
    ) -> None:
        self._acquisition = acquisition or BlinkitAcquisitionAdapter()
        self._artifact_store = artifact_store
        self._parser = parser or BlinkitProductParser()
        self._bridge = bridge or BlinkitParserBridge()
        self._lifecycle_reporter = lifecycle_reporter

    async def execute(self, job: ScrapeJob) -> IngestionWorkerResult:
        attempt_number = 1
        attempt_id = f"{job.job_id}:{attempt_number}"
        started_at = datetime.now(timezone.utc)
        artifact_reference: RawArtifactReference | None = None
        stage = "job_created"

        def report_transition(
            previous_state: JobState | None,
            current_state: JobState,
            reason: str,
            *,
            failure: JobFailure | None = None,
        ) -> None:
            if self._lifecycle_reporter is not None:
                self._lifecycle_reporter(
                    job,
                    previous_state,
                    current_state,
                    reason,
                    attempt_number=attempt_number if current_state is not JobState.CREATED else None,
                    failure=failure,
                    transition_timestamp=started_at,
                )

        try:
            report_transition(None, JobState.CREATED, "job accepted")
            report_transition(JobState.CREATED, JobState.QUEUED, "job queued")
            report_transition(JobState.QUEUED, JobState.DEQUEUED, "worker leased job")
            stage = "acquisition"
            report_transition(JobState.DEQUEUED, JobState.ACQUIRING, "acquisition started")
            query = self._query(job)
            evaluation_scope = self._evaluation_scope(job, query)
            acquisition = await self._acquisition.acquire_search(
                query=query,
                evaluation_scope=evaluation_scope,
            )
            stage = "artifact_storage"
            payload_digest = hashlib.sha256(acquisition.payload).hexdigest()
            artifact_id = ArtifactIdentityBuilder().artifact_id(
                job_id=job.job_id,
                attempt_id=attempt_id,
                capture_type=acquisition.capture_type.value,
                content_digest=payload_digest,
            )
            publication = ArtifactPublicationRequest(
                artifact_id=artifact_id,
                content_digest=payload_digest,
                content_type=acquisition.content_type,
            )
            storage_reference = self._artifact_store.store(publication, acquisition.payload)
            artifact_reference = RawArtifactReference(
                artifact_id=artifact_id,
                job_id=job.job_id,
                attempt_id=attempt_id,
                platform=job.platform,
                capture_type=acquisition.capture_type,
                content_digest=payload_digest,
                storage_reference=storage_reference.storage_reference_id,
                content_type=acquisition.content_type,
                capture_timestamp=acquisition.capture_timestamp,
                source_reference=acquisition.source_reference,
            )
            report_transition(JobState.ACQUIRING, JobState.ARTIFACT_CAPTURED, "artifact captured")
            stage = "parsing"
            report_transition(JobState.ARTIFACT_CAPTURED, JobState.PARSING, "parsing started")
            extraction = self._parser.parse_content(
                acquisition.payload,
                query=query,
                source_reference=acquisition.source_reference,
            )
            extraction = self._complete_extraction(extraction, acquisition)
            batch = self._bridge.build_batch(extraction, artifact_reference)
            report_transition(JobState.PARSING, JobState.PARSED, "parsing completed")
            attempt = ScrapeAttempt(
                job_id=job.job_id,
                attempt_number=attempt_number,
                outcome=AttemptOutcome.SUCCEEDED,
                artifact_references=(artifact_reference,),
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
            return IngestionWorkerResult(
                job_id=job.job_id,
                attempt=attempt,
                artifact_reference=artifact_reference,
                parsed_batch=batch,
            )
        except Exception as exc:
            failure_stage = stage
            category = self._failure_category(stage)
            failure = JobFailure(
                category=category,
                message=f"{stage} failed: {type(exc).__name__}",
                source_reference=artifact_reference.source_reference if artifact_reference else None,
                artifact_reference=artifact_reference,
                attempt_id=attempt_id,
                retryable=category in {
                    FailureCategory.NETWORK_ERROR,
                    FailureCategory.PARSER_RUNTIME_FAILURE,
                    FailureCategory.STORAGE_FAILURE,
                },
            )
            if self._lifecycle_reporter is not None and failure_stage not in {"job_created", "lifecycle_persistence"}:
                previous_state = self._failure_previous_state(failure_stage)
                report_transition(previous_state, JobState.FAILED, f"{failure_stage} failed", failure=failure)
            attempt = ScrapeAttempt(
                job_id=job.job_id,
                attempt_number=attempt_number,
                outcome=AttemptOutcome.FAILED,
                failure=failure,
                artifact_references=(artifact_reference,) if artifact_reference else tuple(),
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
            return IngestionWorkerResult(
                job_id=job.job_id,
                attempt=attempt,
                artifact_reference=artifact_reference,
                failed_stage=stage,
            )

    @staticmethod
    def _query(job: ScrapeJob) -> str:
        values = dict(job.request_parameters.values)
        query = values.get("query")
        if not query:
            raise ValueError("search job requires query request parameter")
        return query

    @staticmethod
    def _evaluation_scope(job: ScrapeJob, query: str) -> str:
        return f"{job.job_id}:search:{query}"

    @staticmethod
    def _complete_extraction(result: RawExtractionResult, acquisition) -> RawExtractionResult:
        return result.model_copy(update={
            "evaluation_scope": acquisition.evaluation_scope,
            "capture_coverage": acquisition.capture_coverage,
            "source_reference": acquisition.source_reference,
            "warnings": acquisition.warnings,
            "pages_evaluated": acquisition.pages_evaluated,
            "pagination_complete": acquisition.pagination_complete,
            "termination_reason": acquisition.termination_reason,
        })

    @staticmethod
    def _failure_category(stage: str) -> FailureCategory:
        return {
            "job_created": FailureCategory.STORAGE_FAILURE,
            "acquisition": FailureCategory.NETWORK_ERROR,
            "artifact_storage": FailureCategory.STORAGE_FAILURE,
            "parsing": FailureCategory.PARSER_RUNTIME_FAILURE,
            "lifecycle_persistence": FailureCategory.STORAGE_FAILURE,
        }[stage]

    @staticmethod
    def _failure_previous_state(stage: str) -> JobState | None:
        return {
            "job_created": None,
            "acquisition": JobState.ACQUIRING,
            "artifact_storage": JobState.ACQUIRING,
            "parsing": JobState.PARSING,
            "lifecycle_persistence": JobState.ACQUIRING,
        }[stage]
