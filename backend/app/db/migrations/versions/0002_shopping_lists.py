"""Add user-owned shopping lists and requested items.

Revision ID: 0002_shopping_lists
Revises: 0001_consumer_identity
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_shopping_lists"
down_revision = "0001_consumer_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopping_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_shopping_lists_id_user"),
    )
    op.create_index("ix_shopping_lists_user_updated", "shopping_lists", ["user_id", "updated_at"])
    op.create_table(
        "shopping_list_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("list_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query", sa.String(length=300), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("resolution_status", sa.String(length=32), server_default="unresolved", nullable=False),
        sa.Column("canonical_product_id", sa.String(length=128), nullable=True),
        sa.Column("canonical_variant_id", sa.String(length=128), nullable=True),
        sa.Column("display_name_snapshot", sa.String(length=300), nullable=True),
        sa.Column("source_platform", sa.String(length=64), nullable=True),
        sa.Column("source_listing_id", sa.String(length=256), nullable=True),
        sa.Column("source_observation_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity > 0 AND quantity <= 999", name="ck_shopping_list_items_quantity_range"),
        sa.CheckConstraint(
            "(canonical_product_id IS NULL) = (canonical_variant_id IS NULL)",
            name="ck_shopping_list_items_canonical_pair",
        ),
        sa.CheckConstraint(
            "(source_platform IS NULL AND source_listing_id IS NULL AND source_observation_id IS NULL) OR "
            "(source_platform IS NOT NULL AND source_listing_id IS NOT NULL AND source_observation_id IS NOT NULL)",
            name="ck_shopping_list_items_source_complete",
        ),
        sa.CheckConstraint(
            "resolution_status IN ('unresolved', 'exact_confirmed')",
            name="ck_shopping_list_items_resolution_status",
        ),
        sa.CheckConstraint(
            "resolution_status != 'exact_confirmed' OR "
            "(canonical_product_id IS NOT NULL AND source_observation_id IS NOT NULL)",
            name="ck_shopping_list_items_confirmed_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["list_id", "user_id"],
            ["shopping_lists.id", "shopping_lists.user_id"],
            name="fk_shopping_list_items_list_owner",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shopping_list_items_owner_list", "shopping_list_items", ["user_id", "list_id"])


def downgrade() -> None:
    op.drop_index("ix_shopping_list_items_owner_list", table_name="shopping_list_items")
    op.drop_table("shopping_list_items")
    op.drop_index("ix_shopping_lists_user_updated", table_name="shopping_lists")
    op.drop_table("shopping_lists")
