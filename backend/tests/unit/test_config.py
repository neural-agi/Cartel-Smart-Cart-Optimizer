import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_application


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "app_name": "Cartel",
        "app_env": "development",
        "app_debug": True,
        "app_version": "0.1.0",
        "api_v1_prefix": "/api/v1",
        "log_level": "INFO",
        "log_json": True,
        "docs_enabled": True,
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "postgres_db": "cartel",
        "postgres_user": "cartel",
        "postgres_password": "cartel",
        "redis_url": "redis://localhost:6379/0",
    }
    values.update(overrides)
    return Settings(**values)


def test_valid_configuration_loads() -> None:
    settings = _settings()

    assert settings.app_name == "Cartel"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.checkout_observation_provider_mode == "unavailable"


@pytest.mark.parametrize("mode", ["registry", "unavailable"])
def test_checkout_observation_provider_mode_is_explicit(mode: str) -> None:
    settings = _settings(checkout_observation_provider_mode=mode)
    assert settings.checkout_observation_provider_mode == mode


@pytest.mark.parametrize(
    "overrides",
    [
        {"app_name": ""},
        {"redis_url": "http://localhost:6379"},
        {"postgres_port": 70000},
        {"app_debug": "not-a-boolean"},
        {"app_env": "invalid"},
        {"checkout_observation_provider_mode": "unsupported"},
    ],
)
def test_invalid_configuration_fails_closed(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _settings(**overrides)


def test_production_requires_explicit_safe_configuration() -> None:
    with pytest.raises(ValidationError):
        _settings(app_env="production", app_debug=False, docs_enabled=False)

    settings = _settings(
        app_env="production",
        app_debug=False,
        docs_enabled=False,
        postgres_password="configured-secret",
    )
    assert settings.is_production is True


def test_startup_diagnostics_exclude_secret_values(capsys: pytest.CaptureFixture[str]) -> None:
    settings = _settings(postgres_password="super-secret-password")
    application = create_application(settings)

    from fastapi.testclient import TestClient

    with TestClient(application):
        pass

    messages = capsys.readouterr().err
    assert "Runtime configuration" in messages
    assert "localhost" in messages
    assert "super-secret-password" not in messages
