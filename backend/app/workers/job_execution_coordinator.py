from __future__ import annotations

from datetime import datetime, timezone

from app.data_ingestion import (
    IngestionWorkerResult,
    FailureCategory,
    AttemptOutcome,
    JobFailure,
    JobState,
    LifecycleTransition,
    ScrapeAttempt,
    ScrapeJob,
)
from app.data_ingestion.lifecycle_store import FilesystemScrapeJobLifecycleStore
from app.workers.product_intelligence_runtime import ProductIntelligenceRuntime, ProductIntelligenceRuntimeResult


class JobExecutionCoordinator:
    """Single owner of one ScrapeJob lifecycle across all execution stages."""

    def __init__(self, *, ingestion_worker, product_intelligence_runtime: ProductIntelligenceRuntime,
                 lifecycle_store: FilesystemScrapeJobLifecycleStore) -> None:
        self.ingestion_worker = ingestion_worker
        self.product_intelligence_runtime = product_intelligence_runtime
        self.lifecycle_store = lifecycle_store
        self.ingestion_worker._lifecycle_reporter = self.record_transition

    def __getattr__(self, name):
        return getattr(self.product_intelligence_runtime, name)

    def record_transition(
        self, job: ScrapeJob, previous_state: JobState | None, current_state: JobState,
        reason: str, *, attempt_number: int | None = None, failure: JobFailure | None = None,
        transition_timestamp: datetime | None = None,
    ) -> None:
        self.lifecycle_store.append_transition(LifecycleTransition(
            job_id=job.job_id,
            previous_state=previous_state,
            current_state=current_state,
            reason=reason,
            attempt_number=attempt_number,
            failure=failure,
            transition_timestamp=transition_timestamp or datetime.now(timezone.utc),
        ))

    async def execute(self, job: ScrapeJob) -> ProductIntelligenceRuntimeResult:
        attempt_number = self._prepare_attempt(job)
        worker_result = await self.ingestion_worker.execute(job, attempt_number=attempt_number)
        if worker_result.parsed_batch is None:
            final_attempt = self._handle_failure(job, worker_result)
            self.lifecycle_store.record_attempt(final_attempt)
            return ProductIntelligenceRuntimeResult(
                job_id=worker_result.job_id,
                status="ingestion_failed",
                worker_result=worker_result,
                rationale=(worker_result.failed_stage or "ingestion failed",),
            )

        self.record_transition(job, JobState.PARSED, JobState.NORMALIZING, "normalization started", attempt_number=attempt_number)
        result = await self.product_intelligence_runtime.execute_worker_result(job, worker_result, self.record_transition)
        if result.status == "completed":
            self.record_transition(job, JobState.PUBLISHING_PIPELINE_EVENT, JobState.COMPLETED, "pipeline completed", attempt_number=attempt_number)
            final_attempt = worker_result.attempt
        else:
            final_attempt = self._handle_failure(job, worker_result)
        self.lifecycle_store.record_attempt(final_attempt)
        return result

    def _prepare_attempt(self, job: ScrapeJob) -> int:
        current = self.lifecycle_store.get_current_state(job.job_id)
        if current is None:
            self.record_transition(job, None, JobState.CREATED, "job accepted")
            self.record_transition(job, JobState.CREATED, JobState.QUEUED, "job queued")
        elif current in {JobState.COMPLETED, JobState.CANCELLED, JobState.EXPIRED, JobState.DEAD_LETTERED, JobState.FAILED, JobState.BLOCKED, JobState.INVALID}:
            raise ValueError("terminal scrape job cannot execute again")
        elif self.lifecycle_store.has_unfinalized_allocation(job.job_id):
            self._recover_interrupted(job, current)
        attempt_number = self.lifecycle_store.allocate_attempt_number(job.job_id)
        current = self.lifecycle_store.get_current_state(job.job_id)
        if current is JobState.RETRY_SCHEDULED:
            self.record_transition(
                job,
                JobState.RETRY_SCHEDULED,
                JobState.QUEUED,
                "retry became eligible",
                attempt_number=attempt_number,
            )
        self.record_transition(job, JobState.QUEUED, JobState.DEQUEUED, "worker leased job", attempt_number=attempt_number)
        return attempt_number

    def _recover_interrupted(self, job: ScrapeJob, current: JobState) -> None:
        interrupted_number = self.lifecycle_store.latest_allocated_attempt_number(job.job_id) or 1
        if current is JobState.QUEUED:
            self.record_transition(job, JobState.QUEUED, JobState.DEQUEUED, "recovered interrupted lease", attempt_number=interrupted_number)
            current = JobState.DEQUEUED
        failure = JobFailure(
            category=FailureCategory.WORKER_CRASH,
            message="previous attempt was interrupted",
            attempt_id=f"{job.job_id}:{self.lifecycle_store.latest_allocated_attempt_number(job.job_id) or 1}",
            retryable=True,
        )
        can_retry = (
            interrupted_number < 3
            and self.lifecycle_store.transition_allowed(current, JobState.RETRY_SCHEDULED)
        )
        next_state = JobState.RETRY_SCHEDULED if can_retry else JobState.DEAD_LETTERED
        self.record_transition(
            job,
            current,
            next_state,
            "interrupted attempt recovered" if can_retry else "interrupted attempt dead-lettered",
            failure=failure,
            attempt_number=interrupted_number,
        )

    def _handle_failure(self, job: ScrapeJob, worker_result: IngestionWorkerResult) -> ScrapeAttempt:
        current = self.lifecycle_store.get_current_state(job.job_id)
        failure = worker_result.attempt.failure
        if failure is None:
            failure = JobFailure(
                category=FailureCategory.PIPELINE_PUBLICATION_FAILURE,
                message="downstream execution failed",
                artifact_reference=worker_result.artifact_reference,
                attempt_id=worker_result.attempt.attempt_id,
                retryable=True,
            )
        number = worker_result.attempt.attempt_number
        retryable = failure.retryable and number < 3
        next_state = JobState.RETRY_SCHEDULED if retryable else (
            JobState.DEAD_LETTERED if failure.retryable else JobState.FAILED
        )
        self.record_transition(job, current, next_state, "retry scheduled" if retryable else "execution failed", attempt_number=number, failure=failure)
        outcome = (
            AttemptOutcome.RETRY_SCHEDULED
            if retryable
            else (AttemptOutcome.DEAD_LETTERED if failure.retryable else AttemptOutcome.FAILED)
        )
        return worker_result.attempt.model_copy(update={"outcome": outcome, "finished_at": datetime.now(timezone.utc)})
