"""Persist consumer optimization requests, plans, and allocations.

Revision ID: 0003_optimization_records
Revises: 0002_shopping_lists
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_optimization_records"
down_revision = "0002_shopping_lists"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "optimization_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shopping_list_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("list_revision", sa.Integer(), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("list_revision > 0", name="ck_optimization_requests_positive_revision"),
        sa.CheckConstraint("status IN ('ready', 'unresolved', 'unavailable', 'infeasible', 'no_plan')", name="ck_optimization_requests_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shopping_list_id", "user_id"], ["shopping_lists.id", "shopping_lists.user_id"], name="fk_optimization_requests_list_owner", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "request_id", name="uq_optimization_requests_user_request"),
        sa.UniqueConstraint("user_id", "shopping_list_id", "list_revision", "input_digest", "policy_version", name="uq_optimization_requests_idempotency"),
        sa.UniqueConstraint("id", "user_id", name="uq_optimization_requests_id_user"),
    )
    op.create_index("ix_optimization_requests_owner_created", "optimization_requests", ["user_id", "created_at"])
    op.create_table(
        "optimization_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", sa.String(128), nullable=False),
        sa.Column("feasibility", sa.String(32), nullable=False),
        sa.Column("ranking_position", sa.Integer(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("plan_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("feasibility IN ('feasible', 'infeasible', 'unresolved', 'invalid', 'rejected')", name="ck_optimization_plans_feasibility"),
        sa.ForeignKeyConstraint(["request_record_id", "user_id"], ["optimization_requests.id", "optimization_requests.user_id"], name="fk_optimization_plans_request_owner", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_record_id", "plan_id", name="uq_optimization_plans_request_plan"),
        sa.UniqueConstraint("id", "user_id", name="uq_optimization_plans_id_user"),
    )
    op.create_table(
        "optimization_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id_snapshot", sa.String(128), nullable=False),
        sa.Column("canonical_product_id", sa.String(128), nullable=False),
        sa.Column("canonical_variant_id", sa.String(128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("retailer_id", sa.String(128), nullable=False),
        sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("platform_listing_id", sa.String(256), nullable=False),
        sa.Column("observation_id", sa.String(128), nullable=False),
        sa.Column("checkout_group_id", sa.String(128), nullable=False),
        sa.Column("evidence_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_optimization_allocations_positive_quantity"),
        sa.ForeignKeyConstraint(["plan_record_id", "user_id"], ["optimization_plans.id", "optimization_plans.user_id"], name="fk_optimization_allocations_plan_owner", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_optimization_allocations_owner_plan", "optimization_allocations", ["user_id", "plan_record_id"])


def downgrade() -> None:
    op.drop_index("ix_optimization_allocations_owner_plan", table_name="optimization_allocations")
    op.drop_table("optimization_allocations")
    op.drop_table("optimization_plans")
    op.drop_index("ix_optimization_requests_owner_created", table_name="optimization_requests")
    op.drop_table("optimization_requests")
