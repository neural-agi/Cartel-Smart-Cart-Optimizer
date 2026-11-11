"""PostgreSQL integration coverage for the credential vault."""

from __future__ import annotations

import dataclasses
import threading
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.credential_vault.key_provider import (
    StaticKeyProvider,
    UnavailableKeyProvider,
)
from app.credential_vault.service import CredentialVault
from app.credential_vault.types import (
    AUDIT_PAYLOAD_FIELDS,
    InvalidSecretInput,
    SecretAccessDenied,
    SecretDeletionDenied,
    SecretMetadata,
    SecretNotFound,
    SecretOwner,
    SecretStateConflict,
    SecretStatus,
    SecretType,
    SecretVersionConflict,
    UnsupportedSecretType,
    VaultKeyUnavailable,
    VaultUnavailable,
)
from app.db.models import AuditEvent
from app.db.models.credential_secrets import CredentialSecret
from app.retailer_connections import service
from app.retailer_connections.lifecycle import (
    RetailerConnectionReason,
    RetailerConnectionStatus,
    RetailerOperation,
)
from tests.integration.credential_vault.conftest import NOW
from tests.unit.timestamp_support import FrozenClock

PLAINTEXT = b"opaque-refresh-token-material"


def _owner(connection) -> SecretOwner:
    return SecretOwner(
        user_id=connection.user_id,
        connection_id=connection.id,
        retailer_id=connection.retailer_id,
    )


def _vault_audit_events(session, reference) -> list[AuditEvent]:
    return list(
        session.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.object_type == "credential_secret",
                AuditEvent.object_id == str(reference),
            )
            .order_by(AuditEvent.created_at, AuditEvent.id)
        ).all()
    )


def _connected_connection(make_user, make_connection):
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    return user, connection


def test_store_and_retrieve_round_trip_without_auditing_retrieval(
    db_session, make_user, make_connection, vault
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )

    assert metadata.version == 1
    assert metadata.status is SecretStatus.ACTIVE
    assert metadata.algorithm == "AES_256_GCM"
    assert metadata.key_version == "test-v1"

    assert (
        vault.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
        )
        == PLAINTEXT
    )

    events = _vault_audit_events(db_session, metadata.reference)
    assert [event.event_type for event in events] == ["credential_secret_created"]
    assert set(events[0].payload or {}) == AUDIT_PAYLOAD_FIELDS


def test_repeated_store_uses_fresh_ciphertext_and_nonce(
    db_session, make_user, make_connection, vault
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    first = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_ACCESS_TOKEN,
        plaintext=PLAINTEXT,
    )
    second = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_ACCESS_TOKEN,
        plaintext=PLAINTEXT,
    )
    # The reference is a lineage identifier, not a row id; load by reference.
    first_row = db_session.scalar(
        select(CredentialSecret).where(
            CredentialSecret.reference == first.reference,
            CredentialSecret.version == 1,
        )
    )
    second_row = db_session.scalar(
        select(CredentialSecret).where(
            CredentialSecret.reference == second.reference,
            CredentialSecret.version == 1,
        )
    )
    assert first.reference != second.reference
    assert first_row is not None and second_row is not None
    assert first_row.nonce != second_row.nonce
    assert first_row.ciphertext != second_row.ciphertext


def test_cross_user_access_is_indistinguishable_from_missing(
    db_session, make_user, make_connection, vault
) -> None:
    _user_a, connection_a = _connected_connection(make_user, make_connection)
    user_b, connection_b = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection_a),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )

    with pytest.raises(SecretNotFound):
        vault.retrieve(
            db_session,
            owner=_owner(connection_b),
            reference=metadata.reference,
        )
    # Supplying another user's connection id must also fail.
    with pytest.raises(SecretNotFound):
        vault.retrieve(
            db_session,
            owner=SecretOwner(
                user_id=user_b.id,
                connection_id=connection_a.id,
                retailer_id=connection_a.retailer_id,
            ),
            reference=metadata.reference,
        )
    with pytest.raises(SecretNotFound):
        vault.store(
            db_session,
            owner=SecretOwner(
                user_id=user_b.id,
                connection_id=connection_a.id,
                retailer_id=connection_a.retailer_id,
            ),
            secret_type=SecretType.OAUTH_REFRESH_TOKEN,
            plaintext=PLAINTEXT,
        )


