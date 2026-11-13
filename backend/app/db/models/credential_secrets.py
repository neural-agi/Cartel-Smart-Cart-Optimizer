"""Encrypted, owner-bound credential secret versions.

The table stores ciphertext only. Plaintext credentials never enter the
database, audit events, logs, or model representations. The model deliberately
has a safe ``__repr__`` and exposes no property that decrypts material.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.credential_vault.crypto import ALGORITHM, NONCE_BYTES
from app.credential_vault.types import SecretStatus, SecretType
from app.db.base import Base

_SECRET_TYPE_VALUES = ", ".join(f"'{value.value}'" for value in SecretType)
_STATUS_VALUES = ", ".join(f"'{value.value}'" for value in SecretStatus)
_KEY_VERSION_SHAPE = r"^[a-z0-9][a-z0-9._-]{0,63}$"


class CredentialSecret(Base):
    """One encrypted version of a secret bound to a persisted connection."""

    __tablename__ = "credential_secrets"
    __table_args__ = (
        # The composite FK makes cross-user / cross-retailer binding impossible
        # even for a direct SQL writer that bypasses the service.
        ForeignKeyConstraint(
            ["connection_id", "user_id", "retailer_id"],
            [
                "retailer_connections.id",
                "retailer_connections.user_id",
                "retailer_connections.retailer_id",
            ],
            name="fk_credential_secrets_connection_owner_retailer",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "reference",
            "version",
            name="uq_credential_secrets_reference_version",
        ),
        CheckConstraint("version >= 1", name="ck_credential_secrets_version_positive"),
        CheckConstraint(
            f"status IN ({_STATUS_VALUES})",
            name="ck_credential_secrets_status",
        ),
        CheckConstraint(
            f"secret_type IN ({_SECRET_TYPE_VALUES})",
            name="ck_credential_secrets_type",
        ),
        CheckConstraint(
            f"algorithm = '{ALGORITHM}'",
            name="ck_credential_secrets_algorithm",
        ),
        CheckConstraint(
            f"key_version ~ '{_KEY_VERSION_SHAPE}'",
            name="ck_credential_secrets_key_version_shape",
        ),
        CheckConstraint(
            f"nonce IS NULL OR octet_length(nonce) = {NONCE_BYTES}",
            name="ck_credential_secrets_nonce_length",
        ),
        CheckConstraint(
            "ciphertext IS NULL OR octet_length(ciphertext) >= 16",
            name="ck_credential_secrets_ciphertext_length",
        ),
        CheckConstraint(
            "status != 'ACTIVE' OR (nonce IS NOT NULL AND ciphertext IS NOT NULL)",
            name="ck_credential_secrets_active_material",
        ),
        CheckConstraint(
            "status != 'REVOKED' OR revoked_at IS NOT NULL",
            name="ck_credential_secrets_revoked_at",
        ),
        CheckConstraint(
            "status != 'DELETED' OR deleted_at IS NOT NULL",
            name="ck_credential_secrets_deleted_at",
        ),
        CheckConstraint(
            "status != 'DELETED' OR (nonce IS NULL AND ciphertext IS NULL)",
            name="ck_credential_secrets_deleted_shredded",
        ),
        Index(
            "ix_credential_secrets_user_connection",
            "user_id",
            "connection_id",
        ),
        Index(
            "ix_credential_secrets_user_retailer",
            "user_id",
            "retailer_id",
        ),
        Index(
            "ix_credential_secrets_reference_owner",
            "reference",
            "user_id",
            "connection_id",
            "retailer_id",
        ),
        # At most one ACTIVE version per opaque reference. Rotation inserts a
        # new version and supersedes the old one in the same transaction.
        Index(
            "uq_credential_secrets_active_reference",
            "reference",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    reference: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    connection_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    retailer_id: Mapped[str] = mapped_column(String(32), nullable=False)
    secret_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=SecretStatus.ACTIVE.value,
        server_default=SecretStatus.ACTIVE.value,
    )
    algorithm: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ALGORITHM,
        server_default=ALGORITHM,
    )
    key_version: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    rotated_from_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("credential_secrets.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        """Never include nonce or ciphertext in a representation."""

        return (
            "CredentialSecret("
            f"id={self.id}, reference={self.reference}, version={self.version}, "
            f"secret_type={self.secret_type!r}, status={self.status!r})"
        )

    __str__ = __repr__
