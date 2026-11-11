"""Deterministic helpers for capture-timestamp integrity tests.

No wall clock is used here. Callers inject a frozen, timezone-aware instant.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.cost_intelligence.shared.money import Money
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


class FrozenClock:
    """Injected clock returning one fixed, timezone-aware instant."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def make_observation(
    *,
    artifact_id: str,
    timestamp: datetime,
    record_id: str,
    retailer_product_id: str,
    price_minor: int = 10000,
) -> NormalizedObservation:
    """Build one governed ZEPTO observation with an explicit capture time."""

    artifact = RawArtifactReference(
        artifact_id=artifact_id,
        job_id="job-1",
        attempt_id="attempt-1",
        platform=Platform.ZEPTO,
        capture_type=CaptureType.SEARCH_RESULTS,
        content_digest="a" * 64,
        storage_reference=f"storage-{artifact_id}",
        content_type="application/json",
        capture_timestamp=timestamp,
        source_reference="https://zepto.test/s/?q=milk",
        location_scope="test-locality",
        evidence_quality="authoritative",
    )
    evidence = EvidenceReference(source_type="raw_artifact", source_id=artifact_id)
    field = ObservationFieldReference(
        evidence_reference=evidence, locator="products[0].name"
    )
    return NormalizedObservation(
        platform=Platform.ZEPTO,
        source_record_id=record_id,
        raw_artifact_reference=artifact,
        normalized_name="Amul Taaza",
        normalized_quantity="500 ml",
        platform_identifiers=(
            ("retailer_product_id", retailer_product_id),
            (
                "retailer_product_url",
                f"https://zepto.test/prn/amul/prid/{retailer_product_id}",
            ),
        ),
        observed_price_text="100",
        observed_selling_price=Money(currency="INR", minor_units=price_minor),
        availability_signal="available",
        evidence_references=(evidence,),
        field_references=(field,),
        completeness=ObservationCompleteness(
            state=CompletenessState.COMPLETE,
            scope_reference="test-scope",
            basis="complete observation capture",
        ),
        parser_version="zepto-fixture-parser-v1",
        normalization_version="normalizer-v1",
    )


def write_stored_observation(
    root: Path,
    observation: NormalizedObservation,
    *,
    capture_timestamp_value: object,
) -> str:
    """Write a stored observation JSON with an overridden capture timestamp.

    This intentionally bypasses the model constructor so the test can exercise
    the real filesystem read/deserialization path against a historical artifact.
    """

    payload = observation.model_dump(mode="json")
    payload["raw_artifact_reference"]["capture_timestamp"] = capture_timestamp_value
    path = root / f"{observation.observation_id}.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return observation.observation_id
