"""Canonical exceptions for artifact storage backends."""


class ArtifactStorageError(Exception):
    """Base exception exposed by artifact stores."""


class ArtifactNotFound(ArtifactStorageError):
    """The requested artifact is not stored."""


class ArtifactAlreadyExists(ArtifactStorageError):
    """An immutable artifact identity conflicts with stored content."""


class ArtifactStorageFailure(ArtifactStorageError):
    """A backend operation could not be completed."""


class CorruptArtifact(ArtifactStorageError):
    """Stored payload or metadata failed integrity validation."""


class InvalidStorageReference(ArtifactStorageError):
    """A storage reference is malformed or inconsistent."""
