from datetime import datetime, timezone

import pytest

from app.data_ingestion import CaptureContext, CaptureCoverage, CaptureType, DownstreamMode, Platform, RequestParameters, ScrapeJob
from app.data_ingestion.artifact_store import ArtifactPublicationRequest, StorageReference
from app.data_ingestion import JobState
from app.data_ingestion.lifecycle_store import FilesystemScrapeJobLifecycleStore
from app.data_ingestion.enums import FailureCategory
from app.data_ingestion.types import AcquisitionResult
from app.schemas.extraction import RawExtractedProduct, RawExtractionResult
from app.scrapers.blinkit.bridge import BlinkitParserBridge
from app.workers.local_ingestion import LocalIngestionWorker
from app.workers.job_execution_coordinator import JobExecutionCoordinator
from app.workers.product_intelligence_runtime import ProductIntelligenceRuntime


def _job() -> ScrapeJob:
    return ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "milk"),)),
        capture_context=CaptureContext(country_code="IN", currency_code="INR", locale="en-IN", location_scope="blr", session_scope="s"),
        parser_policy_version="p1", normalization_policy_version="n1", downstream_mode=DownstreamMode.NONE, job_contract_version="j1",
    )


def _acquisition() -> AcquisitionResult:
    coverage = CaptureCoverage(evaluation_scope="scope", pages_evaluated=1, pagination_complete=None, termination_reason="unknown")
    return AcquisitionResult(payload=b"html", source_reference="https://blinkit.test/s/?q=milk", content_type="text/html", capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), evaluation_scope="scope", pages_evaluated=1, pagination_complete=None, termination_reason="unknown", capture_type=CaptureType.SEARCH_RESULTS, capture_coverage=coverage)


class FakeAcquisition:
    async def acquire_search(self, *, query: str, evaluation_scope: str) -> AcquisitionResult:
        result = _acquisition()
        return result.model_copy(update={"evaluation_scope": evaluation_scope, "capture_coverage": result.capture_coverage.model_copy(update={"evaluation_scope": evaluation_scope})})


class FakeParser:
    def parse_content(self, payload: bytes, *, query: str | None, source_reference: str) -> RawExtractionResult:
        return RawExtractionResult(platform="blinkit", query=query, source_reference=source_reference, extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc), product_count=1, products=[RawExtractedProduct(source_index=1, product_name="Milk", raw_text="Milk")])


class FakeStore:
    def __init__(self, fail: bool = False) -> None:
        self.requests: list[ArtifactPublicationRequest] = []
        self.fail = fail

    def store(self, request: ArtifactPublicationRequest, payload: bytes) -> StorageReference:
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("storage failed")
        return StorageReference(storage_reference_id="opaque-1", artifact_id=request.artifact_id, store_namespace="test", storage_backend="fake", content_digest=request.content_digest, content_type=request.content_type)


@pytest.mark.asyncio
async def test_worker_publishes_before_bridge_and_returns_result() -> None:
    store = FakeStore()
    worker = LocalIngestionWorker(acquisition=FakeAcquisition(), artifact_store=store, parser=FakeParser(), bridge=BlinkitParserBridge())
    result = await worker.execute(_job())
    assert result.parsed_batch is not None
    assert result.artifact_reference is not None
    assert result.artifact_reference.storage_reference == "opaque-1"
    assert result.attempt.outcome.value == "SUCCEEDED"
    assert len(store.requests) == 1
    assert store.requests[0].content_type == "text/html"


@pytest.mark.asyncio
async def test_storage_failure_prevents_parsing() -> None:
    store = FakeStore(fail=True)
    worker = LocalIngestionWorker(acquisition=FakeAcquisition(), artifact_store=store, parser=FakeParser(), bridge=BlinkitParserBridge())
    result = await worker.execute(_job())
    assert result.parsed_batch is None
    assert result.failed_stage == "artifact_storage"
    assert result.attempt.failure is not None
    assert result.attempt.failure.category is FailureCategory.STORAGE_FAILURE
    assert result.artifact_reference is None


@pytest.mark.asyncio
async def test_worker_persists_lifecycle_transitions_and_attempt(tmp_path) -> None:
    lifecycle_store = FilesystemScrapeJobLifecycleStore(root_dir=tmp_path / "lifecycle")
    worker = LocalIngestionWorker(
        acquisition=FakeAcquisition(),
        artifact_store=FakeStore(),
        parser=FakeParser(),
        bridge=BlinkitParserBridge(),
    )
    coordinator = JobExecutionCoordinator(
        ingestion_worker=worker,
        product_intelligence_runtime=ProductIntelligenceRuntime.__new__(ProductIntelligenceRuntime),
        lifecycle_store=lifecycle_store,
    )

    result = await coordinator.ingestion_worker.execute(_job())
    lifecycle_store.record_attempt(result.attempt)

    assert result.parsed_batch is not None
    assert result.attempt.outcome.value == "SUCCEEDED"
    assert lifecycle_store.get_current_state(_job().job_id) is JobState.PARSED
    assert lifecycle_store.get_attempt(_job().job_id, result.attempt.attempt_id) == result.attempt
    assert tuple(record.transition.current_state for record in lifecycle_store.get_transitions(_job().job_id)) == (
        JobState.CREATED,
        JobState.QUEUED,
        JobState.DEQUEUED,
        JobState.ACQUIRING,
        JobState.ARTIFACT_CAPTURED,
        JobState.PARSING,
        JobState.PARSED,
    )
