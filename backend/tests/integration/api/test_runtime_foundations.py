from fastapi import Request
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_application


def _application(tmp_path):
    return create_application(Settings(_env_file=None, data_dir=tmp_path))


def test_request_id_is_propagated_only_for_safe_values(tmp_path) -> None:
    with TestClient(_application(tmp_path)) as client:
        accepted = client.get("/health", headers={"X-Request-ID": "trace-123"})
        replaced = client.get("/health", headers={"X-Request-ID": "bad value\nwith-newline"})

    assert accepted.headers["X-Request-ID"] == "trace-123"
    assert replaced.headers["X-Request-ID"] != "bad value\nwith-newline"
    assert len(replaced.headers["X-Request-ID"]) == 36


def test_unexpected_errors_are_safe_and_correlated(tmp_path) -> None:
    application = _application(tmp_path)

    @application.get("/_runtime-test/error")
    async def error_route(request: Request):
        raise RuntimeError("private database detail must not reach the client")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/_runtime-test/error", headers={"X-Request-ID": "runtime-test"})

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "runtime-test"
    body = response.json()
    assert body["detail"]["code"] == "internal_error"
    assert body["detail"]["request_id"] == "runtime-test"
    assert "private database detail" not in response.text
    assert "Traceback" not in response.text


def test_liveness_does_not_require_database_and_readiness_reports_optional_checkout(tmp_path) -> None:
    with TestClient(_application(tmp_path)) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["checks"]["checkout_capture"] == "unavailable"


def test_database_pool_configuration_is_explicit(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        db_pool_size=3,
        db_max_overflow=4,
        db_pool_timeout_seconds=12,
        db_pool_recycle_seconds=600,
    )

    assert settings.db_pool_size == 3
    assert settings.db_max_overflow == 4
    assert settings.db_pool_timeout_seconds == 12
    assert settings.db_pool_recycle_seconds == 600
