"""Provider-independent credential vault service.

The vault stores encrypted secret versions bound to a persisted
``RetailerConnection``. It never authenticates to a retailer, never performs
acquisition, and never stores passwords, OTPs, payment data, or reusable payment
credentials.

Security properties enforced here:

* every operation loads the persisted connection and verifies owner, connection,
  and retailer binding instead of trusting caller-supplied IDs;
* retrieval additionally requires a lifecycle-permitted operation, so terminal,
  blocked, degraded (except bounded health checks), and reauth-required
  connections cannot use secrets for retailer operations;
* AES-256-GCM associated data binds ciphertext to owner, connection, retailer,
  secret type, version, and opaque reference;
* missing or malformed keys fail closed;
* audit payloads contain only non-secret identifiers and timestamps;
* revocation and deletion retain audit evidence while blocking retrieval.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.credential_vault import repository
from app.credential_vault.crypto import ALGORITHM, AesGcmCodec, build_aad
from app.credential_vault.key_provider import KeyProvider, build_key_provider
from app.credential_vault.types import (
    AUDIT_CREATED,
    AUDIT_DELETED,
    AUDIT_PAYLOAD_FIELDS,
    AUDIT_REVOKED,
    AUDIT_ROTATED,
    FORBIDDEN_SECRET_TYPES,
    CredentialVaultError,
    InvalidSecretInput,
    SecretAccessDenied,
    SecretDeletionDenied,
    SecretMetadata,
    SecretNotFound,
    SecretOwner,
    SecretReference,
    SecretStateConflict,
    SecretStatus,
    SecretType,
    SecretVersionConflict,
    UnsupportedSecretType,
)
from app.data_ingestion.timestamp_integrity import Clock, SystemClock
from app.db.models import AuditEvent
from app.db.models.credential_secrets import CredentialSecret
from app.db.models.retailer_connections import RetailerConnection
from app.retailer_connections import lifecycle

# A credential may be created or rotated only while the connection can still
# participate in authentication or normal operation. Terminal and explicitly
# blocked connections cannot acquire new secret material. Revocation and
# deletion remain available in every state so cleanup is always possible.
_MUTABLE_STATUSES: frozenset[lifecycle.RetailerConnectionStatus] = frozenset(
    {
        lifecycle.RetailerConnectionStatus.PENDING_AUTH,
        lifecycle.RetailerConnectionStatus.CONNECTED,
        lifecycle.RetailerConnectionStatus.DEGRADED,
        lifecycle.RetailerConnectionStatus.REAUTH_REQUIRED,
    }
)

# Only operations that actually consume retailer credentials may unlock secret
# retrieval. Cartel data access and connection-metadata management are lifecycle
# operations, not credential consumers; allowing them to retrieve secrets would
# turn a permitted management cell into an authentication bypass.
_SECRET_CONSUMING_OPERATIONS: frozenset[lifecycle.RetailerOperation] = frozenset(
    {
        lifecycle.RetailerOperation.RETAILER_HEALTH_CHECK,
        lifecycle.RetailerOperation.PRODUCT_DISCOVERY,
        lifecycle.RetailerOperation.PRICE_AVAILABILITY_ACQUISITION,
        lifecycle.RetailerOperation.CART_PREPARATION,
        lifecycle.RetailerOperation.CHECKOUT,
    }
)


def _now(clock: Clock) -> datetime:
    value = clock.now()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _coerce_secret_type(value: SecretType | str) -> SecretType:
    if isinstance(value, SecretType):
        return value
    if isinstance(value, str) and value in FORBIDDEN_SECRET_TYPES:
        raise UnsupportedSecretType(value)
    try:
        return SecretType(value)
    except (ValueError, TypeError) as exc:
        raise UnsupportedSecretType(value) from exc


def _coerce_operation(value: lifecycle.RetailerOperation | str) -> lifecycle.RetailerOperation:
    if isinstance(value, lifecycle.RetailerOperation):
        return value
    try:
        return lifecycle.RetailerOperation(value)
    except (ValueError, TypeError) as exc:
        raise InvalidSecretInput("invalid_operation") from exc


def _metadata(row: CredentialSecret) -> SecretMetadata:
    return SecretMetadata(
        reference=row.reference,
        version=row.version,
        user_id=row.user_id,
        connection_id=row.connection_id,
        retailer_id=row.retailer_id,
        secret_type=SecretType(row.secret_type),
        status=SecretStatus(row.status),
        algorithm=row.algorithm,
        key_version=row.key_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        superseded_at=row.superseded_at,
        revoked_at=row.revoked_at,
        deleted_at=row.deleted_at,
    )


def _audit_payload(row: CredentialSecret, occurred_at: datetime) -> dict[str, object]:
    payload: dict[str, object] = {
        "reference": str(row.reference),
        "user_id": str(row.user_id),
        "connection_id": str(row.connection_id),
        "retailer_id": row.retailer_id,
        "secret_type": row.secret_type,
        "version": row.version,
        "status": row.status,
        "occurred_at": occurred_at.isoformat(),
    }
    if set(payload) != AUDIT_PAYLOAD_FIELDS:
        raise RuntimeError("credential vault audit payload field allowlist violated")
    return payload


def _audit(
    db: Session,
    *,
    row: CredentialSecret,
    event: str,
    occurred_at: datetime,
    request_id: str | None,
) -> None:
    db.add(
        AuditEvent(
            user_id=row.user_id,
            event_type=event,
            object_type="credential_secret",
            object_id=str(row.reference),
            request_id=request_id,
            payload=_audit_payload(row, occurred_at),
        )
    )


class CredentialVault:
    """Owner-scoped, AEAD-encrypted credential storage."""

    def __init__(
        self,
        *,
        key_provider: KeyProvider,
        codec: AesGcmCodec | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._key_provider = key_provider
        self._codec = codec or AesGcmCodec()
        self._clock = clock or SystemClock()

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        clock: Clock | None = None,
    ) -> CredentialVault:
        """Build the vault from deployment configuration.

        With the default ``VAULT_KEY_PROVIDER=unavailable`` every key operation
        fails closed.
        """

        return cls(key_provider=build_key_provider(settings), clock=clock)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_connection(
        self,
        db: Session,
        owner: SecretOwner,
        *,
        for_update: bool = False,
    ) -> RetailerConnection:
        connection = repository.get_connection_for_owner(
            db,
            user_id=owner.user_id,
            connection_id=owner.connection_id,
            for_update=for_update,
        )
        if connection is None or connection.retailer_id != owner.retailer_id:
            db.rollback()
            raise SecretNotFound(owner.connection_id)
        return connection

    def _authorize_retrieval(
        self,
        connection: RetailerConnection,
        operation: lifecycle.RetailerOperation,
    ) -> None:
        status = lifecycle.RetailerConnectionStatus(connection.status)
        if not lifecycle.operation_is_permitted(status, operation):
            raise SecretAccessDenied(
                connection_id=connection.id,
                operation=operation.value,
            )

    def _authorize_mutation(self, connection: RetailerConnection) -> None:
        status = lifecycle.RetailerConnectionStatus(connection.status)
        if status not in _MUTABLE_STATUSES:
            raise SecretAccessDenied(
                connection_id=connection.id,
                operation="credential_mutation",
            )

    def _reference(self, reference: SecretReference | str | UUID) -> UUID:
        if isinstance(reference, SecretReference):
            return reference.value
        return SecretReference.from_value(reference).value

    def _encrypt(
        self,
        *,
        plaintext: bytes,
        user_id: UUID,
        connection_id: UUID,
        retailer_id: str,
        secret_type: SecretType,
        version: int,
        reference: UUID,
    ) -> tuple[bytes, bytes, str]:
        key_version = self._key_provider.current_version()
        key = self._key_provider.key_for(key_version)
        aad = build_aad(
            user_id=user_id,
            connection_id=connection_id,
            retailer_id=retailer_id,
            secret_type=secret_type.value,
            version=version,
            reference=reference,
        )
        nonce, ciphertext = self._codec.encrypt(
            plaintext=plaintext,
            key=key,
            aad=aad,
        )
        return nonce, ciphertext, key_version

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def store(
        self,
        db: Session,
        *,
        owner: SecretOwner,
        secret_type: SecretType | str,
        plaintext: bytes,
        request_id: str | None = None,
    ) -> SecretMetadata:
        """Store version 1 of a new secret lineage."""

        connection = self._require_connection(db, owner, for_update=True)
        self._authorize_mutation(connection)
        st = _coerce_secret_type(secret_type)
        now = _now(self._clock)
        reference = SecretReference.new().value
        nonce, ciphertext, key_version = self._encrypt(
            plaintext=plaintext,
            user_id=connection.user_id,
            connection_id=connection.id,
            retailer_id=connection.retailer_id,
            secret_type=st,
            version=1,
            reference=reference,
        )
        row = CredentialSecret(
            reference=reference,
            version=1,
            user_id=connection.user_id,
            connection_id=connection.id,
            retailer_id=connection.retailer_id,
            secret_type=st.value,
            status=SecretStatus.ACTIVE.value,
            algorithm=ALGORITHM,
            key_version=key_version,
            nonce=nonce,
            ciphertext=ciphertext,
            created_at=now,
            updated_at=now,
        )
        try:
            repository.add(db, row)
        except IntegrityError as exc:
            db.rollback()
            raise SecretStateConflict("store_conflict") from exc
        _audit(
            db,
            row=row,
            event=AUDIT_CREATED,
            occurred_at=now,
            request_id=request_id,
        )
        db.commit()
        db.refresh(row)
        return _metadata(row)

    def retrieve(
        self,
        db: Session,
        *,
        owner: SecretOwner,
        reference: SecretReference | str | UUID,
        operation: lifecycle.RetailerOperation | str = (
            lifecycle.RetailerOperation.PRICE_AVAILABILITY_ACQUISITION
        ),
        expected_version: int | None = None,
    ) -> bytes:
        """Decrypt the ACTIVE version after owner and operation checks.

        There is deliberately no unrestricted ``get_secret(reference)`` API.
        """

        connection = self._require_connection(db, owner)
        op = _coerce_operation(operation)
        if op not in _SECRET_CONSUMING_OPERATIONS:
            raise SecretAccessDenied(
                connection_id=connection.id,
                operation=op.value,
            )
        self._authorize_retrieval(connection, op)
        ref = self._reference(reference)
        row = repository.get_active_by_reference(
            db,
            reference=ref,
            user_id=connection.user_id,
            connection_id=connection.id,
            retailer_id=connection.retailer_id,
        )
        if row is None:
            raise SecretNotFound(ref)
        if expected_version is not None and row.version != expected_version:
            raise SecretVersionConflict(
                expected_version=expected_version,
                actual_version=row.version,
            )
        key = self._key_provider.key_for(row.key_version)
        aad = build_aad(
            user_id=row.user_id,
            connection_id=row.connection_id,
            retailer_id=row.retailer_id,
            secret_type=row.secret_type,
            version=row.version,
            reference=row.reference,
        )
        return self._codec.decrypt(
            nonce=row.nonce or b"",
            ciphertext=row.ciphertext or b"",
            key=key,
            aad=aad,
        )

    def rotate(
        self,
        db: Session,
        *,
        owner: SecretOwner,
        reference: SecretReference | str | UUID,
        plaintext: bytes,
        expected_version: int | None = None,
        request_id: str | None = None,
    ) -> SecretMetadata:
        """Create a new active version and crypto-shred the old material."""

        connection = self._require_connection(db, owner, for_update=True)
        self._authorize_mutation(connection)
        ref = self._reference(reference)
        active = repository.get_active_by_reference(
            db,
            reference=ref,
            user_id=connection.user_id,
            connection_id=connection.id,
            retailer_id=connection.retailer_id,
            for_update=True,
        )
        if active is None:
            db.rollback()
            raise SecretStateConflict("no_active_secret")
        if expected_version is not None and active.version != expected_version:
            actual_version = active.version
            db.rollback()
            raise SecretVersionConflict(
                expected_version=expected_version,
                actual_version=actual_version,
            )

        now = _now(self._clock)
        new_version = active.version + 1
        nonce, ciphertext, key_version = self._encrypt(
            plaintext=plaintext,
            user_id=active.user_id,
            connection_id=active.connection_id,
            retailer_id=active.retailer_id,
            secret_type=SecretType(active.secret_type),
            version=new_version,
            reference=active.reference,
        )

        # Supersede and shred the old version first so the partial unique index
        # admits exactly one ACTIVE row for the reference.
        active.status = SecretStatus.SUPERSEDED.value
        active.superseded_at = now
        active.updated_at = now
        active.nonce = None
        active.ciphertext = None
        db.flush()

        row = CredentialSecret(
            reference=active.reference,
            version=new_version,
            user_id=active.user_id,
            connection_id=active.connection_id,
            retailer_id=active.retailer_id,
            secret_type=active.secret_type,
            status=SecretStatus.ACTIVE.value,
            algorithm=ALGORITHM,
            key_version=key_version,
            nonce=nonce,
            ciphertext=ciphertext,
            rotated_from_id=active.id,
            created_at=now,
            updated_at=now,
        )
        try:
            repository.add(db, row)
        except IntegrityError as exc:
            db.rollback()
            raise SecretStateConflict("rotation_conflict") from exc
        _audit(
            db,
            row=row,
            event=AUDIT_ROTATED,
            occurred_at=now,
            request_id=request_id,
        )
        db.commit()
        db.refresh(row)
        return _metadata(row)

    def replace(
        self,
        db: Session,
        *,
        owner: SecretOwner,
        reference: SecretReference | str | UUID,
        plaintext: bytes,
        expected_version: int | None = None,
        request_id: str | None = None,
    ) -> SecretMetadata:
        """Alias for :meth:`rotate`; replacement always creates a new version."""

        return self.rotate(
            db,
            owner=owner,
            reference=reference,
            plaintext=plaintext,
            expected_version=expected_version,
            request_id=request_id,
        )

    def revoke(
        self,
        db: Session,
        *,
        owner: SecretOwner,
        reference: SecretReference | str | UUID,
        request_id: str | None = None,
    ) -> SecretMetadata:
        """Immediately block retrieval; audit evidence is retained."""

        connection = self._require_connection(db, owner, for_update=True)
        ref = self._reference(reference)
        active = repository.get_active_by_reference(
            db,
            reference=ref,
            user_id=connection.user_id,
            connection_id=connection.id,
            retailer_id=connection.retailer_id,
            for_update=True,
        )
        if active is None:
            latest = repository.get_latest_by_reference(
                db,
                reference=ref,
                user_id=connection.user_id,
                connection_id=connection.id,
                retailer_id=connection.retailer_id,
            )
            result = (
                _metadata(latest)
                if latest is not None and latest.status == SecretStatus.REVOKED.value
                else None
            )
            db.rollback()
            if result is not None:
                return result
            raise SecretStateConflict("no_active_secret")

        now = _now(self._clock)
        active.status = SecretStatus.REVOKED.value
        active.revoked_at = now
        active.updated_at = now
        _audit(
            db,
            row=active,
            event=AUDIT_REVOKED,
            occurred_at=now,
            request_id=request_id,
        )
        db.commit()
        db.refresh(active)
        return _metadata(active)

    def delete(
        self,
        db: Session,
        *,
        owner: SecretOwner,
        reference: SecretReference | str | UUID,
        request_id: str | None = None,
    ) -> None:
        """Cryptographically erase all versions of a revoked secret lineage.

        Deletion is refused while any version is ACTIVE. It nulls nonce and
        ciphertext for every version and records a non-secret audit event.
        Backups, replicas, and immutable storage may retain earlier ciphertext;
        this method cannot erase those copies.
        """

        connection = self._require_connection(db, owner, for_update=True)
        ref = self._reference(reference)
        rows = repository.list_versions_for_reference(
            db,
            reference=ref,
            user_id=connection.user_id,
            connection_id=connection.id,
            retailer_id=connection.retailer_id,
            for_update=True,
        )
        if not rows:
            db.rollback()
            raise SecretNotFound(ref)
        if any(row.status == SecretStatus.ACTIVE.value for row in rows):
            db.rollback()
            raise SecretDeletionDenied("active_secret_must_be_revoked")
        if all(row.status == SecretStatus.DELETED.value for row in rows):
            db.rollback()
            return

        now = _now(self._clock)
        for row in rows:
            row.status = SecretStatus.DELETED.value
            row.deleted_at = now
            row.updated_at = now
            row.nonce = None
            row.ciphertext = None
        _audit(
            db,
            row=rows[-1],
            event=AUDIT_DELETED,
            occurred_at=now,
            request_id=request_id,
        )
        db.commit()

    # ------------------------------------------------------------------
    # Non-secret inspection
    # ------------------------------------------------------------------

    def inspect(
        self,
        db: Session,
        *,
        owner: SecretOwner,
        reference: SecretReference | str | UUID,
    ) -> SecretMetadata:
        """Return non-secret metadata for the newest version."""

        connection = self._require_connection(db, owner)
        ref = self._reference(reference)
        row = repository.get_latest_by_reference(
            db,
            reference=ref,
            user_id=connection.user_id,
            connection_id=connection.id,
            retailer_id=connection.retailer_id,
        )
        if row is None:
            raise SecretNotFound(ref)
        return _metadata(row)

    def list_metadata(
        self,
        db: Session,
        *,
        owner: SecretOwner,
    ) -> list[SecretMetadata]:
        """Return non-secret metadata for every version on the connection."""

        connection = self._require_connection(db, owner)
        rows = repository.list_for_connection(
            db,
            user_id=connection.user_id,
            connection_id=connection.id,
        )
        return [_metadata(row) for row in rows]


__all__ = [
    "CredentialVault",
    "CredentialVaultError",
]
