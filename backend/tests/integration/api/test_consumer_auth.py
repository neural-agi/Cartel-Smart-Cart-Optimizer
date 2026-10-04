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
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str]] = []

    def send(self, recipient: str, subject: str, body: str) -> None:
        self.messages.append((recipient, subject, body))


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
    mail = RecordingEmailDelivery()
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


def _origin() -> dict[str, str]:
    return {"Origin": "http://testserver"}


def _verification_token(mail: RecordingEmailDelivery) -> str:
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
    assert mail.messages, response.text
    verified = client.post(
        "/api/v2/auth/email/verify",
        json={"token": _verification_token(mail)},
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
    reset_token = _verification_token(mail)
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
        json={"token": _verification_token(mail), "new_password": "reset-password-with-enough-length-3"},
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


def test_consumer_optimization_persists_revision_and_replay_is_owner_scoped(auth_client):
    from sqlalchemy import text

    client, mail, database = auth_client
    _signup(client, mail, "optimization-owner@example.com")
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
        assert connection.execute(text("SELECT count(*) FROM optimization_requests")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM optimization_plans")).scalar_one() == 0

    _signup(client, mail, "optimization-other@example.com")
    assert client.get(f"/api/v2/optimizations/{body['request_id']}").status_code == 404
