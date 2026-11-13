"""add retailer connection lifecycle records

Revision ID: 0008_retailer_connections
Revises: 0007_email_outbox
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_retailer_connections"
down_revision = "0007_email_outbox"
branch_labels = None
depends_on = None


_STATUS_IN = (
    "status IN ('PENDING_AUTH', 'CONNECTED', 'DEGRADED', "
    "'REAUTH_REQUIRED', 'REVOKED', 'BLOCKED', 'DISCONNECTED')"
)
_RETAILER_IN = (
    "retailer_id IN ('BIGBASKET', 'BLINKIT', 'FLIPKART_MINUTES', "
    "'INSTAMART', 'ZEPTO')"
)
_REFERENCE_SHAPE = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$"
_AUTH_METHOD_SHAPE = r"^[a-z][a-z0-9_]{0,63}$"


def upgrade() -> None:
    op.add_column(
        "audit_events",
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_table(
        "retailer_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("retailer_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING_AUTH"),
        sa.Column("authentication_method", sa.String(64)),
        sa.Column("external_authorization_reference", sa.String(256)),
        sa.Column("retailer_location_reference", sa.String(256)),
        sa.Column("connected_at", sa.DateTime(timezone=True)),
        sa.Column("last_validated_at", sa.DateTime(timezone=True)),
        sa.Column("last_auth_failure_at", sa.DateTime(timezone=True)),
        sa.Column("reauth_required_at", sa.DateTime(timezone=True)),
        sa.Column("disconnected_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(_STATUS_IN, name="ck_retailer_connections_status"),
        sa.CheckConstraint(_RETAILER_IN, name="ck_retailer_connections_retailer_id"),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_retailer_connections_version_positive",
        ),
        sa.CheckConstraint(
            "status != 'CONNECTED' OR connected_at IS NOT NULL",
            name="ck_retailer_connections_connected_at",
        ),
        sa.CheckConstraint(
            "status != 'REAUTH_REQUIRED' OR reauth_required_at IS NOT NULL",
            name="ck_retailer_connections_reauth_required_at",
        ),
        sa.CheckConstraint(
            "status != 'DISCONNECTED' OR disconnected_at IS NOT NULL",
            name="ck_retailer_connections_disconnected_at",
        ),
        sa.CheckConstraint(
            "external_authorization_reference IS NULL OR "
            f"external_authorization_reference ~ '{_REFERENCE_SHAPE}'",
            name="ck_retailer_connections_external_reference_shape",
        ),
        sa.CheckConstraint(
            "retailer_location_reference IS NULL OR "
            f"retailer_location_reference ~ '{_REFERENCE_SHAPE}'",
            name="ck_retailer_connections_location_reference_shape",
        ),
        sa.CheckConstraint(
            "authentication_method IS NULL OR "
            f"authentication_method ~ '{_AUTH_METHOD_SHAPE}'",
            name="ck_retailer_connections_auth_method_shape",
        ),
    )
    op.create_index(
        "ix_retailer_connections_user_created",
        "retailer_connections",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_retailer_connections_user_retailer_status",
        "retailer_connections",
        ["user_id", "retailer_id", "status"],
    )
    op.create_index(
        "uq_retailer_connections_active_user_retailer",
        "retailer_connections",
        ["user_id", "retailer_id"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('DISCONNECTED', 'REVOKED')"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_retailer_connections_active_user_retailer",
        table_name="retailer_connections",
    )
    op.drop_index(
        "ix_retailer_connections_user_retailer_status",
        table_name="retailer_connections",
    )
    op.drop_index(
        "ix_retailer_connections_user_created",
        table_name="retailer_connections",
    )
    op.drop_table("retailer_connections")
    op.drop_column("audit_events", "payload")