def test_cross_retailer_access_is_rejected(
    db_session, make_user, make_connection, vault
) -> None:
    user = make_user()
    blinkit = make_connection(
        user_id=user.id,
        status=RetailerConnectionStatus.CONNECTED,
        retailer_id="BLINKIT",
    )
    zepto = make_connection(
        user_id=user.id,
        status=RetailerConnectionStatus.CONNECTED,
        retailer_id="ZEPTO",
    )
    metadata = vault.store(
        db_session,
        owner=_owner(blinkit),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )

    with pytest.raises(SecretNotFound):
        vault.retrieve(
            db_session,
            owner=SecretOwner(
                user_id=user.id,
                connection_id=zepto.id,
                retailer_id="BLINKIT",
            ),
            reference=metadata.reference,
        )
    with pytest.raises(SecretNotFound):
        vault.retrieve(
            db_session,
            owner=SecretOwner(
                user_id=user.id,
                connection_id=blinkit.id,
                retailer_id="ZEPTO",
            ),
            reference=metadata.reference,
        )


def test_cross_connection_access_is_rejected(
    db_session, make_user, make_connection, vault, clock
) -> None:
    user = make_user()
    first = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    metadata = vault.store(
        db_session,
        owner=_owner(first),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    service.disconnect(
        db_session,
        user_id=user.id,
        connection_id=first.id,
        clock=clock,
    )
    second = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )

    with pytest.raises(SecretNotFound):
        vault.retrieve(
            db_session,
            owner=_owner(second),
            reference=metadata.reference,
        )


@pytest.mark.parametrize(
    "secret_type",
    [
        "password",
        "retailer_password",
        "otp",
        "payment_card",
        "cvv",
        "upi_pin",
        "payment_otp",
        "reusable_payment_credential",
        "not_a_real_type",
    ],
)
def test_unsupported_and_forbidden_secret_types_are_rejected(
    db_session, make_user, make_connection, vault, secret_type
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    with pytest.raises(UnsupportedSecretType):
        vault.store(
            db_session,
            owner=_owner(connection),
            secret_type=secret_type,
            plaintext=PLAINTEXT,
        )


def test_empty_and_non_bytes_secret_material_is_rejected(
    db_session, make_user, make_connection, vault
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    with pytest.raises(InvalidSecretInput):
        vault.store(
            db_session,
            owner=_owner(connection),
            secret_type=SecretType.OAUTH_REFRESH_TOKEN,
            plaintext=b"",
        )
    with pytest.raises(InvalidSecretInput):
        vault.store(
            db_session,
            owner=_owner(connection),
            secret_type=SecretType.OAUTH_REFRESH_TOKEN,
            plaintext="not-bytes",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("target", "transition_kwargs"),
    [
        (
            RetailerConnectionStatus.DEGRADED,
            {
                "to_state": RetailerConnectionStatus.DEGRADED,
                "reason": RetailerConnectionReason.HEALTH_DEGRADED,
            },
        ),
        (
            RetailerConnectionStatus.REAUTH_REQUIRED,
            {
                "to_state": RetailerConnectionStatus.REAUTH_REQUIRED,
                "reason": RetailerConnectionReason.AUTH_FAILED,
            },
        ),
        (
            RetailerConnectionStatus.BLOCKED,
            {
                "to_state": RetailerConnectionStatus.BLOCKED,
                "reason": RetailerConnectionReason.BLOCKED,
                "restriction_source": "retailer",
                "restriction_category": "account_suspended",
            },
        ),
        (
            RetailerConnectionStatus.REVOKED,
            {
                "to_state": RetailerConnectionStatus.REVOKED,
                "reason": RetailerConnectionReason.REVOKED,
            },
        ),
        (
            RetailerConnectionStatus.DISCONNECTED,
            {
                "to_state": RetailerConnectionStatus.DISCONNECTED,
                "reason": RetailerConnectionReason.DISCONNECTED,
            },
        ),
    ],
)
def test_retrieval_is_blocked_by_lifecycle_state(
    db_session, make_user, make_connection, vault, clock, target, transition_kwargs
) -> None:
    user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )

    service.transition(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        clock=clock,
        **transition_kwargs,
    )
    with pytest.raises(SecretAccessDenied):
        vault.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
        )


