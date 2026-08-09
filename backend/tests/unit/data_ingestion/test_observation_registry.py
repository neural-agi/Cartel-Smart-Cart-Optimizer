from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from unittest.mock import patch

from app.data_ingestion import (
    CaptureType,
    CompletenessState,
    InMemoryObservationRegistry,
    ObservationCompleteness,
    ObservationFieldReference,
    ObservationRegistrationConflict,
    NormalizedObservation,
    Platform,
    RawArtifactReference,
)
from app.product_intelligence.models import EvidenceReference


def _observation(name: str = "Milk") -> NormalizedObservation:
    artifact = RawArtifactReference(
        artifact_id="artifact-1",
        job_id="job-1",
        attempt_id="attempt-1",
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        content_digest="digest",
        storage_reference="opaque",
        content_type="text/html",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_reference="https://example.test",
    )
    evidence = EvidenceReference(source_type="raw_artifact", source_id="artifact-1")
    field = ObservationFieldReference(evidence_reference=evidence, locator="products[1].name")
    return NormalizedObservation(
        platform=Platform.BLINKIT,
        source_record_id="1",
        raw_artifact_reference=artifact,
        normalized_name=name,
        normalized_quantity="500 ml",
        platform_identifiers=(("source_index", "1"),),
        observed_price_text="100",
        evidence_references=(evidence,),
        field_references=(field,),
        completeness=ObservationCompleteness(
            state=CompletenessState.COMPLETE,
            scope_reference="scope",
            basis="complete",
        ),
        parser_version="blinkit-parser-v1",
        normalization_version="normalizer-v1",
    )


def test_register_get_exists_and_process_local_lifecycle() -> None:
    registry = InMemoryObservationRegistry()
    observation = _observation()

    assert registry.register(observation) == observation
    assert registry.get(observation.observation_id) == observation
    assert registry.exists(observation.observation_id)
    assert registry.get("missing") is None
    assert not registry.exists("missing")
    assert not InMemoryObservationRegistry().exists(observation.observation_id)


def test_identical_registration_is_idempotent_and_conflict_preserves_original() -> None:
    registry = InMemoryObservationRegistry()
    original = _observation()
    replay = _observation()
    with patch(
        "app.data_ingestion.types.NormalizedObservation.observation_id",
        new_callable=lambda: property(lambda _: "collision-id"),
    ):
        assert registry.register(replay) == original
        with pytest.raises(ObservationRegistrationConflict) as error:
            registry.register(_observation("Bread"))
        assert error.value.observation_id == "collision-id"
        assert registry.get("collision-id") == original


def test_provenance_and_values_survive_retrieval_without_mutable_aliases() -> None:
    registry = InMemoryObservationRegistry()
    observation = _observation()
    registry.register(observation)
    retrieved = registry.get(observation.observation_id)

    assert retrieved is not None
    assert retrieved.raw_artifact_reference == observation.raw_artifact_reference
    assert retrieved.evidence_references == observation.evidence_references
    assert retrieved.field_references == observation.field_references
    assert retrieved.completeness == observation.completeness
    assert retrieved.normalization_version == "normalizer-v1"
    assert retrieved.platform_identifiers == (("source_index", "1"),)
    assert retrieved.normalized_name == "Milk"
    assert not hasattr(registry, "update")
    assert not hasattr(registry, "delete")


def test_empty_lookup_keys_are_rejected() -> None:
    registry = InMemoryObservationRegistry()
    with pytest.raises(ValueError):
        registry.get(" ")
    with pytest.raises(ValueError):
        registry.exists("")


def test_concurrent_identical_registration_is_idempotent() -> None:
    registry = InMemoryObservationRegistry()
    observation = _observation()
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: registry.register(_observation()), range(16)))
    assert all(result == observation for result in results)


def test_concurrent_conflicting_registration_cannot_overwrite_original() -> None:
    registry = InMemoryObservationRegistry()
    original = _observation()
    with patch(
        "app.data_ingestion.types.NormalizedObservation.observation_id",
        new_callable=lambda: property(lambda _: "collision-id"),
    ):
        registry.register(original)
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: _register_conflict(registry), range(16)))
    assert all(result is True for result in results)
    assert registry.get("collision-id") == original


def _register_conflict(registry: InMemoryObservationRegistry) -> bool:
    try:
        registry.register(_observation("Bread"))
    except ObservationRegistrationConflict:
        return True
    return False
