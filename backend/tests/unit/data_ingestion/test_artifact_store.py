from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.data_ingestion import CaptureType, Platform
from app.data_ingestion.artifact_store import (
    ArtifactAlreadyExists,
    ArtifactNotFound,
    ArtifactStorageFailure,
    CorruptArtifact,
    InvalidStorageReference,
    LocalFilesystemArtifactStore,
    StorageReference,
)
from app.data_ingestion.types import RawArtifactReference


def _artifact(payload: bytes = b"payload", artifact_id: str = "artifact-1") -> RawArtifactReference:
    return RawArtifactReference(
        artifact_id=artifact_id,
        job_id="job-1",
        attempt_id="attempt-1",
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        content_digest=hashlib.sha256(payload).hexdigest(),
        storage_reference="external-storage-reference",
        content_type="application/octet-stream",
        capture_timestamp="2026-01-01T00:00:00Z",
        source_reference="https://example.test/search",
    )


def test_store_and_retrieve_preserves_binary_payload(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")
    payload = b"\x00\xff\x10cartel"

    reference = store.store(_artifact(payload), payload)

    assert store.retrieve(reference) == payload
    assert store.exists(reference) is True


def test_storage_reference_is_deterministic(tmp_path: Path) -> None:
    payload = "₹100 — café".encode("utf-8")
    first = LocalFilesystemArtifactStore(tmp_path / "one", "local-test").store(_artifact(payload), payload)
    second = LocalFilesystemArtifactStore(tmp_path / "two", "local-test").store(_artifact(payload), payload)

    assert first == second


def test_path_layout_uses_identity_only(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")
    artifact = _artifact()
    store.store(artifact, b"payload")

    expected = tmp_path / "artifacts" / artifact.artifact_id[:2] / artifact.artifact_id
    assert (expected / "payload.bin").exists()
    assert (expected / "reference.json").exists()


def test_duplicate_identical_storage_is_idempotent(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")
    artifact = _artifact()

    first = store.store(artifact, b"payload")
    second = store.store(artifact, b"payload")

    assert first == second


def test_duplicate_different_digest_is_rejected(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")
    store.store(_artifact(b"first"), b"first")

    with pytest.raises(ArtifactAlreadyExists):
        store.store(_artifact(b"second"), b"second")


def test_payload_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")

    with pytest.raises(ArtifactStorageFailure, match="digest"):
        store.store(_artifact(b"declared"), b"different")


def test_missing_artifact_is_not_found(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")
    artifact = _artifact()
    reference = store._reference(artifact, artifact.content_digest)

    assert store.exists(reference) is False
    with pytest.raises(ArtifactNotFound):
        store.retrieve(reference)


def test_invalid_root_must_be_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(InvalidStorageReference):
        LocalFilesystemArtifactStore(Path("relative-root"), "local-test")


def test_invalid_artifact_id_is_rejected(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")

    with pytest.raises(InvalidStorageReference):
        store.store(_artifact(artifact_id="a"), b"payload")

    with pytest.raises(InvalidStorageReference):
        store.store(_artifact(artifact_id="../escape"), b"payload")


def test_invalid_storage_reference_identity_is_rejected(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")
    artifact = _artifact()
    reference = store.store(artifact, b"payload")
    malformed = reference.model_copy(update={"storage_reference_id": "wrong"})

    with pytest.raises(InvalidStorageReference):
        store.retrieve(malformed)


def test_corrupt_metadata_is_detected(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")
    artifact = _artifact()
    reference = store.store(artifact, b"payload")
    metadata_path = tmp_path / "artifacts" / artifact.artifact_id[:2] / artifact.artifact_id / "reference.json"
    metadata_path.write_text("{malformed", encoding="utf-8")

    with pytest.raises(CorruptArtifact):
        store.retrieve(reference)


def test_corrupt_payload_is_detected(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")
    artifact = _artifact()
    reference = store.store(artifact, b"payload")
    payload_path = tmp_path / "artifacts" / artifact.artifact_id[:2] / artifact.artifact_id / "payload.bin"
    payload_path.write_bytes(b"changed")

    with pytest.raises(CorruptArtifact):
        store.retrieve(reference)


def test_metadata_is_utf8_and_canonical(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path, "local-test")
    artifact = _artifact("данные".encode("utf-8"))
    store.store(artifact, "данные".encode("utf-8"))
    metadata_path = tmp_path / "artifacts" / artifact.artifact_id[:2] / artifact.artifact_id / "reference.json"

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["content_type"] == "application/octet-stream"
    assert metadata_path.read_text(encoding="utf-8") == json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def test_storage_reference_is_immutable() -> None:
    reference = StorageReference(
        storage_reference_id="ref",
        artifact_id="artifact-1",
        store_namespace="local-test",
        storage_backend="local_filesystem",
        content_digest="0" * 64,
        content_type="text/plain",
    )

    with pytest.raises((TypeError, ValueError)):
        reference.artifact_id = "changed"
