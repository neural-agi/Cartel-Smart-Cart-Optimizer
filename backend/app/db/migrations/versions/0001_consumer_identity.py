"""Initial consumer identity schema.

Revision ID: 0001_consumer_identity
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_consumer_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(320), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "subject", name="uq_identities_provider_subject"),
    )
    op.create_index("ix_identities_user_id", "identities", ["user_id"])
    op.create_table(
        "password_credentials",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoke_reason", sa.String(32)),
        sa.Column("user_agent_hash", sa.String(64)),
    )
    op.create_index("ix_sessions_user_active", "sessions", ["user_id", "revoked_at", "expires_at"])
    op.create_table(
        "verification_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_verification_challenges_user_purpose", "verification_challenges", ["user_id", "purpose"])
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("object_type", sa.String(64)),
        sa.Column("object_id", sa.String(64)),
        sa.Column("request_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_events_user_created", "audit_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_user_created", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_verification_challenges_user_purpose", table_name="verification_challenges")
    op.drop_table("verification_challenges")
    op.drop_index("ix_sessions_user_active", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("password_credentials")
    op.drop_index("ix_identities_user_id", table_name="identities")
    op.drop_table("identities")
    op.drop_table("users")
