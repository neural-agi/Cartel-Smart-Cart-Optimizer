from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
import httpx
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app.auth.service import csrf_token_for_session
from app.core.config import Settings
from app.db.base import Base
from app.db.models import (
    AuthSession,
    IdempotencyRecord,
    OptimizationAllocationRecord,
    OptimizationPlanRecord,
    OptimizationRequestRecord,
    ShoppingList,
    ShoppingListItem,
    User,
)
from app.db.session import get_db
from app.main import create_application


if "app" not in __import__("inspect").signature(httpx.Client.__init__).parameters:
    _httpx_init = httpx.Client.__init__

    def _httpx_compatible_init(self, *args, app=None, **kwargs):
        _httpx_init(self, *args, **kwargs)

    httpx.Client.__init__ = _httpx_compatible_init


MUTATING_ROUTES = (
    ("POST", "/api/v1/lists", {"name": "test"}),
    ("PATCH", "/api/v1/lists/00000000-0000-0000-0000-000000000001", {"name": "test"}),
    ("POST", "/api/v1/lists/00000000-0000-0000-0000-000000000001/items", {"query": "test"}),
    ("PATCH", "/api/v1/lists/00000000-0000-0000-0000-000000000001/items/00000000-0000-0000-0000-000000000002", {"quantity": 2}),
    ("DELETE", "/api/v1/lists/00000000-0000-0000-0000-000000000001/items/00000000-0000-0000-0000-000000000002", None),
    ("POST", "/api/v1/optimizations", {"list_id": "00000000-0000-0000-0000-000000000001", "expected_revision": 1}),
)


