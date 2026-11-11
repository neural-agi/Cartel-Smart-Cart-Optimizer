"""Unit coverage for the vault's AEAD primitive and AAD construction."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.credential_vault.crypto import (
    ALGORITHM,
    AesGcmCodec,
    build_aad,
)
from app.credential_vault.types import (
    InvalidSecretInput,
    SecretDecryptionFailed,
)

KEY = bytes(range(32))
OTHER_KEY = bytes(range(32, 64))


def _aad(**overrides):
    values = {
        "user_id": uuid4(),
        "connection_id": uuid4(),
        "retailer_id": "BLINKIT",
        "secret_type": "oauth_refresh_token",
        "version": 1,
        "reference": uuid4(),
    }
    values.update(overrides)
    return build_aad(**values)


def test_round_trip_recovers_plaintext() -> None:
    codec = AesGcmCodec()
    plaintext = b"opaque-token-material"
    aad = _aad()

    nonce, ciphertext = codec.encrypt(plaintext=plaintext, key=KEY, aad=aad)

    assert nonce != plaintext
    assert ciphertext != plaintext
    assert codec.decrypt(nonce=nonce, ciphertext=ciphertext, key=KEY, aad=aad) == plaintext


def test_repeated_encryption_uses_fresh_nonce_and_ciphertext() -> None:
    codec = AesGcmCodec()
    plaintext = b"same-plaintext"
    aad = _aad()

    first = codec.encrypt(plaintext=plaintext, key=KEY, aad=aad)
    second = codec.encrypt(plaintext=plaintext, key=KEY, aad=aad)

    assert first[0] != second[0]
    assert first[1] != second[1]
    assert codec.decrypt(nonce=first[0], ciphertext=first[1], key=KEY, aad=aad) == plaintext
    assert codec.decrypt(nonce=second[0], ciphertext=second[1], key=KEY, aad=aad) == plaintext


def test_tampered_ciphertext_is_rejected() -> None:
    codec = AesGcmCodec()
    aad = _aad()
    nonce, ciphertext = codec.encrypt(plaintext=b"secret", key=KEY, aad=aad)
    tampered = bytearray(ciphertext)
    tampered[-1] ^= 0x01

    with pytest.raises(SecretDecryptionFailed):
        codec.decrypt(nonce=nonce, ciphertext=bytes(tampered), key=KEY, aad=aad)


def test_aad_mismatch_is_rejected() -> None:
    codec = AesGcmCodec()
    user_id = uuid4()
    connection_id = uuid4()
    reference = uuid4()
    aad = _aad(
        user_id=user_id,
        connection_id=connection_id,
        reference=reference,
    )
    nonce, ciphertext = codec.encrypt(plaintext=b"secret", key=KEY, aad=aad)

    mismatches = [
        _aad(user_id=uuid4(), connection_id=connection_id, reference=reference),
        _aad(user_id=user_id, connection_id=uuid4(), reference=reference),
        _aad(user_id=user_id, connection_id=connection_id, retailer_id="ZEPTO", reference=reference),
        _aad(
            user_id=user_id,
            connection_id=connection_id,
            secret_type="oauth_access_token",
            reference=reference,
        ),
        _aad(user_id=user_id, connection_id=connection_id, version=2, reference=reference),
        _aad(user_id=user_id, connection_id=connection_id, reference=uuid4()),
    ]
    for wrong_aad in mismatches:
        with pytest.raises(SecretDecryptionFailed):
            codec.decrypt(nonce=nonce, ciphertext=ciphertext, key=KEY, aad=wrong_aad)


def test_wrong_key_is_rejected() -> None:
    codec = AesGcmCodec()
    aad = _aad()
    nonce, ciphertext = codec.encrypt(plaintext=b"secret", key=KEY, aad=aad)

    with pytest.raises(SecretDecryptionFailed):
        codec.decrypt(nonce=nonce, ciphertext=ciphertext, key=OTHER_KEY, aad=aad)


def test_invalid_inputs_fail_closed() -> None:
    codec = AesGcmCodec()
    aad = _aad()

    with pytest.raises(InvalidSecretInput):
        codec.encrypt(plaintext=b"", key=KEY, aad=aad)
    with pytest.raises(InvalidSecretInput):
        codec.encrypt(plaintext=b"x" * (64 * 1024 + 1), key=KEY, aad=aad)
    with pytest.raises(InvalidSecretInput):
        codec.encrypt(plaintext=b"secret", key=b"short", aad=aad)
    with pytest.raises(SecretDecryptionFailed):
        codec.decrypt(nonce=b"short", ciphertext=b"x" * 16, key=KEY, aad=aad)
    with pytest.raises(SecretDecryptionFailed):
        codec.decrypt(nonce=b"x" * 12, ciphertext=b"short", key=KEY, aad=aad)


def test_algorithm_identifier_is_explicit() -> None:
    assert ALGORITHM == "AES_256_GCM"


def test_aad_is_deterministic_for_the_same_binding() -> None:
    values = {
        "user_id": uuid4(),
        "connection_id": uuid4(),
        "retailer_id": "BLINKIT",
        "secret_type": "oauth_refresh_token",
        "version": 3,
        "reference": uuid4(),
    }
    assert build_aad(**values) == build_aad(**values)
    assert b"cartel-credential-vault|v1" in build_aad(**values)
