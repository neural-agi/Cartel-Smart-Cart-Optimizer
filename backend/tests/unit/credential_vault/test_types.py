"""Unit coverage for vault value types and secrecy of representations."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.credential_vault.types import (
    AUDIT_PAYLOAD_FIELDS,
    FORBIDDEN_SECRET_TYPES,
    InvalidSecretInput,
    SecretMetadata,
    SecretOwner,
    SecretReference,
    SecretStatus,
    SecretType,
)


def test_secret_type_vocabulary_is_controlled() -> None:
    assert {value.value for value in SecretType} == {
        "oauth_access_token",
        "oauth_refresh_token",
        "browser_session_credential",
        "retailer_authorization_artifact",
    }


def test_forbidden_secret_types_are_not_storable() -> None:
    stored = {value.value for value in SecretType}
    assert stored.isdisjoint(FORBIDDEN_SECRET_TYPES)
    for forbidden in (
        "password",
        "otp",
        "payment_card",
        "cvv",
        "upi_pin",
        "payment_otp",
        "reusable_payment_credential",
    ):
        assert forbidden in FORBIDDEN_SECRET_TYPES


def test_secret_reference_round_trips() -> None:
    value = uuid4()
    reference = SecretReference.from_value(str(value))
    assert reference.value == value
    assert SecretReference.from_value(value) == reference
    assert str(reference) == str(value)
    assert str(value) in repr(reference)


def test_secret_reference_rejects_malformed_values() -> None:
    for value in ("", "not-a-uuid", "  ", None, 123):
        with pytest.raises(InvalidSecretInput):
            SecretReference.from_value(value)  # type: ignore[arg-type]


def test_secret_owner_and_metadata_repr_never_include_secret_material() -> None:
    user_id = uuid4()
    connection_id = uuid4()
    reference = uuid4()
    owner = SecretOwner(
        user_id=user_id,
        connection_id=connection_id,
        retailer_id="BLINKIT",
    )
    metadata = SecretMetadata(
        reference=reference,
        version=2,
        user_id=user_id,
        connection_id=connection_id,
        retailer_id="BLINKIT",
        secret_type=SecretType.OAUTH_REFRESH_TOKEN,
        status=SecretStatus.ACTIVE,
        algorithm="AES_256_GCM",
        key_version="dev-v1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    rendered = repr(owner) + repr(metadata) + str(metadata)
    assert "ciphertext" not in rendered
    assert "nonce" not in rendered
    assert "plaintext" not in rendered
    assert "token-material" not in rendered


def test_audit_payload_allowlist_contains_no_secret_material() -> None:
    assert AUDIT_PAYLOAD_FIELDS == {
        "reference",
        "user_id",
        "connection_id",
        "retailer_id",
        "secret_type",
        "version",
        "status",
        "occurred_at",
    }
    for forbidden in ("plaintext", "ciphertext", "nonce", "key", "token", "secret"):
        assert forbidden not in AUDIT_PAYLOAD_FIELDS
