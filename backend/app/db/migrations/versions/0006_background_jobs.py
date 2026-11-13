"""add durable background jobs

Revision ID: 0006_background_jobs
Revises: 0005_idempotency_records
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_background_jobs"
down_revision = "0005_idempotency_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("owner_reference", sa.String(128)),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(512)),
        sa.Column("request_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')", name="ck_background_jobs_status"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_background_jobs_attempt_count"),
        sa.CheckConstraint("max_attempts > 0", name="ck_background_jobs_max_attempts"),
        sa.UniqueConstraint("owner_reference", "job_type", "idempotency_key", name="uq_background_jobs_owner_type_key"),
    )
    op.create_index("ix_background_jobs_claim", "background_jobs", ["status", "available_at", "created_at"])
    op.create_index("ix_background_jobs_leases", "background_jobs", ["status", "lease_expires_at"])
    op.create_index("ix_background_jobs_owner_created", "background_jobs", ["owner_user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_background_jobs_owner_created", table_name="background_jobs")
    op.drop_index("ix_background_jobs_leases", table_name="background_jobs")
    op.drop_index("ix_background_jobs_claim", table_name="background_jobs")
    op.drop_table("background_jobs")
