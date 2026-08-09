"""Backend-independent artifact storage contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, field_validator


class ArtifactPublicationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    content_digest: str
    content_type: str

    @field_validator("artifact_id", "content_digest", "content_type")
    @classmethod
    def _require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("publication fields must be non-empty")
        return value


class StorageReference(BaseModel):
    """Opaque immutable reference returned by an artifact store."""

    model_config = ConfigDict(frozen=True)

    storage_reference_id: str
    artifact_id: str
    store_namespace: str
    storage_backend: str
    content_digest: str
    content_type: str

    @field_validator(
        "storage_reference_id",
        "artifact_id",
        "store_namespace",
        "storage_backend",
        "content_digest",
        "content_type",
    )
    @classmethod
    def _require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("storage reference fields must be non-empty")
        return value


class ArtifactStore(ABC):
    """Deterministic storage boundary independent of backend technology."""

    @abstractmethod
    def store(self, request: ArtifactPublicationRequest, payload: bytes) -> StorageReference:
        """Store immutable bytes and return an opaque storage reference."""

    @abstractmethod
    def retrieve(self, reference: StorageReference) -> bytes:
        """Retrieve and integrity-check immutable artifact bytes."""

    @abstractmethod
    def exists(self, reference: StorageReference) -> bool:
        """Return whether a structurally readable artifact is present."""
