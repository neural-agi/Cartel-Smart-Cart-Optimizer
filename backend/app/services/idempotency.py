"""Small PostgreSQL-backed idempotency boundary for consumer mutations."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import IdempotencyRecord
from app.core.metrics import metrics


def request_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def idempotency_key(request: Request) -> str | None:
    value = request.headers.get("Idempotency-Key")
    if value is None:
        return None
    value = value.strip()
    if not 1 <= len(value) <= 128 or any(ord(char) < 33 or ord(char) > 126 for char in value):
        raise HTTPException(status_code=422, detail={"code": "invalid_idempotency_key"})
    return value


def claim(
    db: Session,
    *,
    user_id: UUID,
    operation: str,
    key: str | None,
    payload: object,
    ttl_seconds: int,
) -> IdempotencyRecord | None:
    if key is None:
        return None
    digest = request_hash(payload)
    now = datetime.now(timezone.utc)
    existing = db.scalar(select(IdempotencyRecord).where(
        IdempotencyRecord.user_id == user_id,
        IdempotencyRecord.operation == operation,
        IdempotencyRecord.key == key,
    ).with_for_update())
    if existing is not None and existing.expires_at <= now:
        db.delete(existing)
        db.flush()
        existing = None
    if existing is not None:
        if existing.request_hash != digest:
            metrics.inc("cartel_idempotency_total", operation=operation, outcome="conflict")
            raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict"})
        metrics.inc("cartel_idempotency_total", operation=operation, outcome="replay")
        return existing
    record = IdempotencyRecord(
        user_id=user_id,
        operation=operation,
        key=key,
        request_hash=digest,
        status_code=0,
        response_body={},
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
    except IntegrityError:
        # A concurrent request won the unique key race. The savepoint keeps
        # this request's transaction usable so the committed result can replay.
        existing = db.scalar(select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.key == key,
        ).with_for_update())
        if existing is None:
            raise
        if existing.request_hash != digest:
            raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict"})
        metrics.inc("cartel_idempotency_total", operation=operation, outcome="replay")
        return existing
    metrics.inc("cartel_idempotency_total", operation=operation, outcome="new")
    return None


def complete(record: IdempotencyRecord | None, *, status_code: int, response_body: dict) -> None:
    if record is not None:
        record.status_code = status_code
        record.response_body = response_body
