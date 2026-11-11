"""Exercise the retailer-connection migration in both directions."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from tests.integration.retailer_connections.conftest import (
    alembic_config,
    database_url,
)

MIGRATION_DATABASE = "cartel_retailer_connections_migration_test"


def _admin_engine(url: str):
    parsed = make_url(url)
    return create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")


def _target_url(url: str) -> str:
    parsed = make_url(url)
    return parsed.set(database=MIGRATION_DATABASE).render_as_string(hide_password=False)


def _table_exists(engine, name: str = "retailer_connections") -> bool:
    with engine.connect() as connection:
        return connection.execute(
            text(f"SELECT to_regclass('public.{name}')")
        ).scalar_one() is not None


def _column_exists(engine, table: str, column: str) -> bool:
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :column"
            ),
            {"table": table, "column": column},
        ).scalar_one() == 1


def _payload_column_exists(engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'audit_events' AND column_name = 'payload'"
            )
        ).scalar_one() == 1


def _index_names(engine, table: str = "retailer_connections") -> set[str]:
    with engine.connect() as connection:
        return set(
            connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = current_schema() "
                    "AND tablename = :table"
                ),
                {"table": table},
            ).scalars()
        )


def test_migration_upgrade_downgrade_upgrade_and_drift_check() -> None:
    url = database_url()
    admin = _admin_engine(url)
    target_url = _target_url(url)
    target = create_engine(target_url, pool_pre_ping=True)
    previous = os.environ.get("DATABASE_URL")
    try:
        try:
            with admin.connect() as connection:
                connection.execute(
                    text(f'DROP DATABASE IF EXISTS "{MIGRATION_DATABASE}" WITH (FORCE)')
                )
                connection.execute(text(f'CREATE DATABASE "{MIGRATION_DATABASE}"'))
        except Exception as exc:  # noqa: BLE001 - any creation failure means skip
            pytest.skip(
                "test database user cannot create a disposable migration database: "
                f"{type(exc).__name__}"
            )

        os.environ["DATABASE_URL"] = target_url
        get_settings.cache_clear()
        config = alembic_config()

        command.upgrade(config, "head")
        assert _table_exists(target)
        assert _table_exists(target, "credential_secrets")
        assert _payload_column_exists(target)
        assert _column_exists(target, "retailer_connections", "blocked_at")
        assert _column_exists(target, "retailer_connections", "blocked_source")
        assert _column_exists(target, "retailer_connections", "blocked_category")
        assert {
            "ix_retailer_connections_user_created",
            "ix_retailer_connections_user_retailer_status",
            "uq_retailer_connections_active_user_retailer",
        } <= _index_names(target)
        assert {
            "ix_credential_secrets_user_connection",
            "ix_credential_secrets_user_retailer",
            "ix_credential_secrets_reference_owner",
            "uq_credential_secrets_active_reference",
        } <= _index_names(target, "credential_secrets")

        heads = ScriptDirectory.from_config(config).get_heads()
        assert heads == ["0009_credential_vault"]

        # 0009 must be reversible without destroying the Phase F table.
        command.downgrade(config, "0008_retailer_connections")
        assert _table_exists(target)
        assert not _table_exists(target, "credential_secrets")
        assert not _column_exists(target, "retailer_connections", "blocked_at")
        assert not _column_exists(target, "retailer_connections", "blocked_source")
        assert not _column_exists(target, "retailer_connections", "blocked_category")

        command.downgrade(config, "0007_email_outbox")
        assert not _table_exists(target)
        assert not _payload_column_exists(target)
        assert _index_names(target) == set()

        command.upgrade(config, "head")
        assert _table_exists(target)
        assert _table_exists(target, "credential_secrets")
        assert _payload_column_exists(target)

        # Raises AutogenerateDiffsDetected if the ORM metadata and the migrated
        # schema have drifted.
        command.check(config)
    finally:
        target.dispose()
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()
        try:
            with admin.connect() as connection:
                connection.execute(
                    text(f'DROP DATABASE IF EXISTS "{MIGRATION_DATABASE}" WITH (FORCE)')
                )
        finally:
            admin.dispose()
