"""Deterministic local filesystem artifact store."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from app.data_ingestion.artifact_store.exceptions import (
    ArtifactAlreadyExists,
    ArtifactNotFound,
    ArtifactStorageFailure,
    CorruptArtifact,
    InvalidStorageReference,
)
from app.data_ingestion.artifact_store.interface import ArtifactPublicationRequest, ArtifactStore, StorageReference


class LocalFilesystemArtifactStore(ArtifactStore):
    """Filesystem backend using identity-only deterministic locations."""

    def __init__(self, root: str | Path, store_namespace: str) -> None:
        self._root = Path(root)
        self._store_namespace = self._non_empty(store_namespace, "store namespace")
        if not self._root.is_absolute():
            raise InvalidStorageReference("artifact store root must be absolute")
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ArtifactStorageFailure("could not initialize artifact store") from exc

    def store(self, request: ArtifactPublicationRequest, payload: bytes) -> StorageReference:
        artifact_id = self._validate_artifact_id(request.artifact_id)
        if not isinstance(payload, bytes):
            raise ArtifactStorageFailure("artifact payload must be bytes")
        digest = hashlib.sha256(payload).hexdigest()
        if digest != request.content_digest:
            raise ArtifactStorageFailure("payload digest does not match artifact reference")

        reference = self._reference(request, digest)
        payload_path, metadata_path = self._paths(artifact_id)
        try:
            if payload_path.exists() or metadata_path.exists():
                return self._resolve_duplicate(reference, payload_path, metadata_path)

            payload_path.parent.mkdir(parents=True, exist_ok=True)
            payload_tmp = payload_path.with_name("payload.bin.tmp")
            metadata_tmp = metadata_path.with_name("reference.json.tmp")
            metadata = self._serialize_reference(reference)
            payload_tmp.write_bytes(payload)
            metadata_tmp.write_text(metadata, encoding="utf-8")
            os.replace(payload_tmp, payload_path)
            os.replace(metadata_tmp, metadata_path)
            return reference
        except (ArtifactAlreadyExists, CorruptArtifact, ArtifactStorageFailure):
            raise
        except OSError as exc:
            raise ArtifactStorageFailure("artifact storage write failed") from exc

    def retrieve(self, reference: StorageReference) -> bytes:
        reference = self._validate_reference(reference)
        payload_path, metadata_path = self._paths(reference.artifact_id)
        try:
            if not payload_path.exists() and not metadata_path.exists():
                raise ArtifactNotFound("artifact is not stored")
            if not payload_path.exists() or not metadata_path.exists():
                raise CorruptArtifact("artifact storage is incomplete")
            stored = self._read_reference(metadata_path)
            self._require_same_reference(reference, stored)
            payload = payload_path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != reference.content_digest:
                raise CorruptArtifact("stored payload digest mismatch")
            return payload
        except (ArtifactNotFound, CorruptArtifact, InvalidStorageReference):
            raise
        except OSError as exc:
            raise ArtifactStorageFailure("artifact retrieval failed") from exc

    def exists(self, reference: StorageReference) -> bool:
        reference = self._validate_reference(reference)
        payload_path, metadata_path = self._paths(reference.artifact_id)
        try:
            if not payload_path.exists() or not metadata_path.exists():
                return False
            stored = self._read_reference(metadata_path)
            self._require_same_reference(reference, stored)
            return True
        except (CorruptArtifact, InvalidStorageReference):
            raise
        except OSError as exc:
            raise ArtifactStorageFailure("artifact existence check failed") from exc

    def _reference(self, request: ArtifactPublicationRequest, digest: str) -> StorageReference:
        reference_id = self._reference_id(self._store_namespace, request.artifact_id, digest)
        return StorageReference(
            storage_reference_id=reference_id,
            artifact_id=request.artifact_id,
            store_namespace=self._store_namespace,
            storage_backend="local_filesystem",
            content_digest=digest,
            content_type=request.content_type,
        )

    @staticmethod
    def _reference_id(namespace: str, artifact_id: str, digest: str) -> str:
        canonical = json.dumps(
            {"artifact_id": artifact_id, "content_digest": digest, "store_namespace": namespace},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _validate_reference(self, reference: StorageReference) -> StorageReference:
        if not isinstance(reference, StorageReference):
            raise InvalidStorageReference("storage reference has an invalid type")
        self._validate_artifact_id(reference.artifact_id)
        expected = self._reference_id(
            reference.store_namespace,
            reference.artifact_id,
            reference.content_digest,
        )
        if reference.storage_reference_id != expected:
            raise InvalidStorageReference("storage reference identity is inconsistent")
        if reference.store_namespace != self._store_namespace:
            raise InvalidStorageReference("storage reference belongs to another namespace")
        if reference.storage_backend != "local_filesystem":
            raise InvalidStorageReference("storage reference has an unsupported backend")
        if len(reference.content_digest) != 64 or any(
            char not in "0123456789abcdef" for char in reference.content_digest
        ):
            raise InvalidStorageReference("storage reference has an invalid sha256 digest")
        return reference

    def _resolve_duplicate(
        self,
        expected: StorageReference,
        payload_path: Path,
        metadata_path: Path,
    ) -> StorageReference:
        if not payload_path.exists() or not metadata_path.exists():
            raise CorruptArtifact("existing artifact storage is incomplete")
        stored = self._read_reference(metadata_path)
        if stored.artifact_id == expected.artifact_id and stored.content_digest != expected.content_digest:
            raise ArtifactAlreadyExists("artifact identity already stores different content")
        self._require_same_reference(expected, stored)
        try:
            payload = payload_path.read_bytes()
        except OSError as exc:
            raise ArtifactStorageFailure("could not verify existing artifact") from exc
        if hashlib.sha256(payload).hexdigest() != expected.content_digest:
            raise CorruptArtifact("existing artifact payload is corrupt")
        return stored

    @staticmethod
    def _serialize_reference(reference: StorageReference) -> str:
        return json.dumps(
            reference.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    @staticmethod
    def _read_reference(path: Path) -> StorageReference:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return StorageReference.model_validate(payload)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise CorruptArtifact("stored reference metadata is malformed") from exc

    @staticmethod
    def _require_same_reference(expected: StorageReference, actual: StorageReference) -> None:
        if actual != expected:
            raise CorruptArtifact("stored reference metadata is inconsistent")

    def _paths(self, artifact_id: str) -> tuple[Path, Path]:
        artifact_id = self._validate_artifact_id(artifact_id)
        directory = self._root / "artifacts" / artifact_id[:2] / artifact_id
        return directory / "payload.bin", directory / "reference.json"

    @staticmethod
    def _validate_artifact_id(value: str) -> str:
        value = LocalFilesystemArtifactStore._non_empty(value, "artifact id")
        if len(value) < 2 or any(char in value for char in ("/", "\\", ":")) or ".." in value:
            raise InvalidStorageReference("artifact id is not a valid storage path segment")
        return value

    @staticmethod
    def _non_empty(value: str, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise InvalidStorageReference(f"{label} must be non-empty")
        return value
