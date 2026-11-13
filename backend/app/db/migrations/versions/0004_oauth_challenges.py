"""Persist one-use OAuth state, nonce, and PKCE transactions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_oauth_challenges"
down_revision = "0003_optimization_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("nonce", sa.String(128), nullable=False),
        sa.Column("code_verifier", sa.String(128), nullable=False),
        sa.Column("redirect_uri", sa.String(512), nullable=False),
        sa.Column("next_path", sa.String(512), nullable=False, server_default="/home"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("state_hash", name="uq_oauth_challenges_state_hash"),
    )
    op.create_index("ix_oauth_challenges_expires", "oauth_challenges", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_oauth_challenges_expires", table_name="oauth_challenges")
    op.drop_table("oauth_challenges")
