from datetime import datetime, timezone

from app.data_ingestion import (
    CaptureType,
    CompletenessState,
    NormalizedObservation,
    ObservationCompleteness,
    ObservationFieldReference,
    Platform,
    RawArtifactReference,
)
from app.product_intelligence.evidence import EvidenceFilesystemStore, FilesystemEvidenceRegistry
from app.product_intelligence.ingestion import (
    ProductIntelligenceEvidencePublisher,
    ProductIntelligenceIngestionAdapter,
)
from app.product_intelligence.models import EvidenceReference


def _run(coro):
    import asyncio
    return asyncio.run(coro)


def _observation(*, state: CompletenessState = CompletenessState.COMPLETE) -> NormalizedObservation:
    artifact = RawArtifactReference(
        artifact_id="artifact-1", job_id="job-1", attempt_id="attempt-1", platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS, content_digest="digest", storage_reference="opaque",
        content_type="text/html", capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_reference="https://example.test",
    )
    evidence = EvidenceReference(source_type="raw_artifact", source_id="artifact-1")
    completeness = ObservationCompleteness(
        state=state, scope_reference="scope", basis="basis",
        missing_scope=("remaining-pagination",) if state is CompletenessState.PARTIAL else (),
    )
    return NormalizedObservation(
        platform=Platform.BLINKIT, source_record_id="1", raw_artifact_reference=artifact,
        normalized_name=None if state is CompletenessState.EMPTY else "Milk",
        normalized_quantity="500 ml", platform_identifiers=(("source_index", "1"),),
        observed_price_text="100", evidence_references=(evidence,),
        field_references=(ObservationFieldReference(evidence_reference=evidence, locator="products[1].name"),),
        completeness=completeness, parser_version="blinkit-parser-v1", normalization_version="normalizer-v1",
    )


def test_publish_registers_and_assembles_existing_evidence_registry(tmp_path) -> None:
    observation = _observation()
    handoff = ProductIntelligenceIngestionAdapter().build_handoff(observation)
    publisher = ProductIntelligenceEvidencePublisher(
        FilesystemEvidenceRegistry(store=EvidenceFilesystemStore(tmp_path))
    )
    result = _run(publisher.publish(handoff))

    assert result.observation_id == observation.observation_id
    assert result.evidence_bundle is not None
    assert result.evidence_bundle.source_artifact_reference == "artifact-1"
    assert result.evidence_bundle.parser_version == "blinkit-parser-v1"
    assert result.raw_artifact_reference == observation.raw_artifact_reference
    assert result.evidence_references == observation.evidence_references
    assert result.field_references == observation.field_references
    assert result.normalization_version == "normalizer-v1"
    assert result.completeness == observation.completeness


def test_replay_is_idempotent_and_completeness_is_preserved(tmp_path) -> None:
    observation = _observation(state=CompletenessState.PARTIAL)
    handoff = ProductIntelligenceIngestionAdapter().build_handoff(observation)
    registry = FilesystemEvidenceRegistry(store=EvidenceFilesystemStore(tmp_path))
    publisher = ProductIntelligenceEvidencePublisher(registry)
    first = _run(publisher.publish(handoff))
    second = _run(publisher.publish(handoff))
    assert first == second
    assert first.completeness.state is CompletenessState.PARTIAL


def test_unknown_completeness_is_preserved(tmp_path) -> None:
    observation = _observation(state=CompletenessState.UNKNOWN)
    registry = FilesystemEvidenceRegistry(store=EvidenceFilesystemStore(tmp_path))
    result = _run(ProductIntelligenceEvidencePublisher(registry).publish(
        ProductIntelligenceIngestionAdapter().build_handoff(observation)
    ))
    assert result.completeness.state is CompletenessState.UNKNOWN


def test_empty_observation_publishes_no_fabricated_bundle(tmp_path) -> None:
    observation = _observation(state=CompletenessState.EMPTY)
    registry = FilesystemEvidenceRegistry(store=EvidenceFilesystemStore(tmp_path))
    result = _run(ProductIntelligenceEvidencePublisher(registry).publish(
        ProductIntelligenceIngestionAdapter().build_handoff(observation)
    ))
    assert result.evidence_bundle is None
    assert list(tmp_path.rglob("*")) == []
