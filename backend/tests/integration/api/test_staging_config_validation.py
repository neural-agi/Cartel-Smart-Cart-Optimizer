"""Executable staging-configuration validation (Architecture A, dummy values).

Every assertion here is structural or runtime-local. It is **not** proof of
provider connectivity: no Render, Neon, Upstash, Vercel, or GitHub account is
contacted. The values are dummies chosen to match the Architecture A shape.

Run against a disposable PostgreSQL database and a disposable Redis:

    CARTEL_TEST_DATABASE_URL=postgresql+psycopg://.../cartel_k4_it \
    REDIS_URL=redis://127.0.0.1:56379/0 \
    python3 -m pytest tests/integration/api/test_staging_config_validation.py -q -rs
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings, get_settings
from app.main import create_application

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = Path(__file__).resolve().parents[3]
PASSWORD = "correct-horse-battery-staple-1"
PUBLIC_ORIGIN = "https://cartel.example"


def _database_url() -> str:
    value = os.environ.get("CARTEL_TEST_DATABASE_URL", "")
    if not value:
        pytest.skip(
            "set CARTEL_TEST_DATABASE_URL to a disposable PostgreSQL database; "
            "SQLite is not supported"
        )
    if value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
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
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
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


class RecordingEmailDelivery:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.messages: list[tuple[str, str, str]] = []

    def send(self, recipient: str, subject: str, body: str) -> None:
        self.messages.append((recipient, subject, body))

    def refresh(self, recipient: str) -> None:
        with self.engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT recipient FROM email_outbox_events "
                    "WHERE lower(recipient) = lower(:recipient)"
                ),
                {"recipient": recipient},
            )

    def token_for(self, recipient: str) -> str:
        with self.engine.connect() as connection:
            body = connection.execute(
                text(
                    "SELECT body FROM email_outbox_events "
                    "WHERE lower(recipient) = lower(:recipient) "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"recipient": recipient},
            ).scalar_one()
        match = re.search(r"#token=([A-Za-z0-9_-]+)", body)
        assert match
        return match.group(1)


def _staging_settings(url: str, tmp_path: Path, **overrides) -> Settings:
    values = dict(
        _env_file=None,
        app_env="staging",
        app_debug=False,
        docs_enabled=False,
        data_dir=tmp_path,
        database_url_override=url,
        database_required=True,
        redis_url=os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
        auth_required=True,
        auth_tokens="operator=dummy-operator-token",
        auth_cookie_secure=True,
        public_origin=PUBLIC_ORIGIN,
        cors_allowed_origins=PUBLIC_ORIGIN,
        github_client_id="dummy-github-client-id",
        github_client_secret="dummy-github-client-secret",
        github_redirect_uri=f"{PUBLIC_ORIGIN}/api/v2/auth/github/callback",
        email_delivery_mode="file",
        local_email_dir=tmp_path / "email",
        demo_fixtures_enabled=False,
        retailer_data_provider_mode="unavailable",
        checkout_observation_provider_mode="unavailable",
        checkout_capture_adapter_mode="unavailable",
        vault_key_provider="unavailable",
        auth_rate_limit_requests=1000,
        rate_limit_requests=100000,
    )
    values.update(overrides)
    return Settings(**values)


def _origin() -> dict[str, str]:
    return {"Origin": PUBLIC_ORIGIN}


def test_architecture_a_staging_configuration_is_structurally_valid(
    pg_database, tmp_path, monkeypatch
) -> None:
    for name in (
        "DEMO_FIXTURES_ENABLED",
        "RETAILER_DATA_PROVIDER_MODE",
        "CHECKOUT_OBSERVATION_PROVIDER_MODE",
        "CHECKOUT_CAPTURE_ADAPTER_MODE",
        "VAULT_KEY_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = _staging_settings(os.environ["CARTEL_TEST_DATABASE_URL"], tmp_path)

    assert settings.app_env == "staging"
    assert settings.auth_required is True
    assert settings.auth_tokens.get_secret_value() == "operator=dummy-operator-token"

    # GitHub OAuth settings are structurally valid (dummy values only).
    assert settings.github_oauth_configured is True
    assert settings.github_redirect_uri == (
        "https://cartel.example/api/v2/auth/github/callback"
    )

    # Database is required and points at the disposable PostgreSQL URL.
    assert settings.database_required is True
    assert settings.database_url.startswith("postgresql+psycopg://")

    # Redis URL is structurally valid. Staging does not ping at startup, but the
    # request-time limiter fails closed (proven in the runtime test below).
    assert settings.redis_url.startswith("redis://")

    # Secure cookie under the HTTPS assumption.
    assert settings.secure_auth_cookie is True

    # CORS is exact, never a wildcard.
    assert settings.cors_origins == ("https://cartel.example",)
    assert "*" not in settings.cors_origins

    # Demo catalog is off by default and only an explicit gate enables it.
    assert Settings(_env_file=None).demo_fixtures_enabled is False
    assert _staging_settings(
        os.environ["CARTEL_TEST_DATABASE_URL"], tmp_path, demo_fixtures_enabled=True
    ).demo_fixtures_enabled is True

    # Live retailer acquisition and checkout capture are unavailable.
    defaults = Settings(_env_file=None)
    assert defaults.retailer_data_provider_mode == "unavailable"
    assert defaults.checkout_observation_provider_mode == "unavailable"
    assert defaults.checkout_capture_adapter_mode == "unavailable"
    assert defaults.vault_key_provider == "unavailable"

    # File email delivery works without SMTP; no worker is required for core demo.
    assert settings.email_delivery_mode == "file"
    assert settings.email_delivery_configured is True
    assert settings.smtp_host == ""


def test_database_required_startup_fails_without_a_database(tmp_path) -> None:
    settings = _staging_settings(
        "postgresql+psycopg://cartel:dummy@127.0.0.1:1/cartel_k4_missing",
        tmp_path,
    )
    with pytest.raises(SQLAlchemyError):
        with TestClient(create_application(settings), base_url="https://testserver"):
            pass


def test_secure_cookie_flags_from_a_real_response(pg_database, tmp_path) -> None:
    mail = RecordingEmailDelivery(pg_database)
    settings = _staging_settings(os.environ["CARTEL_TEST_DATABASE_URL"], tmp_path)
    email = "staging-cookie@example.com"
    with TestClient(
        create_application(settings, email_delivery=mail), base_url="https://testserver"
    ) as client:
        signup = client.post(
            "/api/v2/auth/signup",
            json={"email": email, "password": PASSWORD},
            headers=_origin(),
        )
        assert signup.status_code == 202, signup.text
        verified = client.post(
            "/api/v2/auth/email/verify",
            json={"token": mail.token_for(email)},
            headers=_origin(),
        )
        assert verified.status_code == 200, verified.text
        cookie = verified.headers["set-cookie"].lower()
        assert "httponly" in cookie
        assert "secure" in cookie
        assert "samesite=lax" in cookie
        assert "path=/" in cookie


def test_cors_allows_only_the_exact_origin(pg_database, tmp_path) -> None:
    mail = RecordingEmailDelivery(pg_database)
    settings = _staging_settings(os.environ["CARTEL_TEST_DATABASE_URL"], tmp_path)
    with TestClient(
        create_application(settings, email_delivery=mail), base_url="https://testserver"
    ) as client:
        allowed = client.options(
            "/api/v2/auth/login",
            headers={
                "Origin": PUBLIC_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )
        assert allowed.headers["access-control-allow-origin"] == PUBLIC_ORIGIN
        assert "access-control-allow-credentials" not in allowed.headers

        rejected = client.options(
            "/api/v2/auth/login",
            headers={
                "Origin": "https://evil.invalid",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-origin" not in rejected.headers


def test_staging_redis_failure_fails_closed(pg_database, tmp_path) -> None:
    mail = RecordingEmailDelivery(pg_database)
    settings = _staging_settings(
        os.environ["CARTEL_TEST_DATABASE_URL"],
        tmp_path,
        redis_url="redis://127.0.0.1:1/0",
        redis_connect_timeout_seconds=0.2,
        redis_operation_timeout_seconds=0.2,
    )
    with TestClient(
        create_application(settings, email_delivery=mail), base_url="https://testserver"
    ) as client:
        response = client.post(
            "/api/v2/auth/login",
            json={"email": "nobody@example.com", "password": PASSWORD},
            headers=_origin(),
        )
        assert response.status_code == 503, response.text
        assert response.json()["error"]["code"] == "rate_limit_unavailable"


def test_frontend_rewrite_targets_the_configured_backend() -> None:
    source = (REPO_ROOT / "frontend" / "next.config.ts").read_text(encoding="utf-8")
    assert "process.env.BACKEND_INTERNAL_URL" in source
    assert "source: \"/api/:path*\"" in source
    assert "`${backendInternalUrl ?? \"http://api:8000\"}/api/:path*`" in source
