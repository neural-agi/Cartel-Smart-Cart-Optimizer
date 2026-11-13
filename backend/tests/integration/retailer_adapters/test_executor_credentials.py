"""Integration coverage for adapter secret boundaries and fail-closed vault use."""

from __future__ import annotations

import logging

import pytest

from app.credential_vault.key_provider import UnavailableKeyProvider
from app.credential_vault.service import CredentialVault
from app.credential_vault.types import SecretOwner, SecretType
from app.retailer_adapters.contracts import (
    AdapterCapability,
    AdapterOutcome,
    ProductSearchRequest,
    ProductSearchResult,
)
from app.retailer_adapters.enforcement import RetailerAdapterExecutor
from app.retailer_adapters.registry import RetailerAdapterRegistry
from app.retailer_connections.lifecycle import RetailerConnectionStatus
from tests.unit.retailer_adapters.support import (
    FakeAdapter,
    acquisition,
    search_location,
)

PLAINTEXT = b"opaque-refresh-token-material"


def owner_for(connection) -> SecretOwner:
    return SecretOwner(
        user_id=connection.user_id,
        connection_id=connection.id,
        retailer_id=connection.retailer_id,
    )


def executor_for(adapter: FakeAdapter, *, vault=None) -> RetailerAdapterExecutor:
    registry = RetailerAdapterRegistry()
    registry.register(adapter)
    return RetailerAdapterExecutor(registry=registry, vault=vault)


def request() -> ProductSearchRequest:
    return ProductSearchRequest(query="milk", location=search_location())


def adapter_reading_secret() -> tuple[FakeAdapter, dict[str, bytes]]:
    seen: dict[str, bytes] = {}
    adapter = FakeAdapter(
        supported=(AdapterCapability.PRODUCT_DISCOVERY,),
        secret_types=(SecretType.OAUTH_REFRESH_TOKEN,),
    )

    async def behavior() -> ProductSearchResult:
        seen["token"] = adapter.calls[-1][1].reveal(
            SecretType.OAUTH_REFRESH_TOKEN
        )
        return ProductSearchResult(
            outcome=AdapterOutcome.SUCCESS,
            acquisition=acquisition(AdapterCapability.PRODUCT_DISCOVERY),
        )

    adapter.behaviors[AdapterCapability.PRODUCT_DISCOVERY] = behavior
    return adapter, seen


@pytest.mark.asyncio
async def test_executor_resolves_declared_secret_through_vault(
    db_session, make_user, make_connection, vault
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    vault.store(
        db_session,
        owner=owner_for(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    adapter, seen = adapter_reading_secret()

    result = await executor_for(adapter, vault=vault).execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request(),
    )

    assert result.outcome is AdapterOutcome.SUCCESS
    assert seen["token"] == PLAINTEXT
    assert PLAINTEXT.decode() not in repr(result)
    assert adapter.calls[0][1].reveal(SecretType.OAUTH_REFRESH_TOKEN) == PLAINTEXT


@pytest.mark.asyncio
async def test_secret_never_appears_in_structured_logs(
    db_session, make_user, make_connection, vault
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    vault.store(
        db_session,
        owner=owner_for(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    adapter, seen = adapter_reading_secret()

    captured: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    logger = logging.getLogger("app.retailer_adapters.enforcement")
    handler = _Capture()
    previous_level = logger.level
    previous_disabled = logger.disabled
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # The migration fixture runs Alembic's fileConfig, which disables existing
    # loggers. Re-enable this logger for the duration of the assertion.
    logger.disabled = False
    try:
        result = await executor_for(adapter, vault=vault).execute(
            db_session,
            user_id=user.id,
            connection_id=connection.id,
            capability=AdapterCapability.PRODUCT_DISCOVERY,
            request=request(),
            request_id="request-1",
        )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.disabled = previous_disabled

    assert result.outcome is AdapterOutcome.SUCCESS
    assert seen["token"] == PLAINTEXT
    assert len(captured) == 1
    rendered = "\n".join(record.getMessage() for record in captured)
    extra_values = "\n".join(
        str(value) for record in captured for value in record.__dict__.values()
    )
    assert "retailer_adapter_operation" in rendered
    assert PLAINTEXT.decode() not in rendered
    assert PLAINTEXT.decode() not in extra_values


@pytest.mark.asyncio
async def test_missing_declared_secret_requires_user_action(
    db_session, make_user, make_connection, vault
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    adapter, seen = adapter_reading_secret()

    result = await executor_for(adapter, vault=vault).execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request(),
    )

    assert result.outcome is AdapterOutcome.REQUIRES_USER_ACTION
    assert result.reason_code == "missing_credential"
    assert seen == {}
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_secret_on_another_connection_is_not_visible(
    db_session, make_user, make_connection, vault
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    other = make_connection(
        user_id=user.id,
        status=RetailerConnectionStatus.CONNECTED,
        retailer_id="ZEPTO",
    )
    vault.store(
        db_session,
        owner=owner_for(other),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    adapter, seen = adapter_reading_secret()

    result = await executor_for(adapter, vault=vault).execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request(),
    )

    assert result.outcome is AdapterOutcome.REQUIRES_USER_ACTION
    assert result.reason_code == "missing_credential"
    assert seen == {}


@pytest.mark.asyncio
async def test_revoked_secret_is_not_resolved(
    db_session, make_user, make_connection, vault
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    owner = owner_for(connection)
    metadata = vault.store(
        db_session,
        owner=owner,
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    vault.revoke(db_session, owner=owner, reference=metadata.reference)
    adapter, seen = adapter_reading_secret()

    result = await executor_for(adapter, vault=vault).execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request(),
    )

    assert result.outcome is AdapterOutcome.REQUIRES_USER_ACTION
    assert result.reason_code == "missing_credential"
    assert seen == {}


@pytest.mark.asyncio
async def test_unavailable_key_provider_fails_closed(
    db_session, make_user, make_connection, vault
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    vault.store(
        db_session,
        owner=owner_for(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    adapter, seen = adapter_reading_secret()
    fail_closed = CredentialVault(key_provider=UnavailableKeyProvider())

    result = await executor_for(adapter, vault=fail_closed).execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request(),
    )

    assert result.outcome is AdapterOutcome.TEMPORARY_FAILURE
    assert result.reason_code == "credential_vault_unavailable"
    assert seen == {}
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_lifecycle_denial_prevents_secret_resolution(
    db_session, make_user, make_connection, vault
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.DEGRADED
    )
    vault.store(
        db_session,
        owner=owner_for(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    adapter, seen = adapter_reading_secret()

    result = await executor_for(adapter, vault=vault).execute(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        capability=AdapterCapability.PRODUCT_DISCOVERY,
        request=request(),
    )

    assert result.outcome is AdapterOutcome.ACCESS_DENIED
    assert result.reason_code == "connection_degraded"
    assert seen == {}
    assert adapter.calls == []
