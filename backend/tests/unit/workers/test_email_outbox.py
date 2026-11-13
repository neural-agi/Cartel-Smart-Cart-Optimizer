from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.auth.email_delivery import EmailDeliveryUnavailable
from app.workers.background_jobs import EmailOutboxWorker


class Settings:
    outbox_poll_interval_seconds = 0.01


class Store:
    def __init__(self, event):
        self.event = event
        self.sent_ids = []
        self.failures = []

    def claim(self):
        event, self.event = self.event, None
        return event

    def sent(self, event_id):
        self.sent_ids.append(event_id)

    def failed(self, event_id, error, *, retryable):
        self.failures.append((event_id, retryable))


class Delivery:
    def __init__(self, error=None):
        self.error = error

    def send(self, *_args):
        if self.error:
            raise self.error


@pytest.mark.asyncio
async def test_email_outbox_marks_success_after_delivery():
    event_id = uuid4()
    store = Store(SimpleNamespace(id=event_id, recipient="a@example.com", subject="s", body="b", event_type="verification", attempt_count=1))
    worker = EmailOutboxWorker(store, Delivery(), Settings())
    assert await worker.run_once() is True
    assert store.sent_ids == [event_id]


@pytest.mark.asyncio
async def test_email_outbox_retries_transport_failures():
    event_id = uuid4()
    store = Store(SimpleNamespace(id=event_id, recipient="a@example.com", subject="s", body="b", event_type="verification", attempt_count=1))
    worker = EmailOutboxWorker(store, Delivery(EmailDeliveryUnavailable("email delivery failed")), Settings())
    await worker.run_once()
    assert store.failures == [(event_id, True)]


@pytest.mark.asyncio
async def test_email_outbox_does_not_retry_configuration_failure():
    event_id = uuid4()
    store = Store(SimpleNamespace(id=event_id, recipient="a@example.com", subject="s", body="b", event_type="verification", attempt_count=1))
    worker = EmailOutboxWorker(store, Delivery(EmailDeliveryUnavailable("email delivery is not configured")), Settings())
    await worker.run_once()
    assert store.failures == [(event_id, False)]
