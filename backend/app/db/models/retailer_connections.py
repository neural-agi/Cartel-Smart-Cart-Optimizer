"""Persistent, user-owned retailer connection lifecycle records.

This model stores only lifecycle metadata and non-secret references. It must
never contain passwords, OTPs, access/refresh tokens, cookies, or browser
session material; the external authorization reference is a non-secret
identifier by definition.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.retailer_connections.lifecycle import (
    SUPPORTED_RETAILER_IDS,
    RestrictionCategory,
    RestrictionSource,
    RetailerConnectionStatus,
)

_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in RetailerConnectionStatus)
_RETAILER_VALUES = ", ".join(f"'{value}'" for value in sorted(SUPPORTED_RETAILER_IDS))
_RESTRICTION_SOURCE_VALUES = ", ".join(
    f"'{source.value}'" for source in RestrictionSource
)
_RESTRICTION_CATEGORY_VALUES = ", ".join(
    f"'{category.value}'" for category in RestrictionCategory
)
_REFERENCE_SHAPE = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$"
_AUTH_METHOD_SHAPE = r"^[a-z][a-z0-9_]{0,63}$"


class RetailerConnection(Base):
    """One user's durable lifecycle relationship with one retailer."""

    __tablename__ = "retailer_connections"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_STATUS_VALUES})",
            name="ck_retailer_connections_status",
        ),
        CheckConstraint(
            f"retailer_id IN ({_RETAILER_VALUES})",
            name="ck_retailer_connections_retailer_id",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_retailer_connections_version_positive",
        ),
        CheckConstraint(
            "status != 'CONNECTED' OR connected_at IS NOT NULL",
            name="ck_retailer_connections_connected_at",
        ),
        CheckConstraint(
            "status != 'REAUTH_REQUIRED' OR reauth_required_at IS NOT NULL",
            name="ck_retailer_connections_reauth_required_at",
        ),
        CheckConstraint(
            "status != 'DISCONNECTED' OR disconnected_at IS NOT NULL",
            name="ck_retailer_connections_disconnected_at",
        ),
        CheckConstraint(
            "external_authorization_reference IS NULL OR "
            f"external_authorization_reference ~ '{_REFERENCE_SHAPE}'",
            name="ck_retailer_connections_external_reference_shape",
        ),
        CheckConstraint(
            "retailer_location_reference IS NULL OR "
            f"retailer_location_reference ~ '{_REFERENCE_SHAPE}'",
            name="ck_retailer_connections_location_reference_shape",
        ),
        CheckConstraint(
            "authentication_method IS NULL OR "
            f"authentication_method ~ '{_AUTH_METHOD_SHAPE}'",
            name="ck_retailer_connections_auth_method_shape",
        ),
        CheckConstraint(
            "status != 'BLOCKED' OR (blocked_at IS NOT NULL "
            "AND blocked_source IS NOT NULL AND blocked_category IS NOT NULL)",
            name="ck_retailer_connections_blocked_metadata",
        ),
        CheckConstraint(
            "blocked_source IS NULL OR "
            f"blocked_source IN ({_RESTRICTION_SOURCE_VALUES})",
            name="ck_retailer_connections_blocked_source",
        ),
        CheckConstraint(
            "blocked_category IS NULL OR "
            f"blocked_category IN ({_RESTRICTION_CATEGORY_VALUES})",
            name="ck_retailer_connections_blocked_category",
        ),
        # Composite uniqueness lets the credential vault bind a secret to the
        # persisted owner + connection + retailer at the database level.
        UniqueConstraint(
            "id",
            "user_id",
            name="uq_retailer_connections_id_user",
        ),
        UniqueConstraint(
            "id",
            "user_id",
            "retailer_id",
            name="uq_retailer_connections_id_user_retailer",
        ),
        Index("ix_retailer_connections_user_created", "user_id", "created_at"),
        Index(
            "ix_retailer_connections_user_retailer_status",
            "user_id",
            "retailer_id",
            "status",
        ),
        # At most one non-terminal connection per user+retailer. A new record
        # may be created after DISCONNECTED or REVOKED, which is why both
        # terminal states are excluded.
        Index(
            "uq_retailer_connections_active_user_retailer",
            "user_id",
            "retailer_id",
            unique=True,
            postgresql_where=text("status NOT IN ('DISCONNECTED', 'REVOKED')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    retailer_id: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RetailerConnectionStatus.PENDING_AUTH.value,
        server_default=RetailerConnectionStatus.PENDING_AUTH.value,
    )
    authentication_method: Mapped[str | None] = mapped_column(String(64))
    external_authorization_reference: Mapped[str | None] = mapped_column(String(256))
    retailer_location_reference: Mapped[str | None] = mapped_column(String(256))
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_auth_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reauth_required_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Explicit BLOCKED restriction provenance. Retained as historical metadata
    # after the connection leaves BLOCKED; a new record starts with all null.
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_source: Mapped[str | None] = mapped_column(String(32))
    blocked_category: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # The lifecycle service writes this from the injected clock on every real
    # transition. No ORM onupdate is used, so a frozen test clock cannot be
    # overwritten by the database wall clock.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
