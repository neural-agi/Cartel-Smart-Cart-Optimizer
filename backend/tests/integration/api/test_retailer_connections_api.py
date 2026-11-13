"""HTTP API integration tests for retailer connection lifecycle management.

These tests run against the project's real PostgreSQL schema and a real
credential-vault instance. They verify the HTTP contract, owner scoping,
lifecycle enforcement, credential revocation on disconnect, disclosure
boundaries, and fail-closed rate limiting.

They do not authenticate to any retailer. No test exercises OAuth, browser
automation, credential retrieval, or retailer operations.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.credential_vault.types import (
    AUDIT_REVOKED as VAULT_AUDIT_REVOKED,
)
from app.credential_vault.types import (
    SecretOwner,
    SecretStatus,
    SecretType,
)
from app.db.models import AuditEvent
from app.db.models.credential_secrets import CredentialSecret
from app.db.models.retailer_connections import RetailerConnection
from app.retailer_connections import lifecycle
from app.retailer_connections.service import AUDIT_PAYLOAD_FIELDS
from tests.integration.api.conftest import RecordingRateLimiter
from tests.integration.retailer_connections.conftest import audit_events_for

CONNECTIONS = "/api/v2/connections"
ORIGIN = "http://testserver"
ALLOWED_RESPONSE_FIELDS = {
    "id",
    "retailer_id",
    "status",
    "authentication_method",
    "connected_at",
    "last_validated_at",
    "reauthorization_required",
    "capabilities",
    "cartel_account_authenticated",
    "retailer_connection_exists",
    "retailer_authenticated",
    "retailer_operational",
    "created_at",
    "updated_at",
}
ALLOWED_CAPABILITY_FIELDS = {
    "cartel_data_access",
    "connection_metadata",
    "retailer_health_check",
    "product_discovery",
    "price_availability_acquisition",
    "cart_preparation",
    "checkout",
}
FORBIDDEN_RESPONSE_TERMS = (
    "ciphertext",
    "nonce",
    "key_version",
    "vault",
    "secret_reference",
    "external_authorization_reference",
    "password",
    "access_token",
    "refresh_token",
    "cookie",
    "otp",
)


def headers(raw_token: str, csrf_token: str, *, mutate: bool = False) -> dict[str, str]:
    result = {"Cookie": f"cartel_session={raw_token}"}
    if mutate:
        result["Origin"] = ORIGIN
        result["X-CSRF-Token"] = csrf_token
    return result


def create_payload(retailer_id: str = "BLINKIT") -> dict[str, str]:
    return {"retailer_id": retailer_id}


def test_create_requires_authentication(api_client) -> None:
    client, _ = api_client
    response = client.post(CONNECTIONS, json=create_payload(), headers={"Origin": ORIGIN})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_create_requires_csrf_and_same_origin(api_client, make_user, make_session) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)

    missing_origin = client.post(
        CONNECTIONS,
        json=create_payload(),
        headers={"Cookie": f"cartel_session={raw}", "X-CSRF-Token": csrf},
    )
    assert missing_origin.status_code == 403
    assert missing_origin.json()["detail"]["code"] == "origin_rejected"

    missing_csrf = client.post(
        CONNECTIONS,
        json=create_payload(),
        headers={"Cookie": f"cartel_session={raw}", "Origin": ORIGIN},
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["detail"]["code"] == "csrf_failed"

    wrong_origin = client.post(
        CONNECTIONS,
        json=create_payload(),
        headers={
            "Cookie": f"cartel_session={raw}",
            "Origin": "http://evil.example",
            "X-CSRF-Token": csrf,
        },
    )
    assert wrong_origin.status_code == 403
    assert wrong_origin.json()["detail"]["code"] == "origin_rejected"


def test_create_returns_pending_auth_metadata_only(
    api_client, make_user, make_session
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)

    response = client.post(
        CONNECTIONS,
        json=create_payload("blinkit"),
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert set(body) == ALLOWED_RESPONSE_FIELDS
    assert set(body["capabilities"]) == ALLOWED_CAPABILITY_FIELDS
    assert UUID(body["id"])
    assert body["retailer_id"] == "BLINKIT"
    assert body["status"] == "PENDING_AUTH"
    assert body["authentication_method"] is None
    assert body["connected_at"] is None
    assert body["last_validated_at"] is None
    assert body["reauthorization_required"] is False

    # Four distinct concepts must never collapse into "connected".
    assert body["cartel_account_authenticated"] is True
    assert body["retailer_connection_exists"] is True
    assert body["retailer_authenticated"] is False
    assert body["retailer_operational"] is False

    assert body["capabilities"]["retailer_health_check"] == "denied"
    assert body["capabilities"]["product_discovery"] == "denied"
    assert body["capabilities"]["checkout"] == "denied"

    serialized = response.text.lower()
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in serialized


def test_create_rejects_credential_material_and_owner_spoofing(
    api_client, make_user, make_session, db_session
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)

    secret = "correct-horse-battery-staple-1"
    response = client.post(
        CONNECTIONS,
        json={
            "retailer_id": "BLINKIT",
            "password": secret,
            "otp": "123456",
            "cookie": "session=abc",
            "access_token": "token-value",
            "user_id": str(uuid4()),
        },
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 422
    # The sanitized validation handler must never echo supplied values.
    assert secret not in response.text
    assert "123456" not in response.text
    assert "token-value" not in response.text

    rows = db_session.scalars(
        select(RetailerConnection).where(RetailerConnection.user_id == user.id)
    ).all()
    assert rows == []


def test_create_rejects_invalid_retailer_identifier(
    api_client, make_user, make_session
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)

    response = client.post(
        CONNECTIONS,
        json=create_payload("not-a-retailer"),
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 422
    assert "not-a-retailer" not in response.text


def test_duplicate_connection_returns_conflict_without_extra_audit(
    api_client, make_user, make_session, db_session
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)

    first = client.post(
        CONNECTIONS,
        json=create_payload(),
        headers=headers(raw, csrf, mutate=True),
    )
    assert first.status_code == 201

    second = client.post(
        CONNECTIONS,
        json=create_payload(),
        headers=headers(raw, csrf, mutate=True),
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "retailer_connection_exists"

    events = audit_events_for(db_session, UUID(first.json()["id"]))
    assert [event.event_type for event in events] == ["retailer_connection_created"]


def test_list_is_owner_scoped(
    api_client, make_user, make_session, make_connection
) -> None:
    client, _ = api_client
    owner = make_user()
    other = make_user()
    raw, csrf = make_session(owner)

    first = make_connection(user_id=owner.id, status=lifecycle.RetailerConnectionStatus.CONNECTED)
    second = make_connection(
        user_id=owner.id,
        status=lifecycle.RetailerConnectionStatus.PENDING_AUTH,
        retailer_id="ZEPTO",
    )
    foreign = make_connection(
        user_id=other.id,
        status=lifecycle.RetailerConnectionStatus.CONNECTED,
        retailer_id="BIGBASKET",
    )

    response = client.get(CONNECTIONS, headers=headers(raw, csrf))
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert ids == {str(first.id), str(second.id)}
    assert str(foreign.id) not in ids

    # A caller-supplied user_id query parameter is ignored, never trusted.
    spoofed = client.get(
        CONNECTIONS,
        params={"user_id": str(other.id)},
        headers=headers(raw, csrf),
    )
    assert spoofed.status_code == 200
    assert {item["id"] for item in spoofed.json()} == ids


def test_get_is_owner_scoped_and_idor_is_indistinguishable(
    api_client, make_user, make_session, make_connection
) -> None:
    client, _ = api_client
    owner = make_user()
    other = make_user()
    raw, csrf = make_session(owner)

    own = make_connection(
        user_id=owner.id, status=lifecycle.RetailerConnectionStatus.CONNECTED
    )
    foreign = make_connection(
        user_id=other.id,
        status=lifecycle.RetailerConnectionStatus.CONNECTED,
        retailer_id="ZEPTO",
    )

    found = client.get(f"{CONNECTIONS}/{own.id}", headers=headers(raw, csrf))
    assert found.status_code == 200
    assert found.json()["id"] == str(own.id)

    cross_user = client.get(f"{CONNECTIONS}/{foreign.id}", headers=headers(raw, csrf))
    nonexistent = client.get(f"{CONNECTIONS}/{uuid4()}", headers=headers(raw, csrf))
    assert cross_user.status_code == 404
    assert nonexistent.status_code == 404
    assert cross_user.json() == nonexistent.json()
    assert cross_user.json()["detail"]["code"] == "retailer_connection_not_found"


def test_get_requires_authentication(api_client) -> None:
    client, _ = api_client
    response = client.get(f"{CONNECTIONS}/{uuid4()}")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_reauthorize_pending_auth_and_repeat_is_idempotent(
    api_client, make_user, make_session, db_session
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)

    created = client.post(
        CONNECTIONS,
        json=create_payload(),
        headers=headers(raw, csrf, mutate=True),
    )
    connection_id = UUID(created.json()["id"])

    first = client.post(
        f"{CONNECTIONS}/{connection_id}/reauthorize",
        headers=headers(raw, csrf, mutate=True),
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "REAUTH_REQUIRED"
    assert first.json()["reauthorization_required"] is True
    assert first.json()["retailer_authenticated"] is False
    assert first.json()["retailer_operational"] is False

    repeated = client.post(
        f"{CONNECTIONS}/{connection_id}/reauthorize",
        headers=headers(raw, csrf, mutate=True),
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "REAUTH_REQUIRED"

    events = audit_events_for(db_session, connection_id)
    assert [event.event_type for event in events] == [
        "retailer_connection_created",
        "retailer_connection_reauth_required",
    ]


@pytest.mark.parametrize(
    "status",
    [
        lifecycle.RetailerConnectionStatus.CONNECTED,
        lifecycle.RetailerConnectionStatus.DEGRADED,
    ],
)
def test_reauthorize_connected_and_degraded(
    api_client, make_user, make_session, make_connection, status
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)
    connection = make_connection(user_id=user.id, status=status)

    response = client.post(
        f"{CONNECTIONS}/{connection.id}/reauthorize",
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "REAUTH_REQUIRED"
    assert response.json()["retailer_authenticated"] is False
    assert response.json()["retailer_operational"] is False


@pytest.mark.parametrize(
    "status",
    [
        lifecycle.RetailerConnectionStatus.BLOCKED,
        lifecycle.RetailerConnectionStatus.REVOKED,
        lifecycle.RetailerConnectionStatus.DISCONNECTED,
    ],
)
def test_reauthorize_is_unavailable_for_restricted_states(
    api_client, make_user, make_session, make_connection, status
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)
    connection = make_connection(user_id=user.id, status=status)

    response = client.post(
        f"{CONNECTIONS}/{connection.id}/reauthorize",
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "reauthorization_not_available"


def test_rejected_transition_leaves_state_and_audit_unchanged(
    api_client, make_user, make_session, make_connection, db_session
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)
    connection = make_connection(
        user_id=user.id,
        status=lifecycle.RetailerConnectionStatus.BLOCKED,
        version=3,
    )
    before = audit_events_for(db_session, connection.id)

    response = client.post(
        f"{CONNECTIONS}/{connection.id}/reauthorize",
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 409

    db_session.expire_all()
    persisted = db_session.get(RetailerConnection, connection.id)
    assert persisted is not None
    assert persisted.status == lifecycle.RetailerConnectionStatus.BLOCKED.value
    assert persisted.version == 3
    assert audit_events_for(db_session, connection.id) == before


def test_disconnect_pending_auth_and_repeat_is_predictable(
    api_client, make_user, make_session, db_session
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)

    created = client.post(
        CONNECTIONS,
        json=create_payload(),
        headers=headers(raw, csrf, mutate=True),
    )
    connection_id = UUID(created.json()["id"])

    first = client.post(
        f"{CONNECTIONS}/{connection_id}/disconnect",
        headers=headers(raw, csrf, mutate=True),
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "DISCONNECTED"
    assert first.json()["retailer_authenticated"] is False
    assert first.json()["retailer_operational"] is False

    repeated = client.post(
        f"{CONNECTIONS}/{connection_id}/disconnect",
        headers=headers(raw, csrf, mutate=True),
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "DISCONNECTED"

    events = audit_events_for(db_session, connection_id)
    assert [event.event_type for event in events] == [
        "retailer_connection_created",
        "retailer_connection_disconnected",
    ]


def test_disconnect_revoked_is_rejected(
    api_client, make_user, make_session, make_connection
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)
    connection = make_connection(
        user_id=user.id, status=lifecycle.RetailerConnectionStatus.REVOKED
    )

    response = client.post(
        f"{CONNECTIONS}/{connection.id}/disconnect",
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "connection_not_disconnectable"


def test_disconnect_blocked_is_allowed(
    api_client, make_user, make_session, make_connection
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)
    connection = make_connection(
        user_id=user.id, status=lifecycle.RetailerConnectionStatus.BLOCKED
    )

    response = client.post(
        f"{CONNECTIONS}/{connection.id}/disconnect",
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "DISCONNECTED"


def test_disconnect_revokes_active_secrets_and_preserves_audit(
    api_client, make_user, make_session, make_connection, vault, db_session, session_factory
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)
    connection = make_connection(
        user_id=user.id, status=lifecycle.RetailerConnectionStatus.CONNECTED
    )
    owner = SecretOwner(
        user_id=connection.user_id,
        connection_id=connection.id,
        retailer_id=connection.retailer_id,
    )
    first = vault.store(
        db_session,
        owner=owner,
        secret_type=SecretType.OAUTH_ACCESS_TOKEN,
        plaintext=b"first-opaque-token",
        request_id="test",
    )
    second = vault.store(
        db_session,
        owner=owner,
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=b"second-opaque-token",
        request_id="test",
    )

    response = client.post(
        f"{CONNECTIONS}/{connection.id}/disconnect",
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "DISCONNECTED"

    with session_factory() as db:
        rows = db.scalars(
            select(CredentialSecret).where(
                CredentialSecret.connection_id == connection.id
            )
        ).all()
        assert {row.status for row in rows} == {SecretStatus.REVOKED.value}
        assert {row.reference for row in rows} == {first.reference, second.reference}

        vault_events = db.scalars(
            select(AuditEvent).where(
                AuditEvent.object_type == "credential_secret",
                AuditEvent.event_type == VAULT_AUDIT_REVOKED,
            )
        ).all()
        assert len(vault_events) == 2

    # No ciphertext, nonce, key version, or reference appears in the response.
    serialized = response.text.lower()
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in serialized
    assert str(first.reference).lower() not in serialized


def test_disconnect_revokes_even_with_fail_closed_key_provider(
    build_client, make_user, make_session, make_connection, vault, db_session, session_factory
) -> None:
    """Revocation must not depend on encryption keys.

    The production default provider is ``unavailable`` and fails closed for key
    operations. Disconnect only needs to mark secrets REVOKED, so it must still
    work when no key material is available.
    """

    owner_user = make_user()
    raw, csrf = make_session(owner_user)
    connection = make_connection(
        user_id=owner_user.id, status=lifecycle.RetailerConnectionStatus.CONNECTED
    )
    owner = SecretOwner(
        user_id=connection.user_id,
        connection_id=connection.id,
        retailer_id=connection.retailer_id,
    )
    stored = vault.store(
        db_session,
        owner=owner,
        secret_type=SecretType.OAUTH_ACCESS_TOKEN,
        plaintext=b"fail-closed-revocation",
        request_id="test",
    )

    client, _ = build_client(credential_vault=None)
    response = client.post(
        f"{CONNECTIONS}/{connection.id}/disconnect",
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "DISCONNECTED"

    with session_factory() as db:
        row = db.scalar(
            select(CredentialSecret).where(CredentialSecret.reference == stored.reference)
        )
        assert row is not None
        assert row.status == SecretStatus.REVOKED.value
        assert row.revoked_at is not None


def test_disconnect_does_not_affect_another_users_secrets(
    api_client, make_user, make_session, make_connection, vault, db_session, session_factory
) -> None:
    client, _ = api_client
    owner = make_user()
    other = make_user()
    raw, csrf = make_session(owner)
    owned = make_connection(
        user_id=owner.id, status=lifecycle.RetailerConnectionStatus.CONNECTED
    )
    foreign = make_connection(
        user_id=other.id,
        status=lifecycle.RetailerConnectionStatus.CONNECTED,
        retailer_id="ZEPTO",
    )
    foreign_owner = SecretOwner(
        user_id=foreign.user_id,
        connection_id=foreign.id,
        retailer_id=foreign.retailer_id,
    )
    foreign_secret = vault.store(
        db_session,
        owner=foreign_owner,
        secret_type=SecretType.OAUTH_ACCESS_TOKEN,
        plaintext=b"other-users-token",
        request_id="test",
    )

    response = client.post(
        f"{CONNECTIONS}/{owned.id}/disconnect",
        headers=headers(raw, csrf, mutate=True),
    )
    assert response.status_code == 200

    with session_factory() as db:
        row = db.scalar(
            select(CredentialSecret).where(
                CredentialSecret.reference == foreign_secret.reference
            )
        )
        assert row is not None
        assert row.status == SecretStatus.ACTIVE.value
        persisted = db.get(RetailerConnection, foreign.id)
        assert persisted is not None
        assert persisted.status == lifecycle.RetailerConnectionStatus.CONNECTED.value


@pytest.mark.parametrize(
    ("status", "authenticated", "operational", "health", "discovery"),
    [
        (lifecycle.RetailerConnectionStatus.PENDING_AUTH, False, False, "denied", "denied"),
        (lifecycle.RetailerConnectionStatus.CONNECTED, True, True, "permitted", "permitted"),
        (lifecycle.RetailerConnectionStatus.DEGRADED, True, False, "permitted", "denied"),
        (lifecycle.RetailerConnectionStatus.REAUTH_REQUIRED, False, False, "denied", "denied"),
        (lifecycle.RetailerConnectionStatus.BLOCKED, False, False, "denied", "denied"),
        (lifecycle.RetailerConnectionStatus.REVOKED, False, False, "denied", "denied"),
        (lifecycle.RetailerConnectionStatus.DISCONNECTED, False, False, "denied", "denied"),
    ],
)
def test_state_semantics_and_operation_matrix_are_exposed(
    api_client,
    make_user,
    make_session,
    make_connection,
    status,
    authenticated,
    operational,
    health,
    discovery,
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)
    connection = make_connection(user_id=user.id, status=status)

    response = client.get(f"{CONNECTIONS}/{connection.id}", headers=headers(raw, csrf))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == status.value
    assert body["cartel_account_authenticated"] is True
    assert body["retailer_connection_exists"] is True
    assert body["retailer_authenticated"] is authenticated
    assert body["retailer_operational"] is operational
    assert body["capabilities"]["product_discovery"] == discovery
    assert body["capabilities"]["retailer_health_check"] == health
    assert body["capabilities"]["checkout"] == discovery
    assert body["reauthorization_required"] == (
        status is lifecycle.RetailerConnectionStatus.REAUTH_REQUIRED
    )
    assert set(body["capabilities"]) == ALLOWED_CAPABILITY_FIELDS


@pytest.mark.parametrize(
    ("status", "cartel", "metadata"),
    [
        (lifecycle.RetailerConnectionStatus.PENDING_AUTH, "deferred", "deferred"),
        (lifecycle.RetailerConnectionStatus.CONNECTED, "permitted", "permitted"),
        (lifecycle.RetailerConnectionStatus.DEGRADED, "permitted", "permitted"),
        (lifecycle.RetailerConnectionStatus.REAUTH_REQUIRED, "permitted", "permitted"),
        (lifecycle.RetailerConnectionStatus.BLOCKED, "deferred", "permitted"),
        (lifecycle.RetailerConnectionStatus.REVOKED, "deferred", "deferred"),
        (lifecycle.RetailerConnectionStatus.DISCONNECTED, "deferred", "deferred"),
    ],
)
def test_deferred_cells_require_existing_authorization_not_default_permission(
    api_client, make_user, make_session, make_connection, status, cartel, metadata
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)
    connection = make_connection(user_id=user.id, status=status)

    # The owner-scoped session is the explicit existing authorization that lets
    # connection metadata be read. DEFERRED is reported as such, never as
    # permitted.
    response = client.get(f"{CONNECTIONS}/{connection.id}", headers=headers(raw, csrf))
    assert response.status_code == 200, response.text
    capabilities = response.json()["capabilities"]
    assert capabilities["cartel_data_access"] == cartel
    assert capabilities["connection_metadata"] == metadata


def test_rate_limit_returns_429(build_client, make_user, make_session) -> None:
    client, limiter = build_client(rate_limit_requests=2)
    user = make_user()
    raw, csrf = make_session(user)

    first = client.get(CONNECTIONS, headers=headers(raw, csrf))
    second = client.get(CONNECTIONS, headers=headers(raw, csrf))
    third = client.get(CONNECTIONS, headers=headers(raw, csrf))

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "rate_limited"
    assert third.headers["Retry-After"]
    assert limiter.calls >= 3


def test_rate_limit_backend_failure_is_fail_closed(
    build_client, make_user, make_session
) -> None:
    client, _ = build_client(limiter=RecordingRateLimiter(fail=True))
    user = make_user()
    raw, csrf = make_session(user)

    response = client.get(CONNECTIONS, headers=headers(raw, csrf))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "rate_limit_unavailable"


def test_audit_payloads_are_allowlisted_and_contain_no_credentials(
    api_client, make_user, make_session, db_session
) -> None:
    client, _ = api_client
    user = make_user()
    raw, csrf = make_session(user)

    created = client.post(
        CONNECTIONS,
        json=create_payload(),
        headers=headers(raw, csrf, mutate=True),
    )
    connection_id = UUID(created.json()["id"])
    client.post(
        f"{CONNECTIONS}/{connection_id}/reauthorize",
        headers=headers(raw, csrf, mutate=True),
    )
    client.post(
        f"{CONNECTIONS}/{connection_id}/disconnect",
        headers=headers(raw, csrf, mutate=True),
    )

    events = audit_events_for(db_session, connection_id)
    assert {event.event_type for event in events} == {
        "retailer_connection_created",
        "retailer_connection_reauth_required",
        "retailer_connection_disconnected",
    }
    for event in events:
        assert set(event.payload) == AUDIT_PAYLOAD_FIELDS
        serialized = str(event.payload).lower()
        for term in FORBIDDEN_RESPONSE_TERMS:
            assert term not in serialized
