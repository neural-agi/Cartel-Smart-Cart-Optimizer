"""Database-level constraint tests for retailer connections."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.integration.retailer_connections.conftest import NOW


def _insert(
    engine,
    *,
    user_id,
    retailer_id: str = "BLINKIT",
    status: str = "PENDING_AUTH",
    version: int = 1,
    connected_at=None,
    reauth_required_at=None,
    disconnected_at=None,
    external_authorization_reference=None,
    retailer_location_reference=None,
    authentication_method=None,
    blocked_at=None,
    blocked_source=None,
    blocked_category=None,
):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO retailer_connections (
                    id, user_id, retailer_id, status, version,
                    created_at, updated_at, connected_at, reauth_required_at,
                    disconnected_at, external_authorization_reference,
                    retailer_location_reference, authentication_method,
                    blocked_at, blocked_source, blocked_category
                ) VALUES (
                    :id, :user_id, :retailer_id, :status, :version,
                    :now, :now, :connected_at, :reauth_required_at,
                    :disconnected_at, :external_authorization_reference,
                    :retailer_location_reference, :authentication_method,
                    :blocked_at, :blocked_source, :blocked_category
                )
                """
            ),
            {
                "id": uuid4(),
                "user_id": user_id,
                "retailer_id": retailer_id,
                "status": status,
                "version": version,
                "now": NOW,
                "connected_at": connected_at,
                "reauth_required_at": reauth_required_at,
                "disconnected_at": disconnected_at,
                "external_authorization_reference": external_authorization_reference,
                "retailer_location_reference": retailer_location_reference,
                "authentication_method": authentication_method,
                "blocked_at": blocked_at,
                "blocked_source": blocked_source,
                "blocked_category": blocked_category,
            },
        )


def test_status_check_rejects_unknown_status(pg_engine, make_user) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(pg_engine, user_id=user.id, status="BOGUS")


def test_retailer_check_rejects_unknown_retailer(pg_engine, make_user) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(pg_engine, user_id=user.id, retailer_id="UNKNOWN")


def test_version_must_be_positive(pg_engine, make_user) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(pg_engine, user_id=user.id, version=0)


def test_connected_requires_connected_at(pg_engine, make_user) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(pg_engine, user_id=user.id, status="CONNECTED", connected_at=None)


def test_reauth_required_requires_reauth_required_at(pg_engine, make_user) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(
            pg_engine,
            user_id=user.id,
            status="REAUTH_REQUIRED",
            reauth_required_at=None,
        )


def test_disconnected_requires_disconnected_at(pg_engine, make_user) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(
            pg_engine,
            user_id=user.id,
            status="DISCONNECTED",
            disconnected_at=None,
        )


@pytest.mark.parametrize(
    "reference",
    ["has space", "bad!reference", "trailing-space ", ""],
)
def test_external_reference_shape_is_enforced(
    pg_engine, make_user, reference: str
) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(
            pg_engine,
            user_id=user.id,
            external_authorization_reference=reference,
        )


def test_location_reference_shape_is_enforced(pg_engine, make_user) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(
            pg_engine,
            user_id=user.id,
            retailer_location_reference="has space",
        )


def test_authentication_method_shape_is_enforced(pg_engine, make_user) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(
            pg_engine,
            user_id=user.id,
            authentication_method="Bad-Method",
        )


def test_blocked_requires_restriction_metadata(pg_engine, make_user) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(pg_engine, user_id=user.id, status="BLOCKED")
    with pytest.raises(IntegrityError):
        _insert(
            pg_engine,
            user_id=user.id,
            status="BLOCKED",
            blocked_at=NOW,
            blocked_source="retailer",
        )


@pytest.mark.parametrize(
    ("source", "category"),
    [
        ("bogus", "account_suspended"),
        ("retailer", "bogus"),
    ],
)
def test_blocked_restriction_vocabulary_is_enforced(
    pg_engine, make_user, source: str, category: str
) -> None:
    user = make_user()
    with pytest.raises(IntegrityError):
        _insert(
            pg_engine,
            user_id=user.id,
            status="BLOCKED",
            blocked_at=NOW,
            blocked_source=source,
            blocked_category=category,
        )


