from __future__ import annotations

from unittest.mock import patch

import pytest

from app.data_ingestion import FilesystemObservationRegistry, ObservationRegistrationConflict
from app.cost_intelligence.shared.money import Money
from tests.unit.data_ingestion.test_observation_registry import _observation


def test_registration_lookup_and_restart_preserve_all_fields(tmp_path) -> None:
    original = _observation()
    first = FilesystemObservationRegistry(tmp_path)
    assert first.register(original) == original
    assert first.get(original.observation_id) == original

    second = FilesystemObservationRegistry(tmp_path)
    restored = second.get(original.observation_id)
    assert restored == original
    assert restored is not original
    assert restored is not None
    assert restored.raw_artifact_reference == original.raw_artifact_reference
    assert restored.field_references == original.field_references
    assert restored.completeness == original.completeness
    assert restored.evidence_references == original.evidence_references
    assert restored.parser_version == original.parser_version
    assert restored.normalization_version == original.normalization_version


def test_typed_price_round_trips_after_restart(tmp_path) -> None:
    original = _observation().model_copy(
        update={"observed_selling_price": Money(currency="INR", minor_units=10000)}
    )
    FilesystemObservationRegistry(tmp_path).register(original)

    restored = FilesystemObservationRegistry(tmp_path).get(original.observation_id)

    assert restored is not None
    assert restored.observed_selling_price == Money(currency="INR", minor_units=10000)
    assert restored.observed_price_text == original.observed_price_text


def test_identical_registration_is_idempotent_and_serialization_is_deterministic(tmp_path) -> None:
    original = _observation()
    registry = FilesystemObservationRegistry(tmp_path)
    first = registry.register(original)
    first_payload = next(tmp_path.glob("*.json")).read_text(encoding="utf-8")

    assert registry.register(_observation()) == first
    second_payload = next(tmp_path.glob("*.json")).read_text(encoding="utf-8")
    assert second_payload == first_payload


@pytest.mark.parametrize(
    "changed",
    [
        _observation("Bread"),
        _observation().model_copy(update={"observed_price_text": "101"}),
        _observation().model_copy(update={"completeness": _observation().completeness.model_copy(update={"basis": "changed"})}),
        _observation().model_copy(update={"evidence_references": tuple()}),
    ],
)
def test_same_observation_id_with_conflicting_content_fails_closed(tmp_path, changed) -> None:
    registry = FilesystemObservationRegistry(tmp_path)
    original = _observation()
    with patch(
        "app.data_ingestion.types.NormalizedObservation.observation_id",
        new_callable=lambda: property(lambda _: "collision-id"),
    ):
        registry.register(original)
        with pytest.raises(ObservationRegistrationConflict):
            registry.register(changed)
        assert registry.get("collision-id") == original
