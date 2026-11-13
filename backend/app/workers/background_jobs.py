from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import socket
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import BackgroundJob, EmailOutboxEvent
from app.auth.email_delivery import EmailDelivery, EmailDeliveryUnavailable
from app.core.metrics import metrics

logger = logging.getLogger(__name__)
JobHandler = Callable[[dict[str, Any]], Awaitable[Any]]


def payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def retry_delay(attempt: int, base: float, maximum: float, *, random_value: float | None = None) -> float:
    delay = min(maximum, base * (2 ** max(0, attempt - 1)))
    return delay + (random_value if random_value is not None else random.uniform(0, min(1.0, delay * 0.1)))


class DurableJobStore:
    def __init__(self, session_factory, settings: Settings):
        self.session_factory = session_factory
        self.settings = settings

    def create(self, *, job_type: str, payload: dict[str, Any], owner_user_id: UUID | None = None,
               owner_reference: str | None = None, idempotency_key: str | None = None,
               request_id: str | None = None) -> BackgroundJob:
        now = datetime.now(timezone.utc)
        digest = payload_hash(payload)
        with self.session_factory() as db:
            if idempotency_key:
                existing = db.scalar(select(BackgroundJob).where(
                    BackgroundJob.owner_reference == owner_reference,
                    BackgroundJob.job_type == job_type,
                    BackgroundJob.idempotency_key == idempotency_key,
                ).with_for_update())
                if existing:
                    if existing.payload_hash != digest:
                        raise ValueError("idempotency key was already used for a different request")
                    return existing
            job = BackgroundJob(
                job_type=job_type, payload=payload, payload_hash=digest,
                owner_user_id=owner_user_id, owner_reference=owner_reference,
                idempotency_key=idempotency_key, max_attempts=self.settings.job_max_attempts,
                available_at=now, request_id=request_id,
            )
            db.add(job)
            try:
                db.commit()
            except Exception:
                db.rollback()
                if idempotency_key:
                    existing = db.scalar(select(BackgroundJob).where(
                        BackgroundJob.owner_reference == owner_reference,
                        BackgroundJob.job_type == job_type,
                        BackgroundJob.idempotency_key == idempotency_key,
                    ))
                    if existing and existing.payload_hash == digest:
                        return existing
                raise
            db.refresh(job)
            metrics.inc("cartel_background_jobs_total", job_type=job.job_type, outcome="claimed")
            return job

    def get(self, job_id: UUID) -> BackgroundJob | None:
        with self.session_factory() as db:
            return db.get(BackgroundJob, job_id)

    def claim(self) -> BackgroundJob | None:
        now = datetime.now(timezone.utc)
        with self.session_factory() as db:
            db.execute(update(BackgroundJob).where(
                BackgroundJob.status == "running", BackgroundJob.lease_expires_at < now,
            ).values(status="queued", available_at=now, lease_expires_at=None,
                     last_error="worker lease expired", updated_at=now))
            job = db.scalar(select(BackgroundJob).where(
                BackgroundJob.status == "queued", BackgroundJob.available_at <= now,
            ).order_by(BackgroundJob.created_at).limit(1).with_for_update(skip_locked=True))
            if not job:
                db.commit()
                return None
            job.status = "running"
            job.attempt_count += 1
            job.started_at = now
            job.lease_expires_at = now + timedelta(seconds=self.settings.job_lease_seconds)
            job.updated_at = now
            db.commit()
            db.refresh(job)
            return job

    def succeed(self, job_id: UUID, result: Any) -> None:
        now = datetime.now(timezone.utc)
        with self.session_factory() as db:
            job = db.get(BackgroundJob, job_id)
            if job and job.status == "running":
                job.status, job.result, job.completed_at = "succeeded", result, now
                job.lease_expires_at, job.updated_at = None, now
                db.commit()
                metrics.inc("cartel_background_jobs_total", job_type=job.job_type, outcome="succeeded")

    def fail(self, job_id: UUID, error: Exception, *, retryable: bool) -> None:
        now = datetime.now(timezone.utc)
        safe_error = str(error)[:512]
        with self.session_factory() as db:
            job = db.get(BackgroundJob, job_id)
            if not job or job.status != "running":
                return
            if retryable and job.attempt_count < job.max_attempts:
                delay = retry_delay(job.attempt_count, self.settings.job_retry_base_seconds, self.settings.job_retry_max_seconds)
                job.status, job.available_at = "queued", now + timedelta(seconds=delay)
            else:
                job.status, job.completed_at = "failed", now
            job.last_error, job.lease_expires_at, job.updated_at = safe_error, None, now
            db.commit()
            metrics.inc("cartel_background_jobs_total", job_type=job.job_type, outcome="retry" if job.status == "queued" else "failed")


