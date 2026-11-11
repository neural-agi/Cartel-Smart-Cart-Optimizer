"""Owner-scoped persistence queries for retailer connections.

Every read filters by ``user_id`` at the query level. A record owned by another
user is indistinguishable from a record that does not exist; the service maps
both to :class:`~app.retailer_connections.lifecycle.RetailerConnectionNotFound`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.retailer_connections import RetailerConnection
from app.retailer_connections.lifecycle import TERMINAL_STATES


def get_owned(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    for_update: bool = False,
) -> RetailerConnection | None:
    """Return one owner-scoped connection, optionally taking a row lock."""

    statement = select(RetailerConnection).where(
        RetailerConnection.id == connection_id,
        RetailerConnection.user_id == user_id,
    )
    if for_update:
        # populate_existing forces the locked row to overwrite any stale object
        # already in the session identity map, so the version check observes the
        # value another writer committed.
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return db.scalar(statement)


def list_owned(db: Session, *, user_id: UUID) -> list[RetailerConnection]:
    """Return all connections owned by ``user_id``, newest first."""

    return list(
        db.scalars(
            select(RetailerConnection)
            .where(RetailerConnection.user_id == user_id)
            .order_by(RetailerConnection.created_at.desc(), RetailerConnection.id)
        ).all()
    )


def find_non_terminal(
    db: Session,
    *,
    user_id: UUID,
    retailer_id: str,
) -> RetailerConnection | None:
    """Return the owner's non-terminal connection for one retailer, if any."""

    terminal_values = tuple(status.value for status in TERMINAL_STATES)
    return db.scalar(
        select(RetailerConnection).where(
            RetailerConnection.user_id == user_id,
            RetailerConnection.retailer_id == retailer_id,
            RetailerConnection.status.not_in(terminal_values),
        )
    )


def add(db: Session, connection: RetailerConnection) -> RetailerConnection:
    """Stage a new connection and flush so database constraints run now."""

    db.add(connection)
    db.flush()
    return connection
