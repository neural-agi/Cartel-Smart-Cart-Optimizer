"""Owner-scoped persistence queries for credential secrets.

Every query filters by the persisted owner, connection, and retailer. A caller
that supplies another user's identifiers sees the same result as a caller that
supplies a nonexistent reference.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.credential_vault.types import SecretStatus
from app.db.models.credential_secrets import CredentialSecret
from app.db.models.retailer_connections import RetailerConnection


def get_connection_for_owner(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    for_update: bool = False,
) -> RetailerConnection | None:
    """Load the persisted connection that owns a secret."""

    statement = select(RetailerConnection).where(
        RetailerConnection.id == connection_id,
        RetailerConnection.user_id == user_id,
    )
    if for_update:
        statement = statement.with_for_update().execution_options(
            populate_existing=True
        )
    return db.scalar(statement)


def get_active_by_reference(
    db: Session,
    *,
    reference: UUID,
    user_id: UUID,
    connection_id: UUID,
    retailer_id: str,
    for_update: bool = False,
) -> CredentialSecret | None:
    """Return the one ACTIVE version bound to the full owner context."""

    statement = select(CredentialSecret).where(
        CredentialSecret.reference == reference,
        CredentialSecret.user_id == user_id,
        CredentialSecret.connection_id == connection_id,
        CredentialSecret.retailer_id == retailer_id,
        CredentialSecret.status == SecretStatus.ACTIVE.value,
    )
    if for_update:
        # populate_existing re-reads the row after a lock wait, so a concurrent
        # rotation is observed rather than served from the identity map.
        statement = statement.with_for_update().execution_options(
            populate_existing=True
        )
    return db.scalar(statement)


def get_latest_by_reference(
    db: Session,
    *,
    reference: UUID,
    user_id: UUID,
    connection_id: UUID,
    retailer_id: str,
) -> CredentialSecret | None:
    """Return the newest version for non-secret metadata inspection."""

    return db.scalar(
        select(CredentialSecret)
        .where(
            CredentialSecret.reference == reference,
            CredentialSecret.user_id == user_id,
            CredentialSecret.connection_id == connection_id,
            CredentialSecret.retailer_id == retailer_id,
        )
        .order_by(CredentialSecret.version.desc())
        .limit(1)
    )


def list_versions_for_reference(
    db: Session,
    *,
    reference: UUID,
    user_id: UUID,
    connection_id: UUID,
    retailer_id: str,
    for_update: bool = False,
) -> list[CredentialSecret]:
    """Return every version of one reference, optionally locking them."""

    statement = (
        select(CredentialSecret)
        .where(
            CredentialSecret.reference == reference,
            CredentialSecret.user_id == user_id,
            CredentialSecret.connection_id == connection_id,
            CredentialSecret.retailer_id == retailer_id,
        )
        .order_by(CredentialSecret.version)
    )
    if for_update:
        statement = statement.with_for_update().execution_options(
            populate_existing=True
        )
    return list(db.scalars(statement).all())


def list_for_connection(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
) -> list[CredentialSecret]:
    """Return all secret versions for one owner-scoped connection."""

    return list(
        db.scalars(
            select(CredentialSecret)
            .where(
                CredentialSecret.user_id == user_id,
                CredentialSecret.connection_id == connection_id,
            )
            .order_by(CredentialSecret.created_at, CredentialSecret.version)
        ).all()
    )


def add(db: Session, secret: CredentialSecret) -> CredentialSecret:
    """Stage a new secret version and flush so constraints run now."""

    db.add(secret)
    db.flush()
    return secret
