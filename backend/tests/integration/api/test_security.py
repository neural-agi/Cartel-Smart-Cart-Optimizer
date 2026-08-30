from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_application


def test_protected_api_rejects_missing_bearer_token(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path, auth_required=True, auth_tokens="user-1=secret-token")
    with TestClient(create_application(settings)) as client:
        response = client.get("/api/v1/products/search", params={"query": "milk"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.headers["x-request-id"]


def test_authenticated_request_exposes_no_token_in_response(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path, auth_required=True, auth_tokens="user-1=secret-token")
    with TestClient(create_application(settings)) as client:
        response = client.get(
            "/api/v1/products/search",
            params={"query": "milk"},
            headers={"Authorization": "Bearer secret-token"},
        )

    assert response.status_code == 200
    assert "secret-token" not in response.text


def test_rate_limit_returns_structured_error(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path, rate_limit_requests=1, rate_limit_window_seconds=60)
    with TestClient(create_application(settings)) as client:
        first = client.get("/api/v1/products/search", params={"query": "milk"})
        second = client.get("/api/v1/products/search", params={"query": "bread"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"


def test_cors_preflight_allows_configured_origin(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path, cors_allowed_origins="https://app.example")
    with TestClient(create_application(settings)) as client:
        response = client.options(
            "/api/v1/products/search",
            headers={
                "Origin": "https://app.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.example"
