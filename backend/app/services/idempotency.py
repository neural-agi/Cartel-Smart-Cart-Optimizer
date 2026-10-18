"""Database-backed idempotency primitives for persistent mutations.

A claim and its domain mutation must be committed in the same SQLAlchemy
transaction. The unique database constraint arbitrates claims across workers.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import IdempotencyRecord


@dataclass(frozen=True)
class IdempotencyClaim:
    """Claim result; only ``execute`` owns the mutation and completes it."""

    action: str
    record: IdempotencyRecord | None = None
    status_code: int | None = None
    response_body: dict[str, Any] | None = None

    @property
    def should_execute(self) -> bool:
        return self.action == "execute"

    @property
    def is_replay(self) -> bool:
        return self.action == "replay"


def request_hash(payload: object) -> str:
    """Hash JSON-compatible request data with deterministic key ordering."""
    try:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("idempotency payload must be finite JSON data") from exc
    return hashlib.sha256(encoded).hexdigest()


def idempotency_key(request: Request) -> str | None:
    """Read and validate the optional Idempotency-Key header."""
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
    wait_timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.05,
) -> IdempotencyClaim:
    """Claim a key, replay a completed result, or reject a conflicting request.

    The caller must commit the returned new claim in the same transaction as
    its mutation and call :func:`complete` before that commit. If another
    transaction has claimed the same key, PostgreSQL's unique constraint makes
    the insert wait. After the winner commits, this function reads the stored
    response; if the winner rolls back, this transaction can claim and execute.
    """
    if key is None:
        return IdempotencyClaim(action="execute")
    if not operation or len(operation) > 64:
        raise ValueError("operation must contain between 1 and 64 characters")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    if wait_timeout_seconds <= 0 or poll_interval_seconds <= 0:
        raise ValueError("wait and poll intervals must be positive")

    digest = request_hash(payload)
    identity = (
        IdempotencyRecord.user_id == user_id,
        IdempotencyRecord.operation == operation,
        IdempotencyRecord.key == key,
    )
    deadline = time.monotonic() + wait_timeout_seconds
    owns_outer_transaction = db.in_transaction()
    managed_outer_transaction = bool(getattr(db, "_trans_context_manager", None))

    while True:
        now = datetime.now(timezone.utc)
        existing = db.scalar(select(IdempotencyRecord).where(*identity).with_for_update())
        if existing is not None and _as_utc(existing.expires_at) <= now:
            db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.id == existing.id))
            db.flush()
            existing = None

        if existing is not None:
            if existing.request_hash != digest:
                raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict"})
            if existing.status_code > 0:
                return IdempotencyClaim(
                    action="replay",
                    record=existing,
                    status_code=existing.status_code,
                    response_body=existing.response_body,
                )
            if time.monotonic() >= deadline:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "idempotency_request_in_progress"},
                    headers={"Retry-After": "1"},
                )
            _release_transaction_for_wait(db)
            time.sleep(poll_interval_seconds)
            if owns_outer_transaction and not managed_outer_transaction:
                db.begin()
            continue

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
            db.add(record)
            db.flush()
            return IdempotencyClaim(action="execute", record=record)
        except IntegrityError:
            # A competing insert can only win through the unique DB constraint.
            _release_transaction_for_wait(db)
            if time.monotonic() >= deadline:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "idempotency_request_in_progress"},
                    headers={"Retry-After": "1"},
                )
            time.sleep(poll_interval_seconds)
            if owns_outer_transaction and not managed_outer_transaction:
                db.begin()


def _release_transaction_for_wait(db: Session) -> None:
    """Release a read/lock snapshot while waiting for another transaction."""
    db.rollback()


def complete(
    claim_result: IdempotencyClaim,
    *,
    status_code: int,
    response_body: dict[str, Any],
) -> None:
    """Persist the response in the caller's mutation transaction."""
    if not claim_result.should_execute or claim_result.record is None:
        return
    if not 100 <= status_code <= 599:
        raise ValueError("status_code must be a valid HTTP status")
    request_hash(response_body)
    claim_result.record.status_code = status_code
    claim_result.record.response_body = response_body


def _as_utc(value: datetime) -> datetime:
    # Some lightweight test dialects return naive timestamps despite the
    # timezone-aware column declaration. PostgreSQL returns aware values.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
