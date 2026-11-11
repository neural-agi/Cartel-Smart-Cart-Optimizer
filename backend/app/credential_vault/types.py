"""Provider-independent credential-vault vocabulary and public value types.

This module contains no retailer, OAuth, browser-automation, or transport
concerns. It defines only the controlled secret-type vocabulary, opaque
references, non-secret metadata, and typed failures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID, uuid4


class SecretType(StrEnum):
    """Controlled, extensible secret-purpose vocabulary.

    These are storage categories only. No retailer credential is created in
    this phase, and no type represents a password, OTP, payment card, CVV, UPI
    PIN, payment OTP, or reusable payment credential.
    """

    OAUTH_ACCESS_TOKEN = "oauth_access_token"
    OAUTH_REFRESH_TOKEN = "oauth_refresh_token"
    BROWSER_SESSION_CREDENTIAL = "browser_session_credential"
    RETAILER_AUTHORIZATION_ARTIFACT = "retailer_authorization_artifact"


# Explicitly rejected categories. They are not members of SecretType; this set
# exists so the service can return a precise, non-secret error and so tests can
# prove that forbidden material is never accepted.
FORBIDDEN_SECRET_TYPES: Final[frozenset[str]] = frozenset(
    {
        "password",
        "retailer_password",
        "otp",
        "one_time_password",
        "payment_card",
        "card_number",
        "cvv",
        "cvc",
        "upi_pin",
        "payment_otp",
        "reusable_payment_credential",
    }
)


class SecretStatus(StrEnum):
    """Lifecycle of one stored secret version."""

    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    DELETED = "DELETED"


@dataclass(frozen=True)
class SecretReference:
    """Opaque, non-secret handle for a secret lineage.

    The reference is not a credential and is safe to persist and audit. It is
    never sufficient on its own: every vault operation also requires a verified
    owner + persisted connection context.
    """

    value: UUID

    @classmethod
    def new(cls) -> SecretReference:
        return cls(uuid4())

    @classmethod
    def from_value(cls, value: str | UUID) -> SecretReference:
        if isinstance(value, UUID):
            return cls(value)
        try:
            return cls(UUID(str(value)))
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidSecretInput("invalid_secret_reference") from exc

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"SecretReference({self.value})"


@dataclass(frozen=True)
class SecretOwner:
    """Caller-supplied ownership context, validated against the database."""

    user_id: UUID
    connection_id: UUID
    retailer_id: str

    def __repr__(self) -> str:
        return (
            "SecretOwner("
            f"user_id={self.user_id}, connection_id={self.connection_id}, "
            f"retailer_id={self.retailer_id!r})"
        )


@dataclass(frozen=True)
class SecretMetadata:
    """Non-secret description of one stored secret version.

    Deliberately excludes plaintext, nonce, ciphertext, and key material so it
    is safe to serialize, log, or return from a future HTTP layer.
    """

    reference: UUID
    version: int
    user_id: UUID
    connection_id: UUID
    retailer_id: str
    secret_type: SecretType
    status: SecretStatus
    algorithm: str
    key_version: str
    created_at: datetime
    updated_at: datetime
    superseded_at: datetime | None = None
    revoked_at: datetime | None = None
    deleted_at: datetime | None = None

    def __repr__(self) -> str:
        return (
            "SecretMetadata("
            f"reference={self.reference}, version={self.version}, "
            f"secret_type={self.secret_type.value!r}, status={self.status.value!r})"
        )


class CredentialVaultError(Exception):
    """Base class for typed credential-vault failures."""


class VaultUnavailable(CredentialVaultError):
    """No safe key provider is configured; the vault fails closed."""


class VaultKeyUnavailable(CredentialVaultError):
    """A required key version is missing, malformed, or inaccessible."""


class SecretNotFound(CredentialVaultError):
    """Owner-scoped lookup found nothing (including another owner's secret)."""

    def __init__(self, reference: object) -> None:
        self.reference = reference
        super().__init__("credential secret not found")


class SecretAccessDenied(CredentialVaultError):
    """The persisted connection state or operation does not permit retrieval."""

    def __init__(self, *, connection_id: object, operation: object) -> None:
        self.connection_id = connection_id
        self.operation = operation
        super().__init__("credential secret access denied for this connection state")


class UnsupportedSecretType(CredentialVaultError):
    """The requested secret type is outside the controlled vocabulary."""

    def __init__(self, secret_type: object) -> None:
        self.secret_type = secret_type
        super().__init__("unsupported credential secret type")


class InvalidSecretInput(CredentialVaultError):
    """Caller supplied a malformed or out-of-policy value."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"invalid credential vault input: {code}")


class SecretVersionConflict(CredentialVaultError):
    """A stale writer presented an expected secret version."""

    def __init__(self, *, expected_version: int, actual_version: int) -> None:
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            "credential secret version conflict: expected "
            f"{expected_version}, found {actual_version}"
        )


class SecretStateConflict(CredentialVaultError):
    """The secret is not in a state that permits the requested mutation."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"credential secret state conflict: {code}")


class SecretDeletionDenied(CredentialVaultError):
    """Retention rules do not permit deletion yet (for example, still ACTIVE)."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"credential secret deletion denied: {code}")


class SecretDecryptionFailed(CredentialVaultError):
    """Ciphertext, AAD, or key material failed authentication."""


class SecretRotationConflict(CredentialVaultError):
    """A concurrent rotation already changed the active secret version."""

    def __init__(self, *, reference: object) -> None:
        self.reference = reference
        super().__init__("concurrent credential secret rotation detected")


# Audit event names. Retrieval and health observations are intentionally not
# audited here; they would create unbounded permanent rows.
AUDIT_CREATED: Final[str] = "credential_secret_created"
AUDIT_ROTATED: Final[str] = "credential_secret_rotated"
AUDIT_REVOKED: Final[str] = "credential_secret_revoked"
AUDIT_DELETED: Final[str] = "credential_secret_deleted"

# Audit payloads are non-secret by construction. No plaintext, ciphertext,
# nonce, key version material, or caller text is allowed.
AUDIT_PAYLOAD_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "reference",
        "user_id",
        "connection_id",
        "retailer_id",
        "secret_type",
        "version",
        "status",
        "occurred_at",
    }
)