class BackgroundWorker:
    def __init__(self, store: DurableJobStore, handlers: dict[str, JobHandler], settings: Settings):
        self.store, self.handlers, self.settings = store, handlers, settings
        self.stop_event = asyncio.Event()
        self.worker_id = f"{socket.gethostname()}:{id(self)}"

    async def run_once(self) -> bool:
        job = await asyncio.to_thread(self.store.claim)
        if not job:
            return False
        logger.info("background job claimed", extra={"job_id": str(job.id), "job_type": job.job_type, "attempt": job.attempt_count})
        try:
            handler = self.handlers[job.job_type]
            result = await handler(job.payload)
            await asyncio.to_thread(self.store.succeed, job.id, result.model_dump(mode="json") if hasattr(result, "model_dump") else result)
        except KeyError as exc:
            await asyncio.to_thread(self.store.fail, job.id, ValueError(f"unsupported job type: {job.job_type}"), retryable=False)
        except Exception as exc:
            await asyncio.to_thread(self.store.fail, job.id, exc, retryable=True)
            logger.exception("background job failed", extra={"job_id": str(job.id), "job_type": job.job_type})
        return True

    async def run_forever(self) -> None:
        while not self.stop_event.is_set():
            did_work = False
            for _ in range(self.settings.worker_concurrency):
                did_work = await self.run_once() or did_work
            if not did_work:
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=self.settings.job_poll_interval_seconds)
                except asyncio.TimeoutError:
                    pass

    def stop(self) -> None:
        self.stop_event.set()


class EmailOutboxStore:
    def __init__(self, session_factory, settings: Settings):
        self.session_factory = session_factory
        self.settings = settings

    def claim(self) -> EmailOutboxEvent | None:
        now = datetime.now(timezone.utc)
        with self.session_factory() as db:
            db.execute(update(EmailOutboxEvent).where(
                EmailOutboxEvent.status == "processing", EmailOutboxEvent.lease_expires_at < now,
            ).values(status="pending", available_at=now, lease_expires_at=None,
                     last_error="email worker lease expired", updated_at=now))
            event = db.scalar(select(EmailOutboxEvent).where(
                EmailOutboxEvent.status == "pending", EmailOutboxEvent.available_at <= now,
            ).order_by(EmailOutboxEvent.created_at).limit(1).with_for_update(skip_locked=True))
            if event is None:
                db.commit()
                return None
            event.status, event.attempt_count = "processing", event.attempt_count + 1
            event.started_at, event.lease_expires_at = now, now + timedelta(seconds=self.settings.outbox_lease_seconds)
            event.updated_at = now
            db.commit()
            db.refresh(event)
            metrics.inc("cartel_email_outbox_total", event_type=event.event_type, outcome="claimed")
            return event

    def sent(self, event_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        with self.session_factory() as db:
            event = db.get(EmailOutboxEvent, event_id)
            if event and event.status == "processing":
                event.status, event.completed_at, event.lease_expires_at, event.updated_at = "sent", now, None, now
                db.commit()
                metrics.inc("cartel_email_outbox_total", event_type=event.event_type, outcome="sent")

    def failed(self, event_id: UUID, error: Exception, *, retryable: bool) -> None:
        now = datetime.now(timezone.utc)
        with self.session_factory() as db:
            event = db.get(EmailOutboxEvent, event_id)
            if not event or event.status != "processing":
                return
            if retryable and event.attempt_count < event.max_attempts:
                event.status, event.available_at = "pending", now + timedelta(seconds=retry_delay(event.attempt_count, self.settings.outbox_retry_base_seconds, self.settings.outbox_retry_max_seconds))
            else:
                event.status, event.completed_at = "failed", now
            event.last_error, event.lease_expires_at, event.updated_at = str(error)[:512], None, now
            db.commit()
            metrics.inc("cartel_email_outbox_total", event_type=event.event_type, outcome="retry" if event.status == "pending" else "failed")


class EmailOutboxWorker:
    def __init__(self, store: EmailOutboxStore, delivery: EmailDelivery, settings: Settings):
        self.store, self.delivery, self.settings = store, delivery, settings
        self.stop_event = asyncio.Event()

    async def run_once(self) -> bool:
        event = await asyncio.to_thread(self.store.claim)
        if event is None:
            return False
        try:
            await asyncio.to_thread(self.delivery.send, event.recipient, event.subject, event.body)
            await asyncio.to_thread(self.store.sent, event.id)
        except EmailDeliveryUnavailable as exc:
            retryable = "not configured" not in str(exc) and "requires encrypted" not in str(exc)
            await asyncio.to_thread(self.store.failed, event.id, exc, retryable=retryable)
            logger.exception("email outbox delivery failed", extra={"event_type": event.event_type, "outbox_event_id": str(event.id), "attempt": event.attempt_count})
        except Exception as exc:
            await asyncio.to_thread(self.store.failed, event.id, exc, retryable=False)
            logger.exception("email outbox delivery failed permanently", extra={"event_type": event.event_type, "outbox_event_id": str(event.id), "attempt": event.attempt_count})
        return True

    async def run_forever(self) -> None:
        while not self.stop_event.is_set():
            if not await self.run_once():
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=self.settings.outbox_poll_interval_seconds)
                except asyncio.TimeoutError:
                    pass

    def stop(self) -> None:
        self.stop_event.set()