def test_pending_auth_connection_cannot_use_a_persisted_secret(
    db_session, make_user, make_connection, vault
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.PENDING_AUTH
    )
    # Simulate material persisted by an earlier authentication step.
    row = CredentialSecret(
        reference=uuid4(),
        version=1,
        user_id=user.id,
        connection_id=connection.id,
        retailer_id=connection.retailer_id,
        secret_type=SecretType.OAUTH_REFRESH_TOKEN.value,
        status=SecretStatus.ACTIVE.value,
        key_version="test-v1",
        nonce=b"x" * 12,
        ciphertext=b"x" * 16,
    )
    db_session.add(row)
    db_session.commit()

    with pytest.raises(SecretAccessDenied):
        vault.retrieve(
            db_session,
            owner=_owner(connection),
            reference=row.reference,
        )


@pytest.mark.parametrize(
    "operation",
    [
        RetailerOperation.CARTEL_DATA_ACCESS,
        RetailerOperation.CONNECTION_METADATA,
    ],
)
def test_management_operations_cannot_unlock_secret_retrieval(
    db_session, make_user, make_connection, vault, operation
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    with pytest.raises(SecretAccessDenied):
        vault.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
            operation=operation,
        )


def test_reauth_required_cannot_use_connection_metadata_to_retrieve_secret(
    db_session, make_user, make_connection, vault, clock
) -> None:
    user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    service.record_authentication_failure(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        clock=clock,
    )
    with pytest.raises(SecretAccessDenied):
        vault.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
            operation=RetailerOperation.CONNECTION_METADATA,
        )


def test_degraded_allows_only_bounded_health_check_retrieval(
    db_session, make_user, make_connection, vault, clock
) -> None:
    user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.RETAILER_AUTHORIZATION_ARTIFACT,
        plaintext=PLAINTEXT,
    )
    service.transition(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        to_state=RetailerConnectionStatus.DEGRADED,
        reason=RetailerConnectionReason.HEALTH_DEGRADED,
        clock=clock,
    )

    with pytest.raises(SecretAccessDenied):
        vault.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
        )
    assert (
        vault.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
            operation=RetailerOperation.RETAILER_HEALTH_CHECK,
        )
        == PLAINTEXT
    )


def test_blocked_connection_cannot_store_or_rotate(
    db_session, make_user, make_connection, vault, clock
) -> None:
    user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    service.record_block(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        restriction_source="legal",
        restriction_category="legal_hold",
        clock=clock,
    )

    with pytest.raises(SecretAccessDenied):
        vault.store(
            db_session,
            owner=_owner(connection),
            secret_type=SecretType.OAUTH_REFRESH_TOKEN,
            plaintext=b"another",
        )
    with pytest.raises(SecretAccessDenied):
        vault.rotate(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
            plaintext=b"another",
        )


def test_revocation_immediately_blocks_retrieval_and_retains_audit(
    db_session, make_user, make_connection, vault
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    revoked = vault.revoke(
        db_session,
        owner=_owner(connection),
        reference=metadata.reference,
    )
    assert revoked.status is SecretStatus.REVOKED
    assert revoked.revoked_at is not None

    with pytest.raises(SecretNotFound):
        vault.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
        )

    events = _vault_audit_events(db_session, metadata.reference)
    assert [event.event_type for event in events] == [
        "credential_secret_created",
        "credential_secret_revoked",
    ]
    assert revoked.revoked_at is not None


