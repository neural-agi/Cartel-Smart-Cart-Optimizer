from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.data_ingestion import (
    CaptureType,
    CompletenessState,
    NormalizedObservation,
    ObservationCompleteness,
    ObservationFieldReference,
    Platform,
    RawArtifactReference,
)
from app.product_intelligence.models import EvidenceReference


def _artifact() -> RawArtifactReference:
    return RawArtifactReference(
        artifact_id="artifact-1", job_id="job-1", attempt_id="attempt-1", platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS, content_digest="digest", storage_reference="opaque",
        content_type="text/html", capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), source_reference="https://example.test",
    )


def _observation(version: str = "normalizer-v1") -> NormalizedObservation:
    evidence = EvidenceReference(source_type="raw_artifact", source_id="artifact-1")
    field = ObservationFieldReference(evidence_reference=evidence, locator="products[1].product_name")
    return NormalizedObservation(
        platform=Platform.BLINKIT, source_record_id="1", raw_artifact_reference=_artifact(),
        normalized_name="Milk", normalized_quantity="500 ml", platform_identifiers=(("source_index", "1"),),
        observed_price_text="₹100", observed_mrp_text="₹120", observed_offer_text="₹20 OFF",
        availability_signal="in_stock", evidence_references=(evidence,), field_references=(field,),
        completeness=ObservationCompleteness(state=CompletenessState.COMPLETE, scope_reference="scope", basis="no_next_page"),
        parser_version="blinkit-parser-v1",
        normalization_version=version,
    )


def test_normalized_observation_preserves_contract_data() -> None:
    observation = _observation()
    assert observation.raw_artifact_reference == _artifact()
    assert observation.evidence_references[0].source_id == "artifact-1"
    assert observation.field_references[0].locator == "products[1].product_name"
    assert observation.completeness.state is CompletenessState.COMPLETE
    assert observation.platform_identifiers == (("source_index", "1"),)
    assert not hasattr(observation, "product_id")
    assert not hasattr(observation, "variant_id")


def test_observation_identity_is_deterministic_and_versioned() -> None:
    first = _observation()
    second = _observation()
    assert first.observation_id == second.observation_id
    assert first.observation_id != _observation("normalizer-v2").observation_id


def test_identity_changes_for_observation_defining_input() -> None:
    first = _observation()
    changed = first.model_copy(update={"normalized_name": "Curd"})
    assert first.observation_id != changed.observation_id


def test_observation_is_immutable_and_requires_version() -> None:
    observation = _observation()
    with pytest.raises((TypeError, ValidationError)):
        observation.normalization_version = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        NormalizedObservation(
            platform=Platform.BLINKIT,
            source_record_id="1",
            raw_artifact_reference=_artifact(),
            evidence_references=(),
            field_references=(),
            completeness=ObservationCompleteness(state=CompletenessState.COMPLETE, scope_reference="scope", basis="complete"),
            parser_version="",
            normalization_version="",
        )
