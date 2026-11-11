"""Key-provider abstraction for the credential vault.

Production-grade key management (KMS/HSM or an external secrets service) is not
available in this repository or deployment configuration. The only implemented
provider is explicitly development-only and reads base64 keys from an
environment variable. It must never be represented as production key
management.

The default provider is ``unavailable`` and fails closed. This is deliberate:
missing, malformed, or inaccessible keys must never produce plaintext.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Protocol, runtime_checkable

from app.core.config import Settings
from app.credential_vault.types import VaultKeyUnavailable, VaultUnavailable

KEY_BYTES = 32


@runtime_checkable
class KeyProvider(Protocol):
    """Minimal key-management surface required by the vault."""

    def current_version(self) -> str:
        """Return the key version used for new encryptions."""

    def key_for(self, version: str) -> bytes:
        """Return the 32-byte AES-256 key for ``version`` or fail closed."""

    def versions(self) -> tuple[str, ...]:
        """Return the key versions this provider can currently serve."""


class UnavailableKeyProvider:
    """Fail-closed default used when no key provider is configured."""

    def current_version(self) -> str:
        raise VaultUnavailable("credential vault key provider is not configured")

    def key_for(self, version: str) -> bytes:
        raise VaultUnavailable("credential vault key provider is not configured")

    def versions(self) -> tuple[str, ...]:
        raise VaultUnavailable("credential vault key provider is not configured")


class StaticKeyProvider:
    """Test-only provider with keys held in memory.

    Never use this provider in production. It exists so unit tests can exercise
    key-version compatibility and fail-closed behaviour deterministically.
    """

    def __init__(self, keys: dict[str, bytes], *, active_version: str) -> None:
        if not keys:
            raise VaultKeyUnavailable("static key provider requires at least one key")
        for version, key in keys.items():
            if not isinstance(key, bytes) or len(key) != KEY_BYTES:
                raise VaultKeyUnavailable(f"key {version!r} must be {KEY_BYTES} bytes")
        if active_version not in keys:
            raise VaultKeyUnavailable("active key version is not available")
        self._keys = dict(keys)
        self._active = active_version

    def current_version(self) -> str:
        return self._active

    def key_for(self, version: str) -> bytes:
        try:
            return self._keys[version]
        except KeyError as exc:
            raise VaultKeyUnavailable(f"key version {version!r} is unavailable") from exc

    def versions(self) -> tuple[str, ...]:
        return tuple(self._keys)


class DevelopmentEnvironmentKeyProvider:
    """Development-only key provider backed by an environment variable.

    ``VAULT_DEV_KEYS`` is a JSON object mapping key version to a base64-encoded
    32-byte key, for example ``{"dev-v1": "<base64>"}``. Keys live outside
    ordinary application tables and are never committed. The provider refuses
    to construct itself in production.
    """

    def __init__(self, raw_keys: str, *, active_version: str, app_env: str) -> None:
        if app_env != "development":
            raise VaultKeyUnavailable(
                "development key provider is permitted only when APP_ENV=development"
            )
        if not raw_keys.strip():
            raise VaultKeyUnavailable("VAULT_DEV_KEYS is not configured")
        if not active_version.strip():
            raise VaultKeyUnavailable("VAULT_ACTIVE_KEY_VERSION is not configured")
        try:
            decoded = json.loads(raw_keys)
        except json.JSONDecodeError as exc:
            raise VaultKeyUnavailable("VAULT_DEV_KEYS is not valid JSON") from exc
        if not isinstance(decoded, dict) or not decoded:
            raise VaultKeyUnavailable("VAULT_DEV_KEYS must be a non-empty JSON object")

        keys: dict[str, bytes] = {}
        for version, encoded in decoded.items():
            if not isinstance(version, str) or not version:
                raise VaultKeyUnavailable("VAULT_DEV_KEYS contains an invalid version")
            if not isinstance(encoded, str):
                raise VaultKeyUnavailable("VAULT_DEV_KEYS values must be base64 strings")
            try:
                key = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise VaultKeyUnavailable(
                    f"VAULT_DEV_KEYS value for {version!r} is not valid base64"
                ) from exc
            if len(key) != KEY_BYTES:
                raise VaultKeyUnavailable(
                    f"VAULT_DEV_KEYS value for {version!r} must be {KEY_BYTES} bytes"
                )
            keys[version] = key

        if active_version not in keys:
            raise VaultKeyUnavailable("VAULT_ACTIVE_KEY_VERSION is not present in keys")
        self._keys = keys
        self._active = active_version

    def current_version(self) -> str:
        return self._active

    def key_for(self, version: str) -> bytes:
        try:
            return self._keys[version]
        except KeyError as exc:
            raise VaultKeyUnavailable(f"key version {version!r} is unavailable") from exc

    def versions(self) -> tuple[str, ...]:
        return tuple(self._keys)


def build_key_provider(settings: Settings) -> KeyProvider:
    """Build the configured provider, defaulting to fail-closed."""

    if settings.vault_key_provider == "development_env":
        return DevelopmentEnvironmentKeyProvider(
            settings.vault_dev_keys.get_secret_value(),
            active_version=settings.vault_active_key_version,
            app_env=settings.app_env,
        )
    return UnavailableKeyProvider()