@pytest.fixture
def app_db(tmp_path):
    import os

    database_url = os.environ.get("CARTEL_TEST_DATABASE_URL", "")
    if not database_url.startswith("postgresql+"):
        pytest.skip("CARTEL_TEST_DATABASE_URL must point to PostgreSQL")
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "TRUNCATE TABLE optimization_allocations, optimization_plans, optimization_requests, "
            "shopping_list_items, shopping_lists, idempotency_records, audit_events, sessions, users "
            "CASCADE"
        ))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_application(Settings(_env_file=None, data_dir=tmp_path, auth_required=False, database_url_override=database_url))
    app.state.db_session_factory = factory
    user_id = uuid4()
    token = f"consumer-session-{user_id}"
    csrf = csrf_token_for_session(token)
    with factory.begin() as db:
        user = User(id=user_id)
        db.add(user)
        db.flush()
        db.add(AuthSession(
            user_id=user_id,
            token_hash=__import__("hashlib").sha256(token.encode()).hexdigest(),
            csrf_hash=__import__("hashlib").sha256(csrf.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            last_seen_at=datetime.now(timezone.utc),
        ))
    with TestClient(app) as client:
        client.cookies.set("cartel_session", token)
        client.headers.update({"Origin": "http://localhost:3000", "X-CSRF-Token": csrf})
        yield client, factory, user_id, app, token, csrf
    engine.dispose()


def count(factory, model):
    with factory() as db:
        return db.scalar(select(func.count()).select_from(model))


def independent_list_state(list_id):
    import os

    engine = create_engine(os.environ["CARTEL_TEST_DATABASE_URL"])
    try:
        with engine.connect() as connection:
            backend_pid = connection.scalar(text("SELECT pg_backend_pid()"))
            list_row = connection.execute(
                text("SELECT id, name, revision FROM shopping_lists WHERE id = :list_id"),
                {"list_id": list_id},
            ).mappings().one()
            item_rows = connection.execute(
                text(
                    "SELECT id, list_id, query, quantity, resolution_status "
                    "FROM shopping_list_items WHERE list_id = :list_id ORDER BY id"
                ),
                {"list_id": list_id},
            ).mappings().all()
            return backend_pid, dict(list_row), [dict(row) for row in item_rows]
    finally:
        engine.dispose()


def test_operator_bearer_and_consumer_cookie_are_separate(app_db):
    client, _, _, _, _, _ = app_db
    consumer = client.get("/api/v1/lists")
    assert consumer.status_code == 200
    operator_app = create_application(Settings(
        _env_file=None,
        data_dir=app_db[3].state.settings.data_dir,
        auth_required=True,
        auth_tokens="operator=operator-token",
    ))
    operator_client = TestClient(operator_app)
    assert operator_client.get("/api/v1/products/search", params={"query": "milk"}).status_code == 401
    assert operator_client.get(
        "/api/v1/products/search", params={"query": "milk"},
        headers={"Authorization": "Bearer operator-token"},
    ).status_code == 200
    assert operator_client.get(
        "/api/v1/lists", headers={"Authorization": "Bearer operator-token"}
    ).status_code == 401


@pytest.mark.parametrize(("method", "path", "payload"), MUTATING_ROUTES)
def test_every_cookie_mutation_requires_csrf(app_db, method, path, payload):
    client, _, _, _, _, _ = app_db
    headers = {"Origin": "http://localhost:3000"}
    request_headers = {
        key: value
        for key, value in client.headers.items()
        if key.lower() not in {"origin", "x-csrf-token", "idempotency-key"}
    }
    request_headers.update({**headers, "Idempotency-Key": f"csrf-{method}-{path}"})
    isolated_client = TestClient(client.app, headers=request_headers)
    isolated_client.cookies.set("cartel_session", client.cookies.get("cartel_session"))
    response = isolated_client.request(method, path, json=payload)
    assert "Origin" in response.request.headers
    assert "X-CSRF-Token" not in response.request.headers
    assert response.status_code == 403
    assert response.json() == {"detail": {"code": "csrf_failed"}}


def test_consumer_auth_rejects_missing_expired_and_revoked_sessions(app_db):
    client, factory, user_id, _, _, _ = app_db
    no_cookie = TestClient(client.app)
    assert no_cookie.get("/api/v1/lists").status_code == 401
    expired_token = f"expired-{uuid4()}"
    expired_csrf = csrf_token_for_session(expired_token)
    with factory.begin() as db:
        db.add(AuthSession(
            user_id=user_id,
            token_hash=__import__("hashlib").sha256(expired_token.encode()).hexdigest(),
            csrf_hash=__import__("hashlib").sha256(expired_csrf.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            last_seen_at=datetime.now(timezone.utc),
        ))
    expired = TestClient(client.app)
    expired.cookies.set("cartel_session", expired_token)
    assert expired.get("/api/v1/lists").status_code == 401
    revoked = TestClient(client.app)
    revoked.cookies.set("cartel_session", "revoked-token")
    assert revoked.get("/api/v1/lists").status_code == 401


def test_consumer_session_rotation_revokes_old_token(app_db):
    client, factory, _, _, old_token, _ = app_db
    rotated = client.post("/api/v1/auth/session/rotate")
    assert rotated.status_code == 200
    new_token = rotated.json()["session_token"]
    with factory() as db:
        old = db.scalar(select(AuthSession).where(AuthSession.token_hash == __import__("hashlib").sha256(old_token.encode()).hexdigest()))
        new = db.scalar(select(AuthSession).where(AuthSession.token_hash == __import__("hashlib").sha256(new_token.encode()).hexdigest()))
        assert old is not None and old.revoked_at is not None
        assert new is not None and new.revoked_at is None
    old_client = TestClient(client.app)
    old_client.cookies.set("cartel_session", old_token)
    assert old_client.get("/api/v1/lists").status_code == 401
    new_client = TestClient(client.app)
    new_client.cookies.set("cartel_session", new_token)
    assert new_client.get("/api/v1/lists").status_code == 200


def test_create_list_replay_and_payload_mismatch(app_db):
    client, factory, _, _, _, _ = app_db
    headers = {"Idempotency-Key": "list-create"}
    first = client.post("/api/v1/lists", json={"name": "Groceries"}, headers=headers)
    replay = client.post("/api/v1/lists", json={"name": "Groceries"}, headers=headers)
    mismatch = client.post("/api/v1/lists", json={"name": "Other"}, headers=headers)
    assert first.status_code == 201
    assert replay.status_code == 201 and replay.json() == first.json()
    assert mismatch.status_code == 409
    assert count(factory, ShoppingList) == 1
    assert count(factory, IdempotencyRecord) == 1


def test_list_ownership_isolation(app_db):
    client, _, _, _, _, _ = app_db
    first = client.post("/api/v1/lists", json={"name": "Private"}, headers={"Idempotency-Key": "private"})
    other_token = f"other-{uuid4()}"
    other_user = uuid4()
    csrf = csrf_token_for_session(other_token)
    factory = client.app.state.db_session_factory
    with factory.begin() as db:
        db.add(User(id=other_user))
        db.flush()
        db.add(AuthSession(
            user_id=other_user,
            token_hash=__import__("hashlib").sha256(other_token.encode()).hexdigest(),
            csrf_hash=__import__("hashlib").sha256(csrf.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            last_seen_at=datetime.now(timezone.utc),
        ))
    other = TestClient(client.app)
    other.cookies.set("cartel_session", other_token)
    response = other.get(f"/api/v1/lists/{first.json()['id']}")
    assert response.status_code == 404


def test_add_item_replay_and_repeat_updates_are_idempotent(app_db):
    client, factory, _, _, _, _ = app_db
    created = client.post("/api/v1/lists", json={"name": "List"}, headers={"Idempotency-Key": "list"})
    list_id = created.json()["id"]
    headers = {"Idempotency-Key": "item-add"}
    before = count(factory, ShoppingListItem)
    first = client.post(f"/api/v1/lists/{list_id}/items", json={"query": "milk", "quantity": 2}, headers=headers)
    replay = client.post(f"/api/v1/lists/{list_id}/items", json={"query": "milk", "quantity": 2}, headers=headers)
    assert first.status_code == 201 and replay.status_code == 201
    assert replay.json() == first.json()
    assert len(first.json()["items"]) == 1
    assert first.json()["revision"] == created.json()["revision"] + 1
    assert before == 0 and count(factory, ShoppingListItem) == 1
    _, persisted_list, persisted_items = independent_list_state(list_id)
    assert persisted_list["revision"] == first.json()["revision"]
    assert len(persisted_items) == 1
    assert str(persisted_items[0]["id"]) == first.json()["items"][0]["id"]
    assert persisted_items[0]["quantity"] == 2
    item_id = first.json()["items"][0]["id"]

    update_headers = {"Idempotency-Key": "update-quantity"}
    first_update = client.patch(f"/api/v1/lists/{list_id}/items/{item_id}", json={"quantity": 3}, headers=update_headers)
    revision = first_update.json()["revision"]
    second_update = client.patch(f"/api/v1/lists/{list_id}/items/{item_id}", json={"quantity": 3}, headers=update_headers)
    assert second_update.json() == first_update.json()
    assert second_update.json()["revision"] == revision
    _, persisted_list, persisted_items = independent_list_state(list_id)
    assert persisted_list["revision"] == revision
    assert persisted_items[0]["quantity"] == 3
    assert count(factory, ShoppingListItem) == 1

    assert first.status_code == 201 and replay.status_code == 201
    assert replay.json() == first.json()
    assert before == 0 and count(factory, ShoppingListItem) == 1
    item_id = first.json()["items"][0]["id"]

    update_headers = {"Idempotency-Key": "update-quantity"}
    first_update = client.patch(f"/api/v1/lists/{list_id}/items/{item_id}", json={"quantity": 3}, headers=update_headers)
    revision = first_update.json()["revision"]
    second_update = client.patch(f"/api/v1/lists/{list_id}/items/{item_id}", json={"quantity": 3}, headers=update_headers)
    assert second_update.json() == first_update.json()
    assert second_update.json()["revision"] == revision
    assert count(factory, ShoppingListItem) == 1


def test_list_patch_and_remove_replay_do_not_repeat_revision_or_delete(app_db):
    client, factory, _, _, _, _ = app_db
    created = client.post("/api/v1/lists", json={"name": "List"}, headers={"Idempotency-Key": "list"})
    list_id = created.json()["id"]
    added = client.post(f"/api/v1/lists/{list_id}/items", json={"query": "bread"}, headers={"Idempotency-Key": "item"})
    item_id = added.json()["items"][0]["id"]
    header = {"Idempotency-Key": "rename-archive"}
    first = client.patch(f"/api/v1/lists/{list_id}", json={"name": "Renamed"}, headers=header)
    replay = client.patch(f"/api/v1/lists/{list_id}", json={"name": "Renamed"}, headers=header)
    assert replay.json() == first.json()
    assert replay.json()["revision"] == first.json()["revision"]
    _, persisted_list, persisted_items = independent_list_state(list_id)
    assert persisted_list["name"] == "Renamed"
    assert persisted_list["revision"] == first.json()["revision"]
    assert len(persisted_items) == 1

    delete_headers = {"Idempotency-Key": "remove"}
    before = count(factory, ShoppingListItem)
    first_delete = client.delete(f"/api/v1/lists/{list_id}/items/{item_id}", headers=delete_headers)
    replay_delete = client.delete(f"/api/v1/lists/{list_id}/items/{item_id}", headers=delete_headers)
    assert first_delete.status_code == replay_delete.status_code == 204
    assert before == 1 and count(factory, ShoppingListItem) == 0


def test_failed_mutation_rolls_back_claim_and_rows_then_retry_succeeds(app_db, monkeypatch):
    client, factory, _, _, _, _ = app_db
    from app.api.routes import lists as list_routes

    original = list_routes._audit
    def fail_after_claim(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("forced post-claim failure")

    monkeypatch.setattr(list_routes, "_audit", fail_after_claim)
    with pytest.raises(RuntimeError):
        client.post("/api/v1/lists", json={"name": "Retry"}, headers={"Idempotency-Key": "retry"})
    assert count(factory, ShoppingList) == 0
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0

    monkeypatch.setattr(list_routes, "_audit", original)
    retry = client.post("/api/v1/lists", json={"name": "Retry"}, headers={"Idempotency-Key": "retry"})
    assert retry.status_code == 201
    assert count(factory, ShoppingList) == 1
    assert count(factory, IdempotencyRecord) == 1


def test_optimization_create_persists_immutable_snapshot_and_replays(app_db):
    client, factory, _, _, _, _ = app_db
    created = client.post("/api/v1/lists", json={"name": "List"}, headers={"Idempotency-Key": "list"})
    list_id = created.json()["id"]
    payload = {"list_id": list_id, "expected_revision": created.json()["revision"]}
    headers = {"Idempotency-Key": "optimization-1"}
    first = client.post("/api/v1/optimizations", json=payload, headers=headers)
    assert first.status_code == 201
    first_request_count = count(factory, OptimizationRequestRecord)
    replay = client.post("/api/v1/optimizations", json=payload, headers=headers)
    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert first_request_count == count(factory, OptimizationRequestRecord) == 1
    with factory() as db:
        record = db.scalar(select(OptimizationRequestRecord))
        assert record.result_snapshot.get("observed_listing_prices") == []
        first_snapshot = record.result_snapshot.copy()
    next_result = client.post(
        "/api/v1/optimizations",
        json={"list_id": list_id, "expected_revision": created.json()["revision"]},
        headers={"Idempotency-Key": "optimization-2"},
    )
    assert next_result.status_code == 200
    assert next_result.json() == first.json()
    assert count(factory, OptimizationRequestRecord) == 1
    with factory() as db:
        record = db.scalar(select(OptimizationRequestRecord))
        assert record.result_snapshot == first_snapshot


def test_optimization_rejects_stale_revision_and_cross_user_access(app_db):
    client, factory, _, _, _, _ = app_db
    created = client.post("/api/v1/lists", json={"name": "List"}, headers={"Idempotency-Key": "list"})
    list_id = created.json()["id"]
    patch = client.patch(
        f"/api/v1/lists/{list_id}", json={"name": "Changed"},
        headers={"Idempotency-Key": "rename"},
    )
    stale = client.post(
        "/api/v1/optimizations",
        json={"list_id": list_id, "expected_revision": created.json()["revision"]},
        headers={"Idempotency-Key": "stale-opt"},
    )
    assert patch.status_code == 200
    assert stale.status_code == 409
    other_token = f"other-{uuid4()}"
    other_user = uuid4()
    csrf = csrf_token_for_session(other_token)
    with factory.begin() as db:
        db.add(User(id=other_user))
        db.flush()
        db.add(AuthSession(
            user_id=other_user,
            token_hash=__import__("hashlib").sha256(other_token.encode()).hexdigest(),
            csrf_hash=__import__("hashlib").sha256(csrf.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            last_seen_at=datetime.now(timezone.utc),
        ))
    other = TestClient(client.app)
    other.cookies.set("cartel_session", other_token)
    response = other.get(f"/api/v1/optimizations/{list_id}")
    assert response.status_code == 404


def test_optimization_mismatched_key_payload_conflicts(app_db):
    client, _, _, _, _, _ = app_db
    created = client.post("/api/v1/lists", json={"name": "List"}, headers={"Idempotency-Key": "list"})
    list_id = created.json()["id"]
    headers = {"Idempotency-Key": "same-key"}
    first = client.post("/api/v1/optimizations", json={"list_id": list_id, "expected_revision": 1}, headers=headers)
    second = client.post("/api/v1/optimizations", json={"list_id": list_id, "expected_revision": 2}, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 409


def test_optimization_same_deterministic_request_reuses_immutable_record(app_db):
    client, factory, _, _, _, _ = app_db
    created = client.post("/api/v1/lists", json={"name": "List"}, headers={"Idempotency-Key": "list"})
    payload = {"list_id": created.json()["id"], "expected_revision": 1}
    first = client.post("/api/v1/optimizations", json=payload, headers={"Idempotency-Key": "first-opt"})
    assert first.status_code == 201
    assert count(factory, OptimizationRequestRecord) == 1
    with factory() as db:
        record = db.scalar(select(OptimizationRequestRecord))
        snapshot = record.result_snapshot.copy()
        plan_ids = [row.id for row in db.scalars(select(OptimizationPlanRecord)).all()]
        allocation_ids = [row.id for row in db.scalars(select(OptimizationAllocationRecord)).all()]
    second = client.post("/api/v1/optimizations", json=payload, headers={"Idempotency-Key": "second-opt"})
    assert second.status_code == 200
    assert second.json() == first.json()
    assert count(factory, OptimizationRequestRecord) == 1
    with factory() as db:
        record = db.scalar(select(OptimizationRequestRecord))
        assert record.result_snapshot == snapshot
        assert [row.id for row in db.scalars(select(OptimizationPlanRecord)).all()] == plan_ids
        assert [row.id for row in db.scalars(select(OptimizationAllocationRecord)).all()] == allocation_ids


def test_optimization_read_is_owner_scoped(app_db):
    client, factory, _, _, _, _ = app_db
    created = client.post("/api/v1/lists", json={"name": "List"}, headers={"Idempotency-Key": "list"})
    first = client.post("/api/v1/optimizations", json={"list_id": created.json()["id"], "expected_revision": 1}, headers={"Idempotency-Key": "opt"})
    optimization_id = first.json()["optimization_id"]
    other_token = f"other-{uuid4()}"
    other_user = uuid4()
    csrf = csrf_token_for_session(other_token)
    with factory.begin() as db:
        db.add(User(id=other_user))
        db.flush()
        db.add(AuthSession(
            user_id=other_user,
            token_hash=__import__("hashlib").sha256(other_token.encode()).hexdigest(),
            csrf_hash=__import__("hashlib").sha256(csrf.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            last_seen_at=datetime.now(timezone.utc),
        ))
    other = TestClient(client.app)
    other.cookies.set("cartel_session", other_token)
    assert other.get(f"/api/v1/optimizations/{optimization_id}").status_code == 404
