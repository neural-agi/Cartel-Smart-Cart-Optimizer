"""Fixtures for retailer-connection HTTP API integration tests.

The fixtures here reuse the real PostgreSQL migration fixtures and the
credential-vault fixtures from the domain integration suites. No SQLite
substitute is provided: row locks, partial unique indexes, CHECK constraints,
and the vault schema are security-relevant and must run against PostgreSQL.

Redis is not required to exercise the API layer: the request limiter is a
deterministic in-process stub that implements the same allow/deny contract and
can be configured to fail closed. The production limiter is Redis-backed and is
covered separately by the rate-limit unit tests.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth.service import csrf_token_for_session
from app.core.config import Settings
from app.core.rate_limit import RateLimitBackendUnavailable, RateLimitDecision
from app.db.models import AuthSession
from app.main import create_application
from tests.integration.credential_vault.conftest import (  # noqa: F401
    key_provider,
    vault,
)
from tests.integration.retailer_connections.conftest import (  # noqa: F401
    LATER,
    NOW,
    audit_events_for,
    clock,
    db_session,
    make_connection,
    make_user,
    pg_engine,
    session_factory,
)


class RecordingRateLimiter:
    """Deterministic in-process replacement for the Redis limiter."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.counts: dict[tuple[str, str, str], int] = {}
        self.calls = 0

    async def ping(self) -> None:
        if self.fail:
            raise RateLimitBackendUnavailable("redis unavailable")

    async def close(self) -> None:
        return None

    async def allow(self, **kwargs) -> RateLimitDecision:
        self.calls += 1
        if self.fail:
            raise RateLimitBackendUnavailable("redis unavailable")
        key = (kwargs["category"], kwargs["identity"], kwargs["path"])
        self.counts[key] = self.counts.get(key, 0) + 1
        limit = kwargs["limit"]
        return RateLimitDecision(
            allowed=self.counts[key] <= limit,
            remaining=max(limit - self.counts[key], 0),
        )


@pytest.fixture
def build_client(pg_engine, tmp_path, vault):  # noqa: F811
    """Build an application/client pair sharing the migrated test database."""

    entered: list[TestClient] = []
    database_url = os.environ["CARTEL_TEST_DATABASE_URL"]

    def _build(
        *,
        limiter: RecordingRateLimiter | None = None,
        rate_limit_requests: int = 1000,
        auth_required: bool = True,
        credential_vault="default",
    ):
        limiter = limiter or RecordingRateLimiter()
        settings = Settings(
            _env_file=None,
            data_dir=tmp_path,
            database_url_override=database_url,
            public_origin="http://testserver",
            auth_cookie_secure=False,
            auth_required=auth_required,
            auth_tokens="operator=operator-secret",
            smtp_host="mail.invalid",
            smtp_from="no-reply@example.com",
            rate_limit_requests=rate_limit_requests,
            auth_rate_limit_requests=1000,
        )
        application = create_application(
            settings,
            rate_limiter=limiter,
            credential_vault=vault if credential_vault == "default" else credential_vault,
        )
        client = TestClient(application, base_url="http://testserver")
        client.__enter__()
        entered.append(client)
        return client, limiter

    try:
        yield _build
    finally:
        for client in entered:
            client.__exit__(None, None, None)


@pytest.fixture
def api_client(build_client):
    return build_client()


@pytest.fixture
def make_session(session_factory):  # noqa: F811 - fixture parameter shadows the imported fixture
    """Create a real authenticated Cartel session for a persisted user."""

    def _make_session(user) -> tuple[str, str]:
        raw_token = secrets.token_urlsafe(48)
        csrf_token = csrf_token_for_session(raw_token)
        session = AuthSession(
            user_id=user.id,
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            csrf_hash=hashlib.sha256(csrf_token.encode("utf-8")).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        with session_factory() as db:
            db.add(session)
            db.commit()
        return raw_token, csrf_token

    return _make_session
