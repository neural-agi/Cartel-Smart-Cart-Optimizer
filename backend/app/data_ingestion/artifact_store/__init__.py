"""Backend-independent artifact storage contracts and implementations."""

from app.data_ingestion.artifact_store.exceptions import (
    ArtifactAlreadyExists,
    ArtifactNotFound,
    ArtifactStorageError,
    ArtifactStorageFailure,
    CorruptArtifact,
    InvalidStorageReference,
)
from app.data_ingestion.artifact_store.filesystem import LocalFilesystemArtifactStore
from app.data_ingestion.artifact_store.interface import ArtifactStore, StorageReference

__all__ = [
    "ArtifactAlreadyExists",
    "ArtifactNotFound",
    "ArtifactStorageError",
    "ArtifactStorageFailure",
    "ArtifactStore",
    "CorruptArtifact",
    "InvalidStorageReference",
    "LocalFilesystemArtifactStore",
    "StorageReference",
]