def test_rotation_creates_new_version_and_shreds_old_material(
    db_session, make_user, make_connection, vault
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    rotated = vault.rotate(
        db_session,
        owner=_owner(connection),
        reference=metadata.reference,
        plaintext=b"new-material",
        expected_version=1,
    )
    assert rotated.version == 2
    assert rotated.status is SecretStatus.ACTIVE

    old = db_session.scalar(
        select(CredentialSecret).where(
            CredentialSecret.reference == metadata.reference,
            CredentialSecret.version == 1,
        )
    )
    assert old is not None
    assert old.status == SecretStatus.SUPERSEDED.value
    assert old.nonce is None and old.ciphertext is None
    assert old.superseded_at == NOW

    assert (
        vault.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
        )
        == b"new-material"
    )
    # A stale expected version is rejected.
    with pytest.raises(SecretVersionConflict):
        vault.rotate(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
            plaintext=b"stale",
            expected_version=1,
        )


def test_concurrent_rotation_allows_exactly_one_winner(
    db_session, make_user, make_connection, key_provider, session_factory
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    vault = CredentialVault(key_provider=key_provider, clock=FrozenClock(NOW))
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )

    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def rotate(plaintext: bytes) -> None:
        session = session_factory()
        try:
            barrier.wait(timeout=5)
            try:
                vault.rotate(
                    session,
                    owner=_owner(connection),
                    reference=metadata.reference,
                    plaintext=plaintext,
                    expected_version=1,
                )
                result = "ok"
            except (SecretVersionConflict, SecretStateConflict):
                result = "conflict"
            except Exception as exc:  # noqa: BLE001 - surfaced in assertion
                result = f"unexpected:{type(exc).__name__}"
            with lock:
                outcomes.append(result)
        finally:
            session.close()

    threads = [
        threading.Thread(target=rotate, args=(b"one",)),
        threading.Thread(target=rotate, args=(b"two",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(outcomes) == ["conflict", "ok"]

    active = db_session.scalars(
        select(CredentialSecret).where(
            CredentialSecret.reference == metadata.reference,
            CredentialSecret.status == SecretStatus.ACTIVE.value,
        )
    ).all()
    assert len(active) == 1
    assert active[0].version == 2


def test_delete_requires_revocation_and_shreds_material(
    db_session, make_user, make_connection, vault
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )

    with pytest.raises(SecretDeletionDenied):
        vault.delete(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
        )

    vault.revoke(
        db_session,
        owner=_owner(connection),
        reference=metadata.reference,
    )
    vault.delete(
        db_session,
        owner=_owner(connection),
        reference=metadata.reference,
    )

    row = db_session.scalar(
        select(CredentialSecret).where(
            CredentialSecret.reference == metadata.reference
        )
    )
    assert row is not None
    assert row.status == SecretStatus.DELETED.value
    assert row.nonce is None and row.ciphertext is None
    with pytest.raises(SecretNotFound):
        vault.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
        )

    events = _vault_audit_events(db_session, metadata.reference)
    assert [event.event_type for event in events] == [
        "credential_secret_created",
        "credential_secret_revoked",
        "credential_secret_deleted",
    ]


def test_key_version_compatibility_and_fail_closed_missing_key(
    db_session, make_user, make_connection
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    provider = StaticKeyProvider(
        {"test-v1": bytes(range(32)), "test-v2": bytes(range(32, 64))},
        active_version="test-v1",
    )
    vault = CredentialVault(key_provider=provider, clock=FrozenClock(NOW))
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )

    # New encryptions use the new active version, but the old version remains
    # decryptable because key_version is persisted per row.
    provider_v2 = StaticKeyProvider(
        {"test-v1": bytes(range(32)), "test-v2": bytes(range(32, 64))},
        active_version="test-v2",
    )
    vault_v2 = CredentialVault(key_provider=provider_v2, clock=FrozenClock(NOW))
    assert (
        vault_v2.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
        )
        == PLAINTEXT
    )

    # Removing the required key version fails closed.
    missing_v1 = StaticKeyProvider(
        {"test-v2": bytes(range(32, 64))}, active_version="test-v2"
    )
    vault_missing = CredentialVault(
        key_provider=missing_v1, clock=FrozenClock(NOW)
    )
    with pytest.raises(VaultKeyUnavailable):
        vault_missing.retrieve(
            db_session,
            owner=_owner(connection),
            reference=metadata.reference,
        )


def test_unavailable_key_provider_fails_closed(
    db_session, make_user, make_connection
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    vault = CredentialVault(
        key_provider=UnavailableKeyProvider(), clock=FrozenClock(NOW)
    )
    with pytest.raises(VaultUnavailable):
        vault.store(
            db_session,
            owner=_owner(connection),
            secret_type=SecretType.OAUTH_REFRESH_TOKEN,
            plaintext=PLAINTEXT,
        )


def test_metadata_and_model_representations_never_expose_secret_material(
    db_session, make_user, make_connection, vault
) -> None:
    _user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    row = db_session.scalar(
        select(CredentialSecret).where(
            CredentialSecret.reference == metadata.reference
        )
    )
    assert row is not None

    for rendered in (
        repr(row),
        str(row),
        repr(metadata),
        str(metadata),
        repr(dataclasses.asdict(metadata)),
        repr(vault.list_metadata(db_session, owner=_owner(connection))),
    ):
        assert "opaque-refresh-token-material" not in rendered
        assert "ciphertext" not in rendered
        assert "nonce" not in rendered

    events = _vault_audit_events(db_session, metadata.reference)
    for event in events:
        assert set(event.payload or {}) == AUDIT_PAYLOAD_FIELDS
        serialized = repr(event.payload)
        assert "opaque-refresh-token-material" not in serialized
        assert "ciphertext" not in serialized
        assert "nonce" not in serialized


def test_composite_foreign_key_rejects_cross_retailer_binding(
    db_session, make_user, make_connection
) -> None:
    user, connection = _connected_connection(make_user, make_connection)
    row = CredentialSecret(
        reference=uuid4(),
        version=1,
        user_id=user.id,
        connection_id=connection.id,
        retailer_id="ZEPTO",
        secret_type=SecretType.OAUTH_REFRESH_TOKEN.value,
        status=SecretStatus.ACTIVE.value,
        key_version="test-v1",
        nonce=b"x" * 12,
        ciphertext=b"x" * 16,
    )
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_partial_unique_index_rejects_two_active_versions_for_one_reference(
    db_session, make_user, make_connection
) -> None:
    user, connection = _connected_connection(make_user, make_connection)
    reference = uuid4()

    def row(version: int) -> CredentialSecret:
        return CredentialSecret(
            reference=reference,
            version=version,
            user_id=user.id,
            connection_id=connection.id,
            retailer_id=connection.retailer_id,
            secret_type=SecretType.OAUTH_REFRESH_TOKEN.value,
            status=SecretStatus.ACTIVE.value,
            key_version="test-v1",
            nonce=b"x" * 12,
            ciphertext=b"x" * 16,
        )

    db_session.add(row(1))
    db_session.flush()
    db_session.add(row(2))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_inspect_is_non_secret_and_available_for_management(
    db_session, make_user, make_connection, vault, clock
) -> None:
    user, connection = _connected_connection(make_user, make_connection)
    metadata = vault.store(
        db_session,
        owner=_owner(connection),
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        plaintext=PLAINTEXT,
    )
    service.record_block(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        restriction_source="cartel_operator",
        restriction_category="fraud_review",
        clock=clock,
    )

    inspected = vault.inspect(
        db_session,
        owner=_owner(connection),
        reference=metadata.reference,
    )
    assert isinstance(inspected, SecretMetadata)
    assert inspected.status is SecretStatus.ACTIVE
    assert "opaque-refresh-token-material" not in repr(inspected)
