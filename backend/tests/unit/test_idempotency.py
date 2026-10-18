from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import AuditEvent, IdempotencyRecord, User
from app.services.idempotency import claim, complete


@pytest.fixture
def session_factory(tmp_path):
    database_path = tmp_path / "idempotency.sqlite3"
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    tables = [Base.metadata.tables["users"], AuditEvent.__table__, IdempotencyRecord.__table__]
    Base.metadata.create_all(engine, tables=tables)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(User(id=uuid4()))
    yield factory
    engine.dispose()


def _user_id(factory):
    with factory() as db:
        return db.scalar(select(User.id))


def _claim(db, user_id, key="key-1", payload=None, **kwargs):
    return claim(
        db,
        user_id=user_id,
        operation="shopping_list.create",
        key=key,
        payload=payload if payload is not None else {"name": "Weekly"},
        ttl_seconds=3600,
        **kwargs,
    )


def test_first_request_executes_then_identical_request_replays(session_factory):
    user_id = _user_id(session_factory)
    with session_factory.begin() as db:
        first = _claim(db, user_id)
        assert first.should_execute
        complete(first, status_code=201, response_body={"id": "list-1"})
        db.execute(insert(AuditEvent).values(
            id=uuid4(), user_id=user_id, event_type="list-created", object_type="list",
            object_id="list-1", request_id="req-1",
        ))

    with session_factory() as db:
        replay = _claim(db, user_id)
        assert replay.is_replay
        assert replay.status_code == 201
        assert replay.response_body == {"id": "list-1"}


def test_same_key_with_different_payload_is_rejected(session_factory):
    user_id = _user_id(session_factory)
    with session_factory.begin() as db:
        first = _claim(db, user_id)
        complete(first, status_code=201, response_body={"id": "list-1"})

    with session_factory() as db, pytest.raises(HTTPException) as error:
        _claim(db, user_id, payload={"name": "Other"})
    assert error.value.status_code == 409
    assert error.value.detail == {"code": "idempotency_key_conflict"}


def test_failed_mutation_rolls_back_claim_and_can_retry(session_factory):
    user_id = _user_id(session_factory)
    with session_factory() as db:
        result = _claim(db, user_id)
        assert result.should_execute
        db.rollback()

    with session_factory.begin() as db:
        retry = _claim(db, user_id)
        assert retry.should_execute
        complete(retry, status_code=201, response_body={"id": "list-2"})


def test_persisted_state_survives_session_restart(session_factory):
    user_id = _user_id(session_factory)
    with session_factory.begin() as db:
        result = _claim(db, user_id)
        complete(result, status_code=201, response_body={"id": "durable"})

    restarted_factory = sessionmaker(bind=session_factory.kw["bind"], expire_on_commit=False)
    with restarted_factory() as db:
        replay = _claim(db, user_id)
    assert replay.is_replay
    assert replay.response_body == {"id": "durable"}


def test_user_scope_prevents_cross_user_replay(session_factory):
    first_user = _user_id(session_factory)
    second_user = uuid4()
    with session_factory.begin() as db:
        db.add(User(id=second_user))
    with session_factory.begin() as db:
        result = _claim(db, first_user)
        complete(result, status_code=201, response_body={"owner": str(first_user)})
    with session_factory() as db:
        result = _claim(db, second_user)
    assert result.should_execute


def test_expired_record_is_reclaimed(session_factory):
    user_id = _user_id(session_factory)
    with session_factory.begin() as db:
        result = _claim(db, user_id)
        complete(result, status_code=201, response_body={"old": True})
        assert result.record is not None
        result.record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    with session_factory.begin() as db:
        replacement = _claim(db, user_id)
        assert replacement.should_execute
        complete(replacement, status_code=201, response_body={"new": True})


def test_unique_constraint_prevents_duplicate_scope_key(session_factory):
    user_id = _user_id(session_factory)
    with session_factory.begin() as db:
        result = _claim(db, user_id)
        complete(result, status_code=201, response_body={"id": "one"})
    with session_factory() as db:
        db.add(
            IdempotencyRecord(
                user_id=user_id,
                operation="shopping_list.create",
                key="key-1",
                request_hash="f" * 64,
                status_code=201,
                response_body={},
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()


def test_concurrent_requests_create_only_one_mutation(session_factory):
    user_id = _user_id(session_factory)
    barrier = Barrier(2)

    def run_request(index):
        with session_factory() as db:
            barrier.wait()
            result = _claim(db, user_id, wait_timeout_seconds=5, poll_interval_seconds=0.01)
            if result.should_execute:
                db.execute(insert(AuditEvent).values(
                    id=uuid4(), user_id=user_id, event_type="single-mutation", object_type="list",
                    object_id="created-once", request_id=f"req-{index}",
                ))
                complete(result, status_code=201, response_body={"id": "created-once"})
                db.commit()
            return result.action

    with ThreadPoolExecutor(max_workers=2) as pool:
        actions = list(pool.map(run_request, (1, 2)))

    with session_factory() as db:
        count = db.scalar(
            select(func.count()).select_from(AuditEvent).where(
                AuditEvent.event_type == "single-mutation"
            )
        )
        assert count == 1
        record = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.user_id == user_id))
        assert record.status_code == 201
    assert sorted(actions) == ["execute", "replay"]
