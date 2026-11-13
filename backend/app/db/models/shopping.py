"""User-owned shopping-list intent and persisted items."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShoppingList(Base):
    __tablename__ = "shopping_lists"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_shopping_lists_id_user"),
        Index("ix_shopping_lists_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="shopping_lists")
    items: Mapped[list["ShoppingListItem"]] = relationship(
        back_populates="shopping_list", cascade="all, delete-orphan", order_by="ShoppingListItem.created_at"
    )


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["list_id", "user_id"],
            ["shopping_lists.id", "shopping_lists.user_id"],
            name="fk_shopping_list_items_list_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint("quantity > 0 AND quantity <= 999", name="ck_shopping_list_items_quantity_range"),
        CheckConstraint(
            "(canonical_product_id IS NULL) = (canonical_variant_id IS NULL)",
            name="ck_shopping_list_items_canonical_pair",
        ),
        CheckConstraint(
            "(source_platform IS NULL AND source_listing_id IS NULL AND source_observation_id IS NULL) OR "
            "(source_platform IS NOT NULL AND source_listing_id IS NOT NULL AND source_observation_id IS NOT NULL)",
            name="ck_shopping_list_items_source_complete",
        ),
        CheckConstraint(
            "resolution_status IN ('unresolved', 'exact_confirmed')",
            name="ck_shopping_list_items_resolution_status",
        ),
        CheckConstraint(
            "resolution_status != 'exact_confirmed' OR "
            "(canonical_product_id IS NOT NULL AND source_observation_id IS NOT NULL)",
            name="ck_shopping_list_items_confirmed_evidence",
        ),
        Index("ix_shopping_list_items_owner_list", "user_id", "list_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    list_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    query: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit: Mapped[str | None] = mapped_column(String(32))
    resolution_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unresolved")
    canonical_product_id: Mapped[str | None] = mapped_column(String(128))
    canonical_variant_id: Mapped[str | None] = mapped_column(String(128))
    display_name_snapshot: Mapped[str | None] = mapped_column(String(300))
    source_platform: Mapped[str | None] = mapped_column(String(64))
    source_listing_id: Mapped[str | None] = mapped_column(String(256))
    source_observation_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    shopping_list: Mapped[ShoppingList] = relationship(back_populates="items")
