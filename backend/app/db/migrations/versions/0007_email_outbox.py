"""add transactional email outbox

Revision ID: 0007_email_outbox
Revises: 0006_background_jobs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_email_outbox"
down_revision = "0006_background_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_key", sa.String(256), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("recipient", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(320), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(512)),
        sa.Column("request_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending', 'processing', 'sent', 'failed')", name="ck_email_outbox_status"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_email_outbox_attempt_count"),
        sa.UniqueConstraint("event_key", name="uq_email_outbox_event_key"),
    )
    op.create_index("ix_email_outbox_claim", "email_outbox_events", ["status", "available_at", "created_at"])
    op.create_index("ix_email_outbox_leases", "email_outbox_events", ["status", "lease_expires_at"])
    op.create_index("ix_email_outbox_type", "email_outbox_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_email_outbox_type", table_name="email_outbox_events")
    op.drop_index("ix_email_outbox_leases", table_name="email_outbox_events")
    op.drop_index("ix_email_outbox_claim", table_name="email_outbox_events")
    op.drop_table("email_outbox_events")
