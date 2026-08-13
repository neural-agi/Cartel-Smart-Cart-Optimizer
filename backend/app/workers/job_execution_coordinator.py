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
        worker_result = await self.ingestion_worker.execute(job)
        if worker_result.parsed_batch is None:
            self._finalize_failure(job, worker_result)
            self.lifecycle_store.record_attempt(worker_result.attempt)
            return ProductIntelligenceRuntimeResult(
                job_id=worker_result.job_id,
                status="ingestion_failed",
                worker_result=worker_result,
                rationale=(worker_result.failed_stage or "ingestion failed",),
            )

        self.record_transition(job, JobState.PARSED, JobState.NORMALIZING, "normalization started", attempt_number=1)
        result = await self.product_intelligence_runtime.execute_worker_result(job, worker_result, self.record_transition)
        if result.status == "completed":
            self.record_transition(job, JobState.PUBLISHING_PIPELINE_EVENT, JobState.COMPLETED, "pipeline completed", attempt_number=1)
            final_attempt = worker_result.attempt
        else:
            self._finalize_failure(job, worker_result)
            failure = JobFailure(
                category=FailureCategory.PIPELINE_PUBLICATION_FAILURE,
                message="downstream execution failed",
                artifact_reference=worker_result.artifact_reference,
                attempt_id=worker_result.attempt.attempt_id,
                retryable=True,
            )
            final_attempt = worker_result.attempt.model_copy(update={
                "outcome": AttemptOutcome.FAILED,
                "failure": failure,
                "finished_at": datetime.now(timezone.utc),
            })
        self.lifecycle_store.record_attempt(final_attempt)
        return result

    def _finalize_failure(self, job: ScrapeJob, worker_result: IngestionWorkerResult) -> None:
        current = self.lifecycle_store.get_current_state(job.job_id)
        if current is None or current in {
            JobState.COMPLETED, JobState.CANCELLED, JobState.EXPIRED,
            JobState.DEAD_LETTERED, JobState.FAILED, JobState.BLOCKED, JobState.INVALID,
        }:
            return
        failure = worker_result.attempt.failure
        if failure is None:
            failure = JobFailure(
                category=FailureCategory.PIPELINE_PUBLICATION_FAILURE,
                message="downstream execution failed",
                artifact_reference=worker_result.artifact_reference,
                attempt_id=worker_result.attempt.attempt_id,
                retryable=True,
            )
        self.record_transition(
            job, current, JobState.FAILED, "execution failed",
            attempt_number=worker_result.attempt.attempt_number, failure=failure,
        )
