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


def test_auth_session_returns_identity_for_configured_bearer_token(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path, auth_required=True, auth_tokens="user-1=secret-token")
    with TestClient(create_application(settings)) as client:
        response = client.get(
            "/api/v1/auth/session",
            headers={"Authorization": "Bearer secret-token"},
        )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "user_id": "user-1"}
    assert "secret-token" not in response.text


def test_auth_session_rejects_missing_or_invalid_bearer_token(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path, auth_required=True, auth_tokens="user-1=secret-token")
    with TestClient(create_application(settings)) as client:
        missing = client.get("/api/v1/auth/session")
        invalid = client.get(
            "/api/v1/auth/session",
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"
    assert invalid.json()["error"]["code"] == "authentication_required"


def test_auth_session_does_not_claim_authentication_when_disabled(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path, auth_required=False)
    with TestClient(create_application(settings)) as client:
        response = client.get("/api/v1/auth/session")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "user_id": None}


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


def test_consumer_signup_fails_honestly_when_email_delivery_is_unconfigured(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path, public_origin="http://testserver")
    with TestClient(create_application(settings), base_url="http://testserver") as client:
        response = client.post(
            "/api/v2/auth/signup",
            headers={"Origin": "http://testserver"},
            json={"email": "person@example.com", "password": "correct-horse-battery-staple"},
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "email_delivery_unavailable"
    assert not response.headers.get("set-cookie")


def test_request_validation_does_not_echo_plaintext_password(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path, public_origin="http://testserver")
    password = "not-long"
    with TestClient(create_application(settings), base_url="http://testserver") as client:
        response = client.post(
            "/api/v2/auth/signup",
            headers={"Origin": "http://testserver"},
            json={"email": "person@example.com", "password": password},
        )
    assert response.status_code == 422
    assert password not in response.text
