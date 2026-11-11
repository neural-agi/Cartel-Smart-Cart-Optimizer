from __future__ import annotations

import os
import re
import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import Settings, get_settings
from app.main import create_application


class RecordingEmailDelivery:
    def __init__(self, engine=None) -> None:
        self.messages: list[tuple[str, str, str]] = []
        self.engine = engine

    def send(self, recipient: str, subject: str, body: str) -> None:
        self.messages.append((recipient, subject, body))

    def refresh(self, recipient: str) -> None:
        """Read queued outbox messages, since the API does not deliver synchronously."""
        if self.engine is None:
            return
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT recipient, subject, body FROM email_outbox_events "
                    "WHERE recipient = :recipient ORDER BY created_at, id"
                ),
                {"recipient": recipient.strip().casefold()},
            ).all()
        self.messages = [(row.recipient, row.subject, row.body) for row in rows]


def _database_url() -> str:
    value = os.environ.get("CARTEL_TEST_DATABASE_URL", "")
    if not value:
        pytest.skip("set CARTEL_TEST_DATABASE_URL to a disposable PostgreSQL database; SQLite is not supported")
    if value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
        os.environ["CARTEL_TEST_DATABASE_URL"] = value
    if not value.startswith("postgresql+psycopg://"):
        pytest.fail("CARTEL_TEST_DATABASE_URL must be PostgreSQL")
    return value


@pytest.fixture(scope="module")
def pg_database():
    url = _database_url()
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        engine.dispose()
        pytest.skip(f"disposable PostgreSQL is not reachable: {type(exc).__name__}")

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[3] / "alembic.ini"))
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
            for table in ("optimization_allocations", "optimization_plans", "optimization_requests", "audit_events", "verification_challenges", "sessions", "password_credentials", "identities", "users"):
                connection.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
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
def auth_client(pg_database, tmp_path):
    url = os.environ["CARTEL_TEST_DATABASE_URL"]
    mail = RecordingEmailDelivery(pg_database)
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        database_url_override=url,
        public_origin="http://testserver",
        auth_cookie_secure=False,
        smtp_host="mail.invalid",
        smtp_from="no-reply@example.com",
        auth_required=True,
        auth_tokens="operator=operator-secret",
    )
    with TestClient(create_application(settings, email_delivery=mail), base_url="http://testserver") as client:
        yield client, mail, pg_database


@pytest.fixture
def demo_auth_client(pg_database, tmp_path):
    url = os.environ["CARTEL_TEST_DATABASE_URL"]
    mail = RecordingEmailDelivery(pg_database)
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        database_url_override=url,
        public_origin="http://testserver",
        auth_cookie_secure=False,
        smtp_host="mail.invalid",
        smtp_from="no-reply@example.com",
        auth_required=True,
        auth_tokens="operator=operator-secret",
        demo_fixtures_enabled=True,
    )
    with TestClient(create_application(settings, email_delivery=mail), base_url="http://testserver") as client:
        yield client, mail, pg_database


@pytest.fixture
def synthetic_demo_auth_client(pg_database, tmp_path):
    from app.dev.seed_synthetic_demo_cart import seed_synthetic_demo_catalog

    seed_synthetic_demo_catalog(tmp_path)
    url = os.environ["CARTEL_TEST_DATABASE_URL"]
    mail = RecordingEmailDelivery(pg_database)
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        database_url_override=url,
        public_origin="http://testserver",
        auth_cookie_secure=False,
        smtp_host="mail.invalid",
        smtp_from="no-reply@example.com",
        auth_required=True,
        auth_tokens="operator=operator-secret",
        demo_fixtures_enabled=True,
    )
    with TestClient(create_application(settings, email_delivery=mail), base_url="http://testserver") as client:
        yield client, mail, pg_database


def _origin() -> dict[str, str]:
    return {"Origin": "http://testserver"}


def _verification_token(mail: RecordingEmailDelivery, recipient: str) -> str:
    mail.refresh(recipient)
    match = re.search(r"#token=([A-Za-z0-9_-]+)", mail.messages[-1][2])
    assert match
    return match.group(1)


