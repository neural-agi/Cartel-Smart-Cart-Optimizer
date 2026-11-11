"""PostgreSQL fixtures for retailer-connection integration tests.

These tests intentionally require the project's real database engine. SQLite is
not an acceptable substitute for row locks, partial unique indexes, or the
PostgreSQL CHECK constraints exercised here.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import AuditEvent, User
from app.db.models.retailer_connections import RetailerConnection
from app.retailer_connections.lifecycle import RetailerConnectionStatus
from tests.unit.timestamp_support import FrozenClock

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 6, 1, 12, 5, tzinfo=timezone.utc)


def database_url() -> str:
    value = os.environ.get("CARTEL_TEST_DATABASE_URL", "")
    if not value:
        pytest.skip(
            "set CARTEL_TEST_DATABASE_URL to a disposable PostgreSQL database; "
            "SQLite is not supported"
        )
    if value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
        os.environ["CARTEL_TEST_DATABASE_URL"] = value
    if not value.startswith("postgresql+psycopg://"):
        pytest.fail("CARTEL_TEST_DATABASE_URL must be PostgreSQL")
    return value


def alembic_config() -> Config:
    return Config(str(Path(__file__).parents[3] / "alembic.ini"))


def _drop_all_tables(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DO $$
                DECLARE
                    item RECORD;
                BEGIN
                    FOR item IN
                        SELECT tablename FROM pg_tables
                        WHERE schemaname = current_schema()
                    LOOP
                        EXECUTE 'DROP TABLE IF EXISTS "' || item.tablename || '" CASCADE';
                    END LOOP;
                END $$;
                """
            )
        )


@pytest.fixture(scope="module")
def pg_engine():
    url = database_url()
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any connection failure means skip
        engine.dispose()
        pytest.skip(f"disposable PostgreSQL is not reachable: {type(exc).__name__}")

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    config = alembic_config()
    try:
        _drop_all_tables(engine)
        command.upgrade(config, "head")
        yield engine
        command.downgrade(config, "base")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()
        engine.dispose()


@pytest.fixture
def session_factory(pg_engine) -> sessionmaker[Session]:
    return sessionmaker(bind=pg_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory) -> Session:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(NOW)


@pytest.fixture
def make_user(db_session: Session):
    def _make_user() -> User:
        user = User(id=uuid4(), status="active")
        db_session.add(user)
        db_session.commit()
        return user

    return _make_user


@pytest.fixture
def make_connection(db_session: Session):
    def _make_connection(
        *,
        user_id: UUID,
        status: RetailerConnectionStatus,
        retailer_id: str = "ZEPTO",
        version: int = 1,
        **overrides: object,
    ) -> RetailerConnection:
        connected_at = (
            NOW
            if status
            in {
                RetailerConnectionStatus.CONNECTED,
                RetailerConnectionStatus.DEGRADED,
                RetailerConnectionStatus.REAUTH_REQUIRED,
            }
            else None
        )
        connection = RetailerConnection(
            user_id=user_id,
            retailer_id=retailer_id,
            status=status.value,
            version=version,
            created_at=NOW,
            updated_at=NOW,
            connected_at=connected_at,
            last_validated_at=connected_at,
            last_auth_failure_at=(
                NOW if status == RetailerConnectionStatus.REAUTH_REQUIRED else None
            ),
            reauth_required_at=(
                NOW if status == RetailerConnectionStatus.REAUTH_REQUIRED else None
            ),
            disconnected_at=(
                NOW if status == RetailerConnectionStatus.DISCONNECTED else None
            ),
            blocked_at=(
                NOW if status == RetailerConnectionStatus.BLOCKED else None
            ),
            blocked_source=(
                "retailer" if status == RetailerConnectionStatus.BLOCKED else None
            ),
            blocked_category=(
                "account_suspended"
                if status == RetailerConnectionStatus.BLOCKED
                else None
            ),
            **overrides,
        )
        db_session.add(connection)
        db_session.commit()
        db_session.refresh(connection)
        return connection

    return _make_connection


def audit_events_for(session: Session, connection_id: UUID) -> list[AuditEvent]:
    return list(
        session.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.object_type == "retailer_connection",
                AuditEvent.object_id == str(connection_id),
            )
            .order_by(AuditEvent.created_at, AuditEvent.id)
        ).all()
    )