def test_blocked_with_controlled_metadata_is_accepted(pg_engine, make_user) -> None:
    user = make_user()
    _insert(
        pg_engine,
        user_id=user.id,
        status="BLOCKED",
        blocked_at=NOW,
        blocked_source="legal",
        blocked_category="legal_hold",
    )
    with pg_engine.connect() as connection:
        values = connection.execute(
            text(
                "SELECT blocked_source, blocked_category FROM retailer_connections "
                "WHERE user_id = :user_id"
            ),
            {"user_id": user.id},
        ).one()
    assert values == ("legal", "legal_hold")


def test_owner_foreign_key_is_enforced(pg_engine) -> None:
    with pytest.raises(IntegrityError):
        _insert(pg_engine, user_id=uuid4())


def test_partial_unique_index_allows_one_non_terminal_connection(
    pg_engine, make_user
) -> None:
    user = make_user()
    _insert(pg_engine, user_id=user.id)
    with pytest.raises(IntegrityError):
        _insert(pg_engine, user_id=user.id)


def test_partial_unique_index_allows_new_records_after_terminal_states(
    pg_engine, make_user
) -> None:
    user = make_user()
    _insert(pg_engine, user_id=user.id)
    _insert(
        pg_engine,
        user_id=user.id,
        status="DISCONNECTED",
        disconnected_at=NOW,
    )
    _insert(pg_engine, user_id=user.id, status="REVOKED")
    _insert(
        pg_engine,
        user_id=user.id,
        status="DISCONNECTED",
        disconnected_at=NOW,
    )
    _insert(pg_engine, user_id=user.id, status="REVOKED")

    with pg_engine.connect() as connection:
        count = connection.execute(
            text(
                "SELECT count(*) FROM retailer_connections WHERE user_id = :user_id"
            ),
            {"user_id": user.id},
        ).scalar_one()
    assert count == 5


def test_indexes_and_check_constraints_exist(pg_engine) -> None:
    with pg_engine.connect() as connection:
        indexes = set(
            connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = current_schema() "
                    "AND tablename = 'retailer_connections'"
                )
            ).scalars()
        )
        assert {
            "ix_retailer_connections_user_created",
            "ix_retailer_connections_user_retailer_status",
            "uq_retailer_connections_active_user_retailer",
        } <= indexes

        partial = connection.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'uq_retailer_connections_active_user_retailer'"
            )
        ).scalar_one()
        assert "UNIQUE" in partial
        assert "WHERE" in partial
        assert "DISCONNECTED" in partial
        assert "REVOKED" in partial

        constraints = set(
            connection.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'retailer_connections'::regclass "
                    "AND contype = 'c'"
                )
            ).scalars()
        )
        assert {
            "ck_retailer_connections_status",
            "ck_retailer_connections_retailer_id",
            "ck_retailer_connections_version_positive",
            "ck_retailer_connections_connected_at",
            "ck_retailer_connections_reauth_required_at",
            "ck_retailer_connections_disconnected_at",
            "ck_retailer_connections_external_reference_shape",
            "ck_retailer_connections_location_reference_shape",
            "ck_retailer_connections_auth_method_shape",
            "ck_retailer_connections_blocked_metadata",
            "ck_retailer_connections_blocked_source",
            "ck_retailer_connections_blocked_category",
        } <= constraints

        unique_constraints = set(
            connection.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'retailer_connections'::regclass "
                    "AND contype = 'u'"
                )
            ).scalars()
        )
        assert {
            "uq_retailer_connections_id_user",
            "uq_retailer_connections_id_user_retailer",
        } <= unique_constraints


def test_audit_payload_column_is_jsonb(pg_engine) -> None:
    with pg_engine.connect() as connection:
        data_type = connection.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'audit_events' AND column_name = 'payload'"
            )
        ).scalar_one()
    assert data_type == "jsonb"


def test_deleting_owner_cascades_to_connections(pg_engine, make_user) -> None:
    user = make_user()
    _insert(pg_engine, user_id=user.id)
    with pg_engine.begin() as connection:
        connection.execute(
            text("DELETE FROM users WHERE id = :user_id"), {"user_id": user.id}
        )
        count = connection.execute(
            text(
                "SELECT count(*) FROM retailer_connections WHERE user_id = :user_id"
            ),
            {"user_id": user.id},
        ).scalar_one()
    assert count == 0
