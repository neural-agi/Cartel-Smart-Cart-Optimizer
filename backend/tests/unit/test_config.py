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
        "redis_url": "redis://localhost:6379/0",
    }
    values.update(overrides)
    return Settings(**values)


def test_valid_configuration_loads() -> None:
    settings = _settings()

    assert settings.app_name == "Cartel"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.checkout_observation_provider_mode == "unavailable"
    assert settings.retailer_data_provider_mode == "unavailable"


def test_cors_origins_are_explicitly_parsed() -> None:
    settings = _settings(cors_allowed_origins="https://app.example, https://admin.example/")

    assert settings.cors_origins == ("https://app.example", "https://admin.example")


@pytest.mark.parametrize("mode", ["registry", "unavailable"])
def test_checkout_observation_provider_mode_is_explicit(mode: str) -> None:
    settings = _settings(checkout_observation_provider_mode=mode)
    assert settings.checkout_observation_provider_mode == mode


@pytest.mark.parametrize("mode", ["blinkit", "unavailable"])
def test_retailer_data_provider_mode_is_explicit(mode: str) -> None:
    settings = _settings(retailer_data_provider_mode=mode)
    assert settings.retailer_data_provider_mode == mode


def test_quickcommerce_mode_requires_https_endpoint_and_secret() -> None:
    with pytest.raises(ValidationError):
        _settings(retailer_data_provider_mode="quickcommerce")
    settings = _settings(
        retailer_data_provider_mode="quickcommerce",
        quickcommerce_api_base_url="https://provider.example",
        quickcommerce_api_key="redacted-test-secret",
    )
    assert settings.quickcommerce_api_base_url == "https://provider.example"
    assert "redacted-test-secret" not in repr(settings)


@pytest.mark.parametrize(
    "overrides",
    [
        {"app_name": ""},
        {"redis_url": "http://localhost:6379"},
        {"postgres_port": 70000},
        {"app_debug": "not-a-boolean"},
        {"app_env": "invalid"},
        {"checkout_observation_provider_mode": "unsupported"},
        {"retailer_data_provider_mode": "unsupported"},
        {"planning_max_combinations": 0},
    ],
)
def test_invalid_configuration_fails_closed(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _settings(**overrides)


def test_production_filesystem_runtime_does_not_require_unused_database_secret() -> None:
    settings = _settings(
        app_env="production",
        app_debug=False,
        docs_enabled=False,
        auth_required=True,
        auth_tokens="release-user=release-token",
        public_origin="https://cartel.example",
    )
    assert settings.is_production is True


def test_production_rejects_disabled_bearer_authentication() -> None:
    with pytest.raises(ValidationError, match="AUTH_REQUIRED must be true"):
        _settings(app_env="production", app_debug=False, docs_enabled=False)


def test_startup_diagnostics_exclude_secret_values(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(postgres_password="super-secret-password")
    application = create_application(settings)
    messages: list[str] = []
    import app.main as main_module

    original_info = main_module.logger.info

    def capture_info(message: str, *args, **kwargs) -> None:
        messages.append(message % args if args else message)
        original_info(message, *args, **kwargs)

    monkeypatch.setattr(main_module.logger, "info", capture_info)

    from fastapi.testclient import TestClient

    with TestClient(application):
        pass

    joined = "\n".join(messages)
    assert any("Runtime configuration" in message for message in messages)
    assert "localhost" in joined
    assert "super-secret-password" not in joined


def test_database_url_escapes_credentials_and_keeps_them_secret() -> None:
    settings = _settings(postgres_user="cartel@service", postgres_password="p@ss:/word")

    assert "cartel%40service:p%40ss%3A%2Fword@" in settings.database_url
    assert "p@ss:/word" not in repr(settings)
    assert "super-secret-password" not in repr(_settings(postgres_password="super-secret-password"))


def test_operator_token_is_redacted_from_settings_repr() -> None:
    settings = _settings(auth_required=True, auth_tokens="operator=do-not-print")
    assert "do-not-print" not in repr(settings)


def test_production_requires_postgres_secret_when_database_is_required() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL credentials are required"):
        _settings(
            app_env="production",
            app_debug=False,
            docs_enabled=False,
            auth_required=True,
            auth_tokens="operator=secret",
            database_required=True,
            public_origin="https://cartel.example",
        )
