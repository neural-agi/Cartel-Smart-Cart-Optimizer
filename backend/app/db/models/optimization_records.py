"""Immutable consumer optimization request, plan, and allocation snapshots."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OptimizationRequestRecord(Base):
    __tablename__ = "optimization_requests"
    __table_args__ = (
        CheckConstraint("list_revision > 0", name="ck_optimization_requests_positive_revision"),
        CheckConstraint(
            "status IN ('ready', 'unresolved', 'unavailable', 'infeasible', 'no_plan')",
            name="ck_optimization_requests_status",
        ),
        ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["shopping_list_id", "user_id"],
            ["shopping_lists.id", "shopping_lists.user_id"],
            name="fk_optimization_requests_list_owner",
            ondelete="CASCADE",
        ),
        UniqueConstraint("user_id", "request_id", name="uq_optimization_requests_user_request"),
        UniqueConstraint(
            "user_id", "shopping_list_id", "list_revision", "input_digest", "policy_version",
            name="uq_optimization_requests_idempotency",
        ),
        UniqueConstraint("id", "user_id", name="uq_optimization_requests_id_user"),
        Index("ix_optimization_requests_owner_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    shopping_list_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    list_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OptimizationPlanRecord(Base):
    __tablename__ = "optimization_plans"
    __table_args__ = (
        CheckConstraint(
            "feasibility IN ('feasible', 'infeasible', 'unresolved', 'invalid', 'rejected')",
            name="ck_optimization_plans_feasibility",
        ),
        ForeignKeyConstraint(
            ["request_record_id", "user_id"],
            ["optimization_requests.id", "optimization_requests.user_id"],
            name="fk_optimization_plans_request_owner",
            ondelete="CASCADE",
        ),
        UniqueConstraint("request_record_id", "plan_id", name="uq_optimization_plans_request_plan"),
        UniqueConstraint("id", "user_id", name="uq_optimization_plans_id_user"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    request_record_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(128), nullable=False)
    feasibility: Mapped[str] = mapped_column(String(32), nullable=False)
    ranking_position: Mapped[int | None] = mapped_column(Integer)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    plan_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)


class OptimizationAllocationRecord(Base):
    __tablename__ = "optimization_allocations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_optimization_allocations_positive_quantity"),
        ForeignKeyConstraint(
            ["plan_record_id", "user_id"],
            ["optimization_plans.id", "optimization_plans.user_id"],
            name="fk_optimization_allocations_plan_owner",
            ondelete="CASCADE",
        ),
        Index("ix_optimization_allocations_owner_plan", "user_id", "plan_record_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    plan_record_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    item_id_snapshot: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_product_id: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_variant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    retailer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    platform_listing_id: Mapped[str] = mapped_column(String(256), nullable=False)
    observation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    checkout_group_id: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
