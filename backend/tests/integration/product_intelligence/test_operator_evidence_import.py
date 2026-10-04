from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.data_ingestion.operator_evidence import import_validated_evidence, load_operator_evidence
from app.data_ingestion.observation_registry.filesystem import FilesystemObservationRegistry
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.catalog.storage import CatalogFilesystemStore


# This is synthetic parser-contract input in a temporary test directory only.
SYNTHETIC_CAPTURE = b"""
<html><body><div role="button" id="test-retailer-id">
  <a href="/prn/synthetic-test-item/prid/test-retailer-id">Synthetic Test Item</a>
  <span>500 g</span><span>Rs. 42</span><span>ADD</span>
</div></body></html>
"""


def _manifest(tmp_path, *, html=SYNTHETIC_CAPTURE, overrides=None):
    (tmp_path / "capture.html").write_bytes(html)
    payload = {
        "schema_version": 1,
        "retailer": "BLINKIT",
        "sanitized_capture": True,
        "source_reference": "https://blinkit.com/s/?q=Synthetic%20Test%20Item",
        "captured_at": "2026-09-01T12:00:00+05:30",
        "capture_type": "SEARCH_RESULTS",
        "content_type": "text/html",
        "payload_file": "capture.html",
        "payload_sha256": hashlib.sha256(html).hexdigest(),
        "location_scope": "synthetic test locality",
        "query": "Synthetic Test Item",
        "coverage": {
            "evaluation_scope": "synthetic test capture scope",
            "pages_evaluated": 1,
            "pagination_complete": None,
            "termination_reason": "operator supplied single-page capture",
        },
    }
    payload.update(overrides or {})
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_local_evidence_flows_through_existing_pipeline_and_replays_idempotently(tmp_path):
    path = _manifest(tmp_path)
    evidence = load_operator_evidence(path)
    settings = Settings(data_dir=tmp_path / "cartel-data")

    first = asyncio.run(import_validated_evidence(evidence, settings=settings))
    second = asyncio.run(import_validated_evidence(load_operator_evidence(path), settings=settings))

    assert first.status == second.status == "completed_with_failures"
    assert len(first.observations) == len(second.observations) == 1
    record = first.observations[0]
    replay = second.observations[0]
    assert record.status.value == "association_unresolved"
    assert record.observation.observation_id == replay.observation.observation_id
    assert record.observation.platform_identifiers == (
        ("retailer_product_id", "test-retailer-id"),
        ("retailer_product_url", "https://blinkit.com/prn/synthetic-test-item/prid/test-retailer-id"),
        ("source_index", "1"),
    )
    artifact = record.observation.raw_artifact_reference
    assert artifact.source_reference == "https://blinkit.com/s/?q=Synthetic%20Test%20Item"
    assert artifact.capture_timestamp == datetime.fromisoformat("2026-09-01T12:00:00+05:30")
    assert artifact.content_digest == hashlib.sha256(SYNTHETIC_CAPTURE).hexdigest()

    observations = FilesystemObservationRegistry(settings.data_dir / "product_intelligence/observations")
    assert len(observations.list_all()) == 1
    catalog_root = settings.data_dir / "product_intelligence/catalog"
    catalog = FilesystemAuthoritativeCatalog(store=CatalogFilesystemStore(root_dir=catalog_root))
    associations = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=catalog_root)
    )
    assert catalog.load_state().products == ()
    assert associations.all() == ()


@pytest.mark.parametrize(
    "overrides",
    [
        {"retailer": None},
        {"source_reference": None},
        {"captured_at": None},
        {"payload_sha256": "bad"},
        {"sanitized_capture": None},
    ],
)
def test_incomplete_manifest_provenance_is_rejected_before_persistence(tmp_path, overrides):
    path = _manifest(tmp_path, overrides=overrides)
    with pytest.raises(ValidationError):
        load_operator_evidence(path)


def test_invalid_source_url_and_query_mismatch_are_rejected(tmp_path):
    path = _manifest(tmp_path, overrides={"source_reference": "https://example.invalid/s/?q=Synthetic%20Test%20Item"})
    with pytest.raises(ValidationError):
        load_operator_evidence(path)

    path = _manifest(tmp_path, overrides={"source_reference": "https://blinkit.com/s/?q=other"})
    with pytest.raises(ValueError, match="query must match"):
        load_operator_evidence(path)


@pytest.mark.parametrize(
    "html, message",
    [
        (
            b'<div role="button"><a href="/prn/item/prid/x">Item</a><span>500 g</span><span>Rs. 10</span><span>ADD</span></div>',
            "retailer product ID",
        ),
        (
            b'<div role="button" id="x"><span>Item</span><span>500 g</span><span>Rs. 10</span><span>ADD</span></div>',
            "verified Blinkit product URL",
        ),
        (
            b'<div role="button" id="x"><a href="/prn/item/prid/x">Item</a><span>Rs. 10</span><span>ADD</span></div>',
            "variant/pack information",
        ),
    ],
)
def test_missing_product_or_variant_identity_is_rejected(tmp_path, html, message):
    path = _manifest(tmp_path, html=html)
    with pytest.raises(ValueError, match=message):
        load_operator_evidence(path)


def test_payload_digest_mismatch_and_path_escape_are_rejected(tmp_path):
    path = _manifest(tmp_path, overrides={"payload_sha256": "0" * 64})
    with pytest.raises(ValueError, match="digest does not match"):
        load_operator_evidence(path)

    path = _manifest(tmp_path, overrides={"payload_file": "../outside.html"})
    with pytest.raises(FileNotFoundError):
        load_operator_evidence(path)
