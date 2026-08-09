from datetime import datetime, timezone

import pytest

from app.data_ingestion import (
    CaptureType,
    CompletenessState,
    NormalizedObservation,
    ObservationCompleteness,
    ObservationFieldReference,
    Platform,
    RawArtifactReference,
)
from app.product_intelligence.ingestion import ProductIntelligenceIngestionAdapter
from app.product_intelligence.models import EvidenceReference


def _observation(*, state: CompletenessState = CompletenessState.COMPLETE, name: str | None = "Milk") -> NormalizedObservation:
    artifact = RawArtifactReference(
        artifact_id="artifact-1", job_id="job-1", attempt_id="attempt-1", platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS, content_digest="digest", storage_reference="opaque",
        content_type="text/html", capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_reference="https://example.test",
    )
    evidence = EvidenceReference(source_type="raw_artifact", source_id="artifact-1")
    completeness = ObservationCompleteness(
        state=state,
        scope_reference="scope",
        basis="complete" if state is not CompletenessState.EMPTY else "empty",
        missing_scope=("remaining-pagination",) if state is CompletenessState.PARTIAL else (),
    )
    return NormalizedObservation(
        platform=Platform.BLINKIT, source_record_id="1", raw_artifact_reference=artifact,
        normalized_name=name, normalized_quantity="500 ml", normalized_category="dairy",
        platform_identifiers=(("source_index", "1"),), observed_price_text="100",
        observed_mrp_text="120", observed_offer_text="20 OFF", availability_signal="in_stock",
        evidence_references=(evidence,),
        field_references=(ObservationFieldReference(evidence_reference=evidence, locator="products[1].name"),),
        completeness=completeness, parser_version="blinkit-parser-v1", normalization_version="normalizer-v1",
    )


def test_builds_product_intelligence_inputs_and_preserves_provenance() -> None:
    observation = _observation()
    handoff = ProductIntelligenceIngestionAdapter().build_handoff(observation)
    assert handoff.observation_id == observation.observation_id
    assert handoff.platform_listing is not None
    assert handoff.platform_listing.platform_listing_id == "1"
    assert handoff.platform_listing.raw_title == "Milk"
    assert handoff.listing_observation is not None
    assert handoff.listing_observation.parser_version == "blinkit-parser-v1"
    assert handoff.listing_observation.capture_timestamp == observation.raw_artifact_reference.capture_timestamp
    assert handoff.listing_observation.source_artifact_reference == "artifact-1"
    assert handoff.normalization_version == "normalizer-v1"
    assert handoff.raw_artifact_reference == observation.raw_artifact_reference
    assert handoff.evidence_references == observation.evidence_references
    assert handoff.field_references == observation.field_references
    assert handoff.pipeline_request is not None


def test_replay_is_deterministic_and_completeness_is_preserved() -> None:
    adapter = ProductIntelligenceIngestionAdapter()
    partial = _observation(state=CompletenessState.PARTIAL)
    first = adapter.build_handoff(partial)
    second = adapter.build_handoff(partial.model_copy(deep=True))
    assert first == second
    assert first.completeness.state is CompletenessState.PARTIAL


def test_unknown_completeness_is_not_upgraded() -> None:
    handoff = ProductIntelligenceIngestionAdapter().build_handoff(_observation(state=CompletenessState.UNKNOWN))
    assert handoff.completeness.state is CompletenessState.UNKNOWN


def test_empty_completeness_creates_no_fabricated_listing() -> None:
    handoff = ProductIntelligenceIngestionAdapter().build_handoff(_observation(state=CompletenessState.EMPTY, name=None))
    assert handoff.platform_listing is None
    assert handoff.listing_observation is None
    assert handoff.pipeline_request is None


def test_missing_title_fails_closed() -> None:
    with pytest.raises(ValueError, match="normalized_name"):
        ProductIntelligenceIngestionAdapter().build_handoff(_observation(name=None))