def test_00_migration_can_downgrade_and_upgrade(pg_database):
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = os.environ["CARTEL_TEST_DATABASE_URL"]
    get_settings.cache_clear()
    try:
        config = Config(str(Path(__file__).parents[3] / "alembic.ini"))
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        with pg_database.connect() as connection:
            # The test must run against the disposable PostgreSQL database named
            # in CARTEL_TEST_DATABASE_URL, on a real PostgreSQL server (never
            # SQLite), with exactly one Alembic head applied.
            expected_database = os.environ["CARTEL_TEST_DATABASE_URL"].rsplit("/", 1)[-1]
            current_database = connection.execute(text("SELECT current_database()")).scalar_one()
            server_version = connection.execute(
                text("SELECT current_setting('server_version')")
            ).scalar_one()
            dialect = connection.execute(text("SELECT version()")).scalar_one()
            heads = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
            assert current_database == expected_database
            assert re.fullmatch(r"\d+\.\d+(?:\.\d+)?", server_version), server_version
            assert "PostgreSQL" in dialect
            assert heads == ["0009_credential_vault"]
            tables = set(connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")).scalars())
        assert {
            "users",
            "identities",
            "password_credentials",
            "sessions",
            "verification_challenges",
            "audit_events",
            "shopping_lists",
            "shopping_list_items",
            "optimization_requests",
            "optimization_plans",
            "optimization_allocations",
        } <= tables
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def _signup(client: TestClient, mail: RecordingEmailDelivery, email: str) -> dict:
    response = client.post(
        "/api/v2/auth/signup",
        json={"email": email, "password": "correct-horse-battery-staple-1"},
        headers=_origin(),
    )
    assert response.status_code == 202, response.text
    mail.refresh(email)
    assert mail.messages, response.text
    verified = client.post(
        "/api/v2/auth/email/verify",
        json={"token": _verification_token(mail, email)},
        headers=_origin(),
    )
    assert verified.status_code == 200
    assert verified.cookies.get("cartel_session")
    assert "httponly" in verified.headers["set-cookie"].lower()
    return verified.json()


def test_auth_migration_upgrade_downgrade_upgrade_and_lifecycle(auth_client):
    client, mail, engine = auth_client
    # The module fixture ran a clean upgrade; this also checks every required table exists.
    with engine.connect() as connection:
        tables = set(connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")).scalars())
    assert {"users", "identities", "password_credentials", "sessions", "verification_challenges", "audit_events"} <= tables
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT 1 FROM identities WHERE provider = 'email_password' AND subject = 'first@example.com'")
        ).first() is None

    first = _signup(client, mail, "first@example.com")
    user_id = first["user_id"]
    csrf = first["csrf_token"]
    assert client.get("/api/v2/me").json()["user_id"] == user_id

    old_cookie = client.cookies.get("cartel_session")
    rotated = client.post("/api/v2/auth/rotate", headers={**_origin(), "X-CSRF-Token": csrf})
    assert rotated.status_code == 200
    assert rotated.cookies.get("cartel_session") != old_cookie
    assert client.get("/api/v2/me").status_code == 200
    assert client.get("/api/v2/me", headers={"Cookie": f"cartel_session={old_cookie}"}).status_code == 401

    missing_csrf = client.post("/api/v2/auth/logout")
    assert missing_csrf.status_code == 403
    logout = client.post("/api/v2/auth/logout", headers={**_origin(), "X-CSRF-Token": rotated.json()["csrf_token"]})
    assert logout.status_code == 204
    assert client.get("/api/v2/me").status_code == 401

    login = client.post(
        "/api/v2/auth/login",
        json={"email": "first@example.com", "password": "correct-horse-battery-staple-1"},
        headers=_origin(),
    )
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]
    assert client.post("/api/v2/auth/logout-all", headers={**_origin(), "X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/api/v2/me").status_code == 401


def test_password_recovery_revokes_sessions_and_authentication_is_user_scoped(auth_client):
    client, mail, engine = auth_client
    user_a = _signup(client, mail, "alpha@example.com")
    user_a_id = user_a["user_id"]
    user_b = _signup(client, mail, "beta@example.com")
    user_b_id = user_b["user_id"]
    assert user_a_id != user_b_id
    assert client.get("/api/v2/me?user_id=" + user_a_id).json()["user_id"] == user_b_id

    recovery = client.post("/api/v2/auth/password/recovery", json={"email": "alpha@example.com"}, headers=_origin())
    assert recovery.status_code == 202
    reset_token = _verification_token(mail, "alpha@example.com")
    reset = client.post(
        "/api/v2/auth/password/reset",
        json={"token": reset_token, "new_password": "new-password-with-enough-length-2"},
        headers=_origin(),
    )
    assert reset.status_code == 200
    assert client.post("/api/v2/auth/login", json={"email": "alpha@example.com", "password": "correct-horse-battery-staple-1"}, headers=_origin()).status_code == 401
    assert client.post("/api/v2/auth/login", json={"email": "alpha@example.com", "password": "new-password-with-enough-length-2"}, headers=_origin()).status_code == 200

    with engine.connect() as connection:
        raw_password = connection.execute(text("SELECT password_hash FROM password_credentials WHERE user_id = :id"), {"id": user_a_id}).scalar_one()
        assert "new-password-with-enough-length-2" not in raw_password
        hashes = connection.execute(text("SELECT token_hash, csrf_hash FROM sessions")).all()
        assert all(len(row.token_hash) == 64 and len(row.csrf_hash) == 64 for row in hashes)
        challenge_hashes = connection.execute(text("SELECT token_hash FROM verification_challenges")).scalars().all()
        assert all(reset_token not in value for value in challenge_hashes)


def test_login_requires_verified_email_and_origin_is_checked(auth_client):
    client, mail, _ = auth_client
    response = client.post("/api/v2/auth/signup", json={"email": "unverified@example.com", "password": "correct-horse-battery-staple-1"}, headers=_origin())
    assert response.status_code == 202
    login = client.post("/api/v2/auth/login", json={"email": "unverified@example.com", "password": "correct-horse-battery-staple-1"}, headers=_origin())
    assert login.status_code == 401
    rejected = client.post("/api/v2/auth/login", json={"email": "x@example.com", "password": "long-password-123"}, headers={"Origin": "https://attacker.invalid"})
    assert rejected.status_code == 403


def test_consumer_session_is_limited_to_consumer_api_and_v1_mutations_require_csrf(auth_client):
    client, mail, _ = auth_client
    assert client.get("/api/v2/products/search", params={"query": "milk"}).status_code == 401
    _signup(client, mail, "consumer@example.com")
    search = client.get("/api/v2/products/search", params={"query": "milk"})
    assert search.status_code == 200
    assert search.json() == {"query": "milk", "items": []}
    assert client.get("/api/v2/products/search", params={"query": " "}).status_code == 422
    csrf = client.get("/api/v2/auth/csrf").json()["csrf_token"]
    assert client.get("/api/v1/products/search", params={"query": "milk"}).status_code == 200
    assert client.post("/api/v1/scrape", json={}).status_code == 403
    assert client.post("/api/v1/cart/optimize", json={}).status_code == 403
    denied = client.post("/api/v1/cart/resolve", json={}, headers=_origin())
    assert denied.status_code == 403
    invalid_payload = client.post(
        "/api/v1/cart/resolve",
        json={"items": [{"item_id": "item-1", "quantity": 1}]},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert invalid_payload.status_code == 422


def test_idle_expiry_revokes_consumer_session(auth_client):
    import hashlib
    from datetime import datetime, timedelta, timezone

    client, mail, engine = auth_client
    _signup(client, mail, "idle@example.com")
    raw_cookie = client.cookies.get("cartel_session")
    digest = hashlib.sha256(raw_cookie.encode()).hexdigest()
    with engine.begin() as connection:
        connection.execute(text("UPDATE sessions SET last_seen_at = :expired WHERE token_hash = :token"), {"expired": datetime.now(timezone.utc) - timedelta(days=8), "token": digest})
    assert client.get("/api/v2/me").status_code == 401


def test_absolute_expiry_revokes_consumer_session(auth_client):
    import hashlib
    from datetime import datetime, timedelta, timezone

    client, mail, engine = auth_client
    _signup(client, mail, "absolute-expiry@example.com")
    raw_cookie = client.cookies.get("cartel_session")
    digest = hashlib.sha256(raw_cookie.encode()).hexdigest()
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE sessions SET expires_at = :expired WHERE token_hash = :token"),
            {"expired": datetime.now(timezone.utc) - timedelta(seconds=1), "token": digest},
        )
    assert client.get("/api/v2/me").status_code == 401


def test_password_reset_revokes_previously_issued_cookie(auth_client):
    client, mail, _ = auth_client
    _signup(client, mail, "reset-revokes-session@example.com")
    old_cookie = client.cookies.get("cartel_session")
    recovery = client.post(
        "/api/v2/auth/password/recovery",
        json={"email": "reset-revokes-session@example.com"},
        headers=_origin(),
    )
    assert recovery.status_code == 202
    reset = client.post(
        "/api/v2/auth/password/reset",
        json={"token": _verification_token(mail, "reset-revokes-session@example.com"), "new_password": "reset-password-with-enough-length-3"},
        headers=_origin(),
    )
    assert reset.status_code == 200
    assert client.get("/api/v2/me").status_code == 401
    assert client.get("/api/v2/me", headers={"Cookie": f"cartel_session={old_cookie}"}).status_code == 401


def test_user_owned_shopping_list_create_manage_and_cross_user_isolation(auth_client):
    client, mail, _ = auth_client
    _signup(client, mail, "list-owner@example.com")
    csrf_a = client.get("/api/v2/auth/csrf").json()["csrf_token"]

    no_csrf = client.post("/api/v2/lists", json={"name": "Weekly"})
    assert no_csrf.status_code == 403
    cross_origin = client.post(
        "/api/v2/lists",
        json={"name": "Weekly"},
        headers={"Origin": "https://attacker.invalid", "X-CSRF-Token": csrf_a},
    )
    assert cross_origin.status_code == 403
    forged_owner = client.post(
        "/api/v2/lists",
        json={"name": "Weekly", "user_id": "some-other-user"},
        headers={**_origin(), "X-CSRF-Token": csrf_a},
    )
    assert forged_owner.status_code == 422

    created = client.post(
        "/api/v2/lists",
        json={"name": "  Weekly shop  "},
        headers={**_origin(), "X-CSRF-Token": csrf_a},
    )
    assert created.status_code == 201
    shopping_list = created.json()
    assert shopping_list["name"] == "Weekly shop"
    assert shopping_list["revision"] == 1

    added = client.post(
        f"/api/v2/lists/{shopping_list['id']}/items",
        json={"query": "  oat milk ", "quantity": 2, "unit": "cartons"},
        headers={**_origin(), "X-CSRF-Token": csrf_a},
    )
    assert added.status_code == 201
    item = added.json()["items"][0]
    assert (item["query"], item["quantity"], item["unit"]) == ("oat milk", 2, "cartons")
    assert item["resolution_status"] == "unresolved"
    assert item["canonical_variant_id"] is None
    assert added.json()["revision"] == 2

    invalid_quantity = client.post(
        f"/api/v2/lists/{shopping_list['id']}/items",
        json={"query": "eggs", "quantity": 0},
        headers={**_origin(), "X-CSRF-Token": csrf_a},
    )
    assert invalid_quantity.status_code == 422
    invalid_identity = client.post(
        f"/api/v2/lists/{shopping_list['id']}/items",
        json={"query": "milk", "canonical_variant_id": "variant-only"},
        headers={**_origin(), "X-CSRF-Token": csrf_a},
    )
    assert invalid_identity.status_code == 422

    updated = client.patch(
        f"/api/v2/lists/{shopping_list['id']}/items/{item['id']}",
        json={"quantity": 3},
        headers={**_origin(), "X-CSRF-Token": csrf_a},
    )
    assert updated.status_code == 200
    assert updated.json()["items"][0]["quantity"] == 3
    assert updated.json()["revision"] == 3

    renamed = client.patch(
        f"/api/v2/lists/{shopping_list['id']}",
        json={"name": "Weekly groceries"},
        headers={**_origin(), "X-CSRF-Token": csrf_a},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Weekly groceries"
    assert renamed.json()["revision"] == 4

    _signup(client, mail, "other-list-user@example.com")
    assert client.get("/api/v2/lists").json() == []
    assert client.get(f"/api/v2/lists/{shopping_list['id']}").status_code == 404
    assert client.patch(
        f"/api/v2/lists/{shopping_list['id']}/items/{item['id']}",
        json={"quantity": 8},
        headers={**_origin(), "X-CSRF-Token": client.get("/api/v2/auth/csrf").json()["csrf_token"]},
    ).status_code == 404


def test_shopping_list_item_add_persists_and_idempotent_replay_is_stable(auth_client):
    client, mail, engine = auth_client
    _signup(client, mail, "list-idempotency@example.com")
    csrf = client.get("/api/v2/auth/csrf").json()["csrf_token"]
    created = client.post(
        "/api/v2/lists",
        json={"name": "Replay"},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    list_id = created.json()["id"]

    headers = {
        **_origin(),
        "X-CSRF-Token": csrf,
        "Idempotency-Key": "shopping-list-add-item-replay-1",
    }
    payload = {"query": "oat milk", "quantity": 2, "unit": "cartons"}
    first = client.post(f"/api/v2/lists/{list_id}/items", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["revision"] == 2
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert (item["query"], item["quantity"], item["unit"]) == ("oat milk", 2, "cartons")

    with engine.connect() as connection:
        persisted = connection.execute(
            text("SELECT id, query, quantity, unit FROM shopping_list_items WHERE list_id = :list_id"),
            {"list_id": list_id},
        ).all()
        revision = connection.execute(
            text("SELECT revision FROM shopping_lists WHERE id = :list_id"),
            {"list_id": list_id},
        ).scalar_one()
    assert len(persisted) == 1
    assert (persisted[0].query, persisted[0].quantity, persisted[0].unit) == ("oat milk", 2, "cartons")
    assert str(persisted[0].id) == item["id"]
    assert revision == 2

    replay = client.post(f"/api/v2/lists/{list_id}/items", json=payload, headers=headers)
    assert replay.status_code == 201, replay.text
    assert replay.json() == body

    with engine.connect() as connection:
        persisted = connection.execute(
            text("SELECT count(*) FROM shopping_list_items WHERE list_id = :list_id"),
            {"list_id": list_id},
        ).scalar_one()
        revision = connection.execute(
            text("SELECT revision FROM shopping_lists WHERE id = :list_id"),
            {"list_id": list_id},
        ).scalar_one()
    assert persisted == 1
    assert revision == 2

    fetched = client.get(f"/api/v2/lists/{list_id}")
    assert fetched.status_code == 200
    assert fetched.json()["revision"] == 2
    assert [entry["id"] for entry in fetched.json()["items"]] == [item["id"]]


def test_shopping_list_create_idempotency_replay_and_conflict(auth_client):
    client, mail, engine = auth_client
    account = _signup(client, mail, "list-create-idempotency@example.com")
    user_id = account["user_id"]
    csrf = client.get("/api/v2/auth/csrf").json()["csrf_token"]
    headers = {
        **_origin(),
        "X-CSRF-Token": csrf,
        "Idempotency-Key": "shopping-list-create-replay-1",
    }

    first = client.post("/api/v2/lists", json={"name": "Replay list"}, headers=headers)
    assert first.status_code == 201, first.text
    body = first.json()

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM shopping_lists WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar_one()
    assert count == 1

    replay = client.post("/api/v2/lists", json={"name": "Replay list"}, headers=headers)
    assert replay.status_code == 201, replay.text
    assert replay.json() == body

    conflict = client.post("/api/v2/lists", json={"name": "Different list"}, headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "idempotency_key_conflict"

    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id, name FROM shopping_lists WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).all()
    assert [(str(row.id), row.name) for row in rows] == [(body["id"], "Replay list")]


def test_optimization_create_idempotency_replay_and_conflict(auth_client):
    client, mail, engine = auth_client
    account = _signup(client, mail, "optimization-idempotency@example.com")
    user_id = account["user_id"]
    csrf = client.get("/api/v2/auth/csrf").json()["csrf_token"]
    created = client.post(
        "/api/v2/lists",
        json={"name": "Optimization replay"},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    list_id = created.json()["id"]
    added = client.post(
        f"/api/v2/lists/{list_id}/items",
        json={"query": "milk", "quantity": 2},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert added.status_code == 201, added.text
    revision = added.json()["revision"]

    headers = {
        **_origin(),
        "X-CSRF-Token": csrf,
        "Idempotency-Key": "optimization-create-replay-1",
    }
    payload = {"list_id": list_id, "expected_revision": revision}
    first = client.post("/api/v2/optimizations", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["status"] == "unresolved"

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM optimization_requests WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar_one()
    assert count == 1

    replay = client.post("/api/v2/optimizations", json=payload, headers=headers)
    assert replay.status_code == 201, replay.text
    assert replay.json() == body

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM optimization_requests WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar_one()
    assert count == 1

    changed = client.post(
        f"/api/v2/lists/{list_id}/items",
        json={"query": "bread", "quantity": 1},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert changed.status_code == 201, changed.text
    changed_revision = changed.json()["revision"]
    assert changed_revision != revision

    conflict = client.post(
        "/api/v2/optimizations",
        json={"list_id": list_id, "expected_revision": changed_revision},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "idempotency_key_conflict"

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM optimization_requests WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar_one()
    assert count == 1

    stored = client.get(f"/api/v2/optimizations/{body['request_id']}")
    assert stored.status_code == 200
    assert stored.json() == body


def test_shopping_list_archival_and_selected_product_require_current_governed_evidence(auth_client):
    client, mail, _ = auth_client
    _signup(client, mail, "list-evidence@example.com")
    csrf = client.get("/api/v2/auth/csrf").json()["csrf_token"]
    created = client.post("/api/v2/lists", json={"name": "Pantry"}, headers={**_origin(), "X-CSRF-Token": csrf})
    list_id = created.json()["id"]

    stale_selection = client.post(
        f"/api/v2/lists/{list_id}/items",
        json={
            "query": "milk",
            "canonical_product_id": "unknown-product",
            "canonical_variant_id": "unknown-variant",
            "source_platform": "blinkit",
            "source_listing_id": "unverified-listing",
            "source_observation_id": "unverified-observation",
        },
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert stale_selection.status_code == 409
    assert stale_selection.json()["detail"]["code"] == "selected_product_evidence_stale"

    added = client.post(
        f"/api/v2/lists/{list_id}/items",
        json={"query": "bread", "quantity": 1},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    item_id = added.json()["items"][0]["id"]
    removed = client.delete(
        f"/api/v2/lists/{list_id}/items/{item_id}",
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert removed.status_code == 204
    assert client.get(f"/api/v2/lists/{list_id}").json()["items"] == []

    archived = client.patch(
        f"/api/v2/lists/{list_id}",
        json={"archived": True},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    cannot_add = client.post(
        f"/api/v2/lists/{list_id}/items",
        json={"query": "bread"},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert cannot_add.status_code == 409


def test_consumer_search_excludes_non_live_fixture_evidence(auth_client, tmp_path):
    from tests.integration.product_intelligence.test_vertical_pipeline import _job, _resolver, _runtime

    client, mail, _ = auth_client
    _signup(client, mail, "exact-selection@example.com")
    runtime, _catalog, _associations = _runtime(tmp_path / "governed-catalog", resolver=_resolver())
    client.app.state.product_intelligence_runtime = runtime
    from app.services.product_search import ProductSearchService
    client.app.state.product_search = ProductSearchService(
        catalog=runtime.catalog,
        association_registry=runtime.association_registry,
        observation_registry=runtime.observation_registry,
    )
    asyncio.run(runtime.execute(_job()))

    search = client.get("/api/v2/products/search", params={"query": "amul"})
    assert search.status_code == 200
    assert search.json()["items"] == []

    csrf = client.get("/api/v2/auth/csrf").json()["csrf_token"]
    created = client.post("/api/v2/lists", json={"name": "Weekly"}, headers={**_origin(), "X-CSRF-Token": csrf})
    list_id = created.json()["id"]
    invalid_source = client.post(
        f"/api/v2/lists/{list_id}/items",
        json={
            "query": "Amul milk",
            "canonical_product_id": "product-amul-taaza",
            "canonical_variant_id": "variant-amul-taaza-500ml",
            "source_platform": "ZEPTO",
            "source_listing_id": "1",
            "source_observation_id": "fixture-observation",
        },
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert invalid_source.status_code == 409
    assert invalid_source.json()["detail"]["code"] == "selected_product_evidence_stale"
    selected = client.post(
        f"/api/v2/lists/{list_id}/items",
        json={
            "query": "Amul milk",
            "quantity": 2,
            "canonical_product_id": "product-amul-taaza",
            "canonical_variant_id": "variant-amul-taaza-500ml",
            "source_platform": "BLINKIT",
            "source_listing_id": "1",
            "source_observation_id": "fixture-observation",
        },
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert selected.status_code == 409
    assert selected.json()["detail"]["code"] == "selected_product_evidence_stale"
    assert client.get(f"/api/v2/lists/{list_id}").json()["items"] == []


def test_demo_fixture_selection_is_labelled_and_never_used_for_a_payable_plan(demo_auth_client, tmp_path):
    from tests.integration.product_intelligence.test_vertical_pipeline import _job, _resolver, _runtime

    client, mail, _ = demo_auth_client
    _signup(client, mail, "demo-journey@example.com")
    runtime, _catalog, _associations = _runtime(tmp_path / "demo-governed-catalog", resolver=_resolver())
    client.app.state.product_intelligence_runtime = runtime
    from app.services.product_search import ProductSearchService
    client.app.state.product_search = ProductSearchService(
        catalog=runtime.catalog,
        association_registry=runtime.association_registry,
        observation_registry=runtime.observation_registry,
        include_fixtures=True,
    )
    asyncio.run(runtime.execute(_job()))

    search = client.get("/api/v2/products/search", params={"query": "amul"})
    assert search.status_code == 200
    items = search.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["evidence_state"] == "demo_fixture"
    assert item["fixture_provenance"]

    csrf = client.get("/api/v2/auth/csrf").json()["csrf_token"]
    created = client.post(
        "/api/v2/lists",
        json={"name": "Demo journey"},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    list_id = created.json()["id"]
    added = client.post(
        f"/api/v2/lists/{list_id}/items",
        json={
            "query": "Amul milk",
            "quantity": 2,
            "canonical_product_id": item["canonical_product_id"],
            "canonical_variant_id": item["canonical_variant_id"],
            "source_platform": item["platform"],
            "source_listing_id": item["platform_listing_id"],
            "source_observation_id": item["observation_id"],
        },
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert added.status_code == 201, added.text
    saved = added.json()["items"][0]
    assert saved["resolution_status"] == "exact_confirmed"
    assert saved["evidence_class"] == "demo_fixture"
    assert saved["canonical_variant_id"] == item["canonical_variant_id"]
    assert saved["source_observation_id"] == item["observation_id"]

    optimized = client.post(
        "/api/v2/optimizations",
        json={"list_id": list_id, "expected_revision": added.json()["revision"]},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert optimized.status_code == 201, optimized.text
    result = optimized.json()
    assert result["status"] == "unresolved"
    assert result["completeness"] == "unavailable"
    assert result["offers"] == []
    assert result["optimizer_result"] is None
    assert "demo fixture evidence" in result["explanation"].lower()
    assert result["requested_items"][0]["evidence_class"] == "demo_fixture"
    assert result["unresolved_items"][0]["evidence_class"] == "demo_fixture"
    stored = client.get(f"/api/v2/optimizations/{result['request_id']}")
    assert stored.status_code == 200
    assert stored.json() == result


def test_consumer_optimization_persists_revision_and_replay_is_owner_scoped(auth_client):
    from sqlalchemy import text

    client, mail, database = auth_client
    account = _signup(client, mail, "optimization-owner@example.com")
    user_id = account["user_id"]
    csrf = client.get("/api/v2/auth/csrf").json()["csrf_token"]
    created = client.post("/api/v2/lists", json={"name": "Weekly"}, headers={**_origin(), "X-CSRF-Token": csrf})
    list_id = created.json()["id"]
    added = client.post(
        f"/api/v2/lists/{list_id}/items",
        json={"query": "milk", "quantity": 2},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert added.status_code == 201
    revision = added.json()["revision"]
    request = {"list_id": list_id, "expected_revision": revision}
    assert client.post("/api/v2/optimizations", json=request).status_code == 403
    first = client.post("/api/v2/optimizations", json=request, headers={**_origin(), "X-CSRF-Token": csrf})
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["status"] == "unresolved"
    assert body["completeness"] == "unavailable"
    assert body["requested_items"][0]["quantity"] == 2
    assert body["offers"] == []
    assert body["optimizer_result"] is None
    replay = client.post("/api/v2/optimizations", json=request, headers={**_origin(), "X-CSRF-Token": csrf})
    assert replay.status_code == 200
    assert replay.json() == body
    stored = client.get(f"/api/v2/optimizations/{body['request_id']}")
    assert stored.status_code == 200
    assert stored.json() == body

    item_id = added.json()["items"][0]["id"]
    changed = client.patch(
        f"/api/v2/lists/{list_id}/items/{item_id}",
        json={"quantity": 3},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert changed.status_code == 200
    assert client.get(f"/api/v2/optimizations/{body['request_id']}").json() == body
    stale = client.post("/api/v2/optimizations", json=request, headers={**_origin(), "X-CSRF-Token": csrf})
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_list_revision"

    with database.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM optimization_requests WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar_one() == 1
        assert connection.execute(
            text("SELECT count(*) FROM optimization_plans WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar_one() == 0

    _signup(client, mail, "optimization-other@example.com")
    assert client.get(f"/api/v2/optimizations/{body['request_id']}").status_code == 404


def test_signup_persists_verification_challenge_and_outbox_with_autoflush_disabled(auth_client):
    import hashlib
    from datetime import datetime, timezone

    client, mail, engine = auth_client
    session = client.app.state.db_session_factory()
    try:
        assert session.autoflush is False
    finally:
        session.close()

    email = "challenge-persistence@example.com"
    response = client.post(
        "/api/v2/auth/signup",
        json={"email": email, "password": "correct-horse-battery-staple-1"},
        headers=_origin(),
    )
    assert response.status_code == 202, response.text
    mail.refresh(email)
    assert mail.messages

    token = _verification_token(mail, email)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with engine.connect() as connection:
        challenge = connection.execute(
            text(
                "SELECT id, purpose, token_hash, expires_at FROM verification_challenges "
                "WHERE token_hash = :token_hash"
            ),
            {"token_hash": token_hash},
        ).one()
        outbox = connection.execute(
            text(
                "SELECT event_key, recipient FROM email_outbox_events "
                "WHERE event_type = 'email_verification' AND recipient = :recipient"
            ),
            {"recipient": email},
        ).one()

    assert challenge.purpose == "email_verification"
    assert challenge.token_hash == token_hash
    assert token not in challenge.token_hash
    assert challenge.expires_at > datetime.now(timezone.utc)
    assert outbox.event_key == f"email_verification:{challenge.id}"
    assert outbox.recipient == email


def test_synthetic_demo_catalog_journey_persists_unknown_states_and_is_owner_scoped(
    synthetic_demo_auth_client,
):
    client, mail, database = synthetic_demo_auth_client
    _signup(client, mail, "synthetic-owner@example.com")

    # Discovery is exposed only through the demo gate, and never as live
    # retailer evidence. Blinkit must not appear even when a broad query matches.
    search = client.get("/api/v2/products/search", params={"query": "milk", "limit": 100})
    assert search.status_code == 200, search.text
    items = search.json()["items"]
    assert items
    assert all(item["evidence_state"] == "synthetic_demo" for item in items)
    assert all(item["synthetic"] is True for item in items)
    assert all(item["platform"] == "CARTEL_DEMO" for item in items)
    assert all(item["parser_version"] == "synthetic-v1" for item in items)
    assert all(item["source_reference"].startswith("synthetic://cartel-demo/") for item in items)
    assert all(item["platform"] != "BLINKIT" for item in items)

    by_listing = {item["platform_listing_id"]: item for item in items}
    milk = by_listing["cartel-demo-listing-milk-500ml-a"]
    assert milk["pack"] == "500 ml"
    assert milk["price"] == {"currency": "INR", "minor_units": 2800}
    assert milk["availability_signal"] == "available"

    csrf = client.get("/api/v2/auth/csrf").json()["csrf_token"]
    created = client.post(
        "/api/v2/lists",
        json={"name": "Synthetic demo list"},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert created.status_code == 201, created.text
    list_id = created.json()["id"]

    def add(payload: dict) -> dict:
        response = client.post(
            f"/api/v2/lists/{list_id}/items",
            json=payload,
            headers={**_origin(), "X-CSRF-Token": csrf},
        )
        assert response.status_code == 201, response.text
        return response.json()

    added = add(
        {
            "query": milk["canonical_display_name"],
            "quantity": 2,
            "canonical_product_id": milk["canonical_product_id"],
            "canonical_variant_id": milk["canonical_variant_id"],
            "source_platform": milk["platform"],
            "source_listing_id": milk["platform_listing_id"],
            "source_observation_id": milk["observation_id"],
        }
    )
    milk_item = next(
        item
        for item in added["items"]
        if item["canonical_variant_id"] == "cartel-demo-variant-milk-500ml"
    )
    assert milk_item["resolution_status"] == "exact_confirmed"
    assert milk_item["evidence_class"] == "synthetic_demo"

    rice_search = client.get(
        "/api/v2/products/search", params={"query": "Cartel Demo Basmati Rice", "limit": 100}
    )
    rice_items = {item["platform_listing_id"]: item for item in rice_search.json()["items"]}
    unavailable_rice = rice_items["cartel-demo-listing-rice-1kg-a"]
    assert unavailable_rice["availability_signal"] == "unavailable"
    added = add(
        {
            "query": unavailable_rice["canonical_display_name"],
            "quantity": 1,
            "canonical_product_id": unavailable_rice["canonical_product_id"],
            "canonical_variant_id": unavailable_rice["canonical_variant_id"],
            "source_platform": unavailable_rice["platform"],
            "source_listing_id": unavailable_rice["platform_listing_id"],
            "source_observation_id": unavailable_rice["observation_id"],
        }
    )
    rice_item = next(
        item
        for item in added["items"]
        if item["canonical_variant_id"] == "cartel-demo-variant-rice-1kg"
    )
    assert rice_item["resolution_status"] == "exact_confirmed"
    assert rice_item["evidence_class"] == "synthetic_demo"

    added = add({"query": "Cartel Demo Unmatched Item", "quantity": 1})
    unmatched_item = next(
        item for item in added["items"] if item["query"] == "Cartel Demo Unmatched Item"
    )
    assert unmatched_item["resolution_status"] == "unresolved"
    assert unmatched_item["evidence_class"] == "live"

    list_response = client.get(f"/api/v2/lists/{list_id}")
    assert list_response.status_code == 200
    revision = list_response.json()["revision"]
    assert len(list_response.json()["items"]) == 3

    optimized = client.post(
        "/api/v2/optimizations",
        json={"list_id": list_id, "expected_revision": revision},
        headers={**_origin(), "X-CSRF-Token": csrf},
    )
    assert optimized.status_code == 201, optimized.text
    result = optimized.json()

    assert result["status"] == "unresolved"
    assert result["completeness"] == "partial"
    assert result["optimizer_result"] is None
    assert "synthetic" in result["explanation"].lower()
    assert "fees" in result["explanation"].lower()
    assert "unknown" in result["explanation"].lower()

    exact_requested = [
        item for item in result["requested_items"] if item["resolution_status"] == "exact_confirmed"
    ]
    assert len(exact_requested) == 2
    assert all(item["evidence_class"] == "synthetic_demo" for item in exact_requested)
    assert all(item["synthetic"] is True for item in exact_requested)

    # Every currently-available synthetic listing produces an observed synthetic
    # offer; the explicitly unavailable rice listing does not.
    assert result["offers"], result
    assert all(offer["is_synthetic"] is True for offer in result["offers"])
    assert all(offer["evidence_class"] == "synthetic_demo" for offer in result["offers"])
    assert all(
        offer["observation_state"] == "synthetic_demo_observation"
        for offer in result["offers"]
    )
    assert {offer["canonical_variant_id"] for offer in result["offers"]} == {
        "cartel-demo-variant-milk-500ml",
        "cartel-demo-variant-rice-1kg",
    }
    assert all(
        offer["platform_listing_id"] != "cartel-demo-listing-rice-1kg-a"
        for offer in result["offers"]
    )
    assert all(offer["tax_status"] == "UNKNOWN" for offer in result["offers"])
    assert all(offer["fees_status"] == "unknown" for offer in result["offers"])
    assert all(offer["checkout_total"] is None for offer in result["offers"])
    assert all(offer["source_reference"].startswith("synthetic://cartel-demo/") for offer in result["offers"])

    # Unavailable synthetic evidence and the free-text request stay unresolved
    # rather than being estimated.
    unresolved_variants = {
        item.get("canonical_variant_id") for item in result["unresolved_items"]
    }
    assert "cartel-demo-variant-rice-1kg" in unresolved_variants
    assert any(
        item["query"] == "Cartel Demo Unmatched Item" for item in result["unresolved_items"]
    )

    # Persisted result survives reload without loss or re-derivation.
    stored = client.get(f"/api/v2/optimizations/{result['request_id']}")
    assert stored.status_code == 200
    assert stored.json() == result

    with database.connect() as connection:
        assert connection.execute(
            text(
                "SELECT count(*) FROM optimization_plans p "
                "JOIN optimization_requests r ON r.id = p.request_record_id "
                "WHERE r.request_id = :request_id"
            ),
            {"request_id": result["request_id"]},
        ).scalar_one() == 0

    # A second user cannot read the first user's list or optimization result.
    _signup(client, mail, "synthetic-other@example.com")
    assert client.get(f"/api/v2/lists/{list_id}").status_code == 404
    assert client.get(f"/api/v2/optimizations/{result['request_id']}").status_code == 404
    assert client.get("/api/v2/lists").json() == []


def test_cross_user_isolation_is_enforced_in_both_directions(auth_client):
    """Each owner is denied the other's list and optimization with valid ids.

    The API uses a not-found (404) convention for resources owned by another
    user, so it does not leak the existence of the other user's records.
    """

    client, mail, _ = auth_client
    _signup(client, mail, "isolation-a@example.com")
    cookie_a = client.cookies.get("cartel_session")
    assert cookie_a
    headers_a = {**_origin(), "Cookie": f"cartel_session={cookie_a}"}
    csrf_a = client.get("/api/v2/auth/csrf", headers=headers_a).json()["csrf_token"]

    list_a = client.post(
        "/api/v2/lists",
        json={"name": "A list"},
        headers={**headers_a, "X-CSRF-Token": csrf_a},
    )
    assert list_a.status_code == 201, list_a.text
    list_a_id = list_a.json()["id"]
    added_a = client.post(
        f"/api/v2/lists/{list_a_id}/items",
        json={"query": "milk", "quantity": 1},
        headers={**headers_a, "X-CSRF-Token": csrf_a},
    )
    assert added_a.status_code == 201, added_a.text
    item_a_id = added_a.json()["items"][0]["id"]
    optimization_a = client.post(
        "/api/v2/optimizations",
        json={"list_id": list_a_id, "expected_revision": added_a.json()["revision"]},
        headers={**headers_a, "X-CSRF-Token": csrf_a},
    )
    assert optimization_a.status_code == 201, optimization_a.text
    optimization_a_id = optimization_a.json()["request_id"]

    _signup(client, mail, "isolation-b@example.com")
    cookie_b = client.cookies.get("cartel_session")
    assert cookie_b and cookie_b != cookie_a
    headers_b = {**_origin(), "Cookie": f"cartel_session={cookie_b}"}
    csrf_b = client.get("/api/v2/auth/csrf", headers=headers_b).json()["csrf_token"]

    list_b = client.post(
        "/api/v2/lists",
        json={"name": "B list"},
        headers={**headers_b, "X-CSRF-Token": csrf_b},
    )
    assert list_b.status_code == 201, list_b.text
    list_b_id = list_b.json()["id"]
    added_b = client.post(
        f"/api/v2/lists/{list_b_id}/items",
        json={"query": "bread", "quantity": 1},
        headers={**headers_b, "X-CSRF-Token": csrf_b},
    )
    assert added_b.status_code == 201, added_b.text
    item_b_id = added_b.json()["items"][0]["id"]
    optimization_b = client.post(
        "/api/v2/optimizations",
        json={"list_id": list_b_id, "expected_revision": added_b.json()["revision"]},
        headers={**headers_b, "X-CSRF-Token": csrf_b},
    )
    assert optimization_b.status_code == 201, optimization_b.text
    optimization_b_id = optimization_b.json()["request_id"]

    # B cannot reach any of A's resources, even with valid ids and valid CSRF.
    assert client.get(f"/api/v2/lists/{list_a_id}", headers=headers_b).status_code == 404
    assert client.patch(
        f"/api/v2/lists/{list_a_id}/items/{item_a_id}",
        json={"quantity": 9},
        headers={**headers_b, "X-CSRF-Token": csrf_b},
    ).status_code == 404
    assert client.get(
        f"/api/v2/optimizations/{optimization_a_id}", headers=headers_b
    ).status_code == 404
    assert [
        entry["id"] for entry in client.get("/api/v2/lists", headers=headers_b).json()
    ] == [list_b_id]

    # A cannot reach any of B's resources, even with valid ids and valid CSRF.
    assert client.get(f"/api/v2/lists/{list_b_id}", headers=headers_a).status_code == 404
    assert client.patch(
        f"/api/v2/lists/{list_b_id}/items/{item_b_id}",
        json={"quantity": 9},
        headers={**headers_a, "X-CSRF-Token": csrf_a},
    ).status_code == 404
    assert client.get(
        f"/api/v2/optimizations/{optimization_b_id}", headers=headers_a
    ).status_code == 404
    assert [
        entry["id"] for entry in client.get("/api/v2/lists", headers=headers_a).json()
    ] == [list_a_id]

    # The denials did not mutate either owner's stored state.
    assert client.get(f"/api/v2/lists/{list_a_id}", headers=headers_a).json()["revision"] == 2
    assert client.get(f"/api/v2/lists/{list_b_id}", headers=headers_b).json()["revision"] == 2


def test_persisted_optimization_survives_new_client_and_app_restart(
    synthetic_demo_auth_client,
):
    """A persisted result is readable by a fresh client and a restarted app.

    The original client is discarded, pooled engines are disposed, and a brand
    new application instance is built against the same disposable PostgreSQL
    database. Field-for-field equality proves the result was stored, not
    re-derived in memory.
    """

    from app.db.session import dispose_engines
    from app.main import create_application

    client, mail, database = synthetic_demo_auth_client
    _signup(client, mail, "restart-owner@example.com")
    cookie = client.cookies.get("cartel_session")
    assert cookie
    headers = {**_origin(), "Cookie": f"cartel_session={cookie}"}
    csrf = client.get("/api/v2/auth/csrf", headers=headers).json()["csrf_token"]

    search = client.get("/api/v2/products/search", params={"query": "milk", "limit": 100})
    assert search.status_code == 200, search.text
    milk = {item["platform_listing_id"]: item for item in search.json()["items"]}[
        "cartel-demo-listing-milk-500ml-a"
    ]
    created = client.post(
        "/api/v2/lists",
        json={"name": "Restart list"},
        headers={**headers, "X-CSRF-Token": csrf},
    )
    assert created.status_code == 201, created.text
    list_id = created.json()["id"]
    added = client.post(
        f"/api/v2/lists/{list_id}/items",
        json={
            "query": milk["canonical_display_name"],
            "quantity": 2,
            "canonical_product_id": milk["canonical_product_id"],
            "canonical_variant_id": milk["canonical_variant_id"],
            "source_platform": milk["platform"],
            "source_listing_id": milk["platform_listing_id"],
            "source_observation_id": milk["observation_id"],
        },
        headers={**headers, "X-CSRF-Token": csrf},
    )
    assert added.status_code == 201, added.text
    revision = added.json()["revision"]
    optimized = client.post(
        "/api/v2/optimizations",
        json={"list_id": list_id, "expected_revision": revision},
        headers={**headers, "X-CSRF-Token": csrf},
    )
    assert optimized.status_code == 201, optimized.text
    result = optimized.json()
    assert result["offers"]
    assert result["optimizer_result"] is None

    settings = client.app.state.settings
    dispose_engines()
    with TestClient(
        create_application(settings, email_delivery=RecordingEmailDelivery(database)),
        base_url="http://testserver",
    ) as restarted:
        reloaded = restarted.get(
            f"/api/v2/optimizations/{result['request_id']}", headers=headers
        )
        assert reloaded.status_code == 200, reloaded.text
        assert reloaded.json() == result

        reloaded_list = restarted.get(f"/api/v2/lists/{list_id}", headers=headers)
        assert reloaded_list.status_code == 200, reloaded_list.text
        assert reloaded_list.json()["revision"] == revision
        assert [
            item["canonical_variant_id"] for item in reloaded_list.json()["items"]
        ] == ["cartel-demo-variant-milk-500ml"]

        # The restarted app still enforces owner scoping on the same record.
        assert restarted.get(
            f"/api/v2/optimizations/{result['request_id']}"
        ).status_code == 401
