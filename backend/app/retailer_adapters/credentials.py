"""Secret resolution for authorized adapter operations.

Adapters never receive the vault, a session, or a raw secret reference. The
executor resolves the adapter's declared secret requirements through the
authorized ``CredentialVault`` surface and hands the adapter an opaque bundle.
The bundle's representation is redacted so it is safe to keep out of logs.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Protocol

from sqlalchemy.orm import Session

from app.credential_vault.service import CredentialVault
from app.credential_vault.types import (
    SecretMetadata,
    SecretOwner,
    SecretStatus,
    SecretType,
)
from app.retailer_connections.lifecycle import RetailerOperation

SECRET_REDACTION = "[REDACTED]"
_SECRET_KEY_MARKERS = (
    "secret",
    "token",
    "credential",
    "password",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
)


class CredentialResolutionError(Exception):
    """Base class for adapter credential-resolution failures."""


class MissingCredentialMaterial(CredentialResolutionError):
    """The adapter requires a secret type that has no ACTIVE version."""

    def __init__(self, secret_type: SecretType) -> None:
        self.secret_type = secret_type
        super().__init__(f"missing active credential material: {secret_type.value}")


class RetailerCredentialBundle:
    """Opaque per-operation secret material.

    Raw values are exposed only through :meth:`reveal`, which adapters call
    inside an authorized operation. The bundle deliberately has no public
    attribute or serialization that returns plaintext.
    """

    __slots__ = ("_values",)

    def __init__(self, values: Mapping[SecretType, bytes]) -> None:
        self._values = dict(values)

    def __repr__(self) -> str:
        types = ", ".join(sorted(item.value for item in self._values))
        return f"RetailerCredentialBundle(secret_types=({types}))"

    def __bool__(self) -> bool:
        return bool(self._values)

    @property
    def secret_types(self) -> tuple[SecretType, ...]:
        return tuple(sorted(self._values, key=lambda item: item.value))

    def reveal(self, secret_type: SecretType) -> bytes:
        try:
            return self._values[secret_type]
        except KeyError as exc:
            raise MissingCredentialMaterial(secret_type) from exc

    def get(self, secret_type: SecretType) -> bytes | None:
        return self._values.get(secret_type)


class CredentialResolver(Protocol):
    """Resolve declared secret types through an authorized vault operation."""

    def resolve(
        self,
        db: Session,
        *,
        owner: SecretOwner,
        operation: RetailerOperation,
        secret_types: Sequence[SecretType],
    ) -> RetailerCredentialBundle: ...


class VaultCredentialResolver:
    """Vault-backed resolver that never bypasses lifecycle authorization."""

    def __init__(self, vault: CredentialVault) -> None:
        self._vault = vault

    def resolve(
        self,
        db: Session,
        *,
        owner: SecretOwner,
        operation: RetailerOperation,
        secret_types: Sequence[SecretType],
    ) -> RetailerCredentialBundle:
        required = _deduplicate(secret_types)
        if not required:
            return RetailerCredentialBundle({})

        metadata = self._vault.list_metadata(db, owner=owner)
        active = _active_metadata(metadata, required)
        values: dict[SecretType, bytes] = {}
        for secret_type in required:
            item = active.get(secret_type)
            if item is None:
                raise MissingCredentialMaterial(secret_type)
            values[secret_type] = self._vault.retrieve(
                db,
                owner=owner,
                reference=item.reference,
                operation=operation,
                expected_version=item.version,
            )
        return RetailerCredentialBundle(values)


def _deduplicate(secret_types: Iterable[SecretType]) -> tuple[SecretType, ...]:
    seen: set[SecretType] = set()
    ordered: list[SecretType] = []
    for secret_type in secret_types:
        if secret_type not in seen:
            seen.add(secret_type)
            ordered.append(secret_type)
    return tuple(ordered)


def _active_metadata(
    metadata: Iterable[SecretMetadata],
    required: Sequence[SecretType],
) -> dict[SecretType, SecretMetadata]:
    active: dict[SecretType, SecretMetadata] = {}
    for item in metadata:
        if item.status is not SecretStatus.ACTIVE or item.secret_type not in required:
            continue
        current = active.get(item.secret_type)
        if current is None or item.version > current.version:
            active[item.secret_type] = item
    return active


def redact_log_fields(fields: Mapping[str, object]) -> dict[str, object]:
    """Return a copy safe for structured logs.

    Only key names are inspected; values are never stringified or truncated, so
    an accidentally supplied secret cannot leak through a repr.
    """

    redacted: dict[str, object] = {}
    for key, value in fields.items():
        lowered = key.lower()
        if any(marker in lowered for marker in _SECRET_KEY_MARKERS):
            redacted[key] = SECRET_REDACTION
        else:
            redacted[key] = value
    return redacted


__all__ = [
    "SECRET_REDACTION",
    "CredentialResolutionError",
    "CredentialResolver",
    "MissingCredentialMaterial",
    "RetailerCredentialBundle",
    "VaultCredentialResolver",
    "redact_log_fields",
]
