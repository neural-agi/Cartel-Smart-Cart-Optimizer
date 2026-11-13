"""Unit coverage for vault key providers and fail-closed behaviour."""

from __future__ import annotations

import base64
import json

import pytest

from app.core.config import Settings
from app.credential_vault.key_provider import (
    KEY_BYTES,
    DevelopmentEnvironmentKeyProvider,
    StaticKeyProvider,
    UnavailableKeyProvider,
    build_key_provider,
)
from app.credential_vault.types import VaultKeyUnavailable, VaultUnavailable

KEY_ONE = bytes(range(32))
KEY_TWO = bytes(range(32, 64))


def _encoded(key: bytes) -> str:
    return base64.b64encode(key).decode("ascii")


def test_unavailable_provider_fails_closed() -> None:
    provider = UnavailableKeyProvider()
    with pytest.raises(VaultUnavailable):
        provider.current_version()
    with pytest.raises(VaultUnavailable):
        provider.key_for("dev-v1")
    with pytest.raises(VaultUnavailable):
        provider.versions()


def test_static_provider_serves_key_versions() -> None:
    provider = StaticKeyProvider(
        {"dev-v1": KEY_ONE, "dev-v2": KEY_TWO},
        active_version="dev-v2",
    )
    assert provider.current_version() == "dev-v2"
    assert provider.key_for("dev-v1") == KEY_ONE
    assert provider.key_for("dev-v2") == KEY_TWO
    assert set(provider.versions()) == {"dev-v1", "dev-v2"}


def test_static_provider_rejects_bad_keys_and_missing_active() -> None:
    with pytest.raises(VaultKeyUnavailable):
        StaticKeyProvider({}, active_version="dev-v1")
    with pytest.raises(VaultKeyUnavailable):
        StaticKeyProvider({"dev-v1": b"short"}, active_version="dev-v1")
    with pytest.raises(VaultKeyUnavailable):
        StaticKeyProvider({"dev-v1": KEY_ONE}, active_version="dev-v2")


def test_static_provider_missing_version_fails_closed() -> None:
    provider = StaticKeyProvider({"dev-v1": KEY_ONE}, active_version="dev-v1")
    with pytest.raises(VaultKeyUnavailable):
        provider.key_for("dev-v9")


def test_development_provider_reads_base64_keys() -> None:
    raw = json.dumps({"dev-v1": _encoded(KEY_ONE), "dev-v2": _encoded(KEY_TWO)})
    provider = DevelopmentEnvironmentKeyProvider(
        raw,
        active_version="dev-v1",
        app_env="development",
    )
    assert provider.current_version() == "dev-v1"
    assert provider.key_for("dev-v1") == KEY_ONE
    assert provider.key_for("dev-v2") == KEY_TWO


@pytest.mark.parametrize("app_env", ["production", "staging"])
def test_development_provider_refuses_non_development_environments(app_env: str) -> None:
    raw = json.dumps({"dev-v1": _encoded(KEY_ONE)})
    with pytest.raises(VaultKeyUnavailable):
        DevelopmentEnvironmentKeyProvider(
            raw,
            active_version="dev-v1",
            app_env=app_env,
        )


@pytest.mark.parametrize(
    ("raw", "active"),
    [
        ("", "dev-v1"),
        ("not-json", "dev-v1"),
        ("{}", "dev-v1"),
        (json.dumps({"dev-v1": "not-base64!"}), "dev-v1"),
        (json.dumps({"dev-v1": _encoded(b"short")}), "dev-v1"),
        (json.dumps({"dev-v1": _encoded(KEY_ONE)}), "dev-v2"),
        (json.dumps({"dev-v1": 123}), "dev-v1"),
    ],
)
def test_development_provider_rejects_malformed_configuration(
    raw: str, active: str
) -> None:
    with pytest.raises(VaultKeyUnavailable):
        DevelopmentEnvironmentKeyProvider(
            raw,
            active_version=active,
            app_env="development",
        )


def test_key_length_constant_is_aes_256() -> None:
    assert KEY_BYTES == 32


def test_build_key_provider_defaults_to_unavailable() -> None:
    settings = Settings(VAULT_KEY_PROVIDER="unavailable")
    assert isinstance(build_key_provider(settings), UnavailableKeyProvider)


def test_build_key_provider_builds_development_provider() -> None:
    raw = json.dumps({"dev-v1": _encoded(KEY_ONE)})
    settings = Settings(
        APP_ENV="development",
        VAULT_KEY_PROVIDER="development_env",
        VAULT_DEV_KEYS=raw,
        VAULT_ACTIVE_KEY_VERSION="dev-v1",
    )
    provider = build_key_provider(settings)
    assert isinstance(provider, DevelopmentEnvironmentKeyProvider)
    assert provider.current_version() == "dev-v1"


def test_build_key_provider_fails_closed_in_production() -> None:
    raw = json.dumps({"dev-v1": _encoded(KEY_ONE)})
    settings = Settings(
        APP_ENV="production",
        APP_DEBUG=False,
        DOCS_ENABLED=False,
        AUTH_REQUIRED=True,
        AUTH_TOKENS="user=token",
        PUBLIC_ORIGIN="https://cartel.example",
        VAULT_KEY_PROVIDER="development_env",
        VAULT_DEV_KEYS=raw,
        VAULT_ACTIVE_KEY_VERSION="dev-v1",
    )
    with pytest.raises(VaultKeyUnavailable):
        build_key_provider(settings)
