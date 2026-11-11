"""PostgreSQL fixtures for credential-vault integration tests.

The vault is exercised against the real migrated schema because the composite
foreign key, partial unique index, and row locks are security-relevant and
cannot be represented faithfully in SQLite.
"""

from __future__ import annotations

import pytest

from app.credential_vault.key_provider import StaticKeyProvider
from app.credential_vault.service import CredentialVault
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

VAULT_KEY = bytes(range(32))
VAULT_KEY_V2 = bytes(range(32, 64))


@pytest.fixture
def key_provider() -> StaticKeyProvider:
    return StaticKeyProvider(
        {"test-v1": VAULT_KEY, "test-v2": VAULT_KEY_V2},
        active_version="test-v1",
    )


@pytest.fixture
def vault(key_provider, clock) -> CredentialVault:  # noqa: F811
    return CredentialVault(key_provider=key_provider, clock=clock)
