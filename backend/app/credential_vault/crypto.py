"""Authenticated encryption for the credential vault.

AES-256-GCM is used directly from the established ``cryptography`` library. No
algorithm is invented here. Every encryption uses a fresh 96-bit nonce, and the
associated data binds the ciphertext to the owner, persisted connection,
retailer, secret type, secret version, and opaque reference.
"""

from __future__ import annotations

import secrets
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.credential_vault.types import (
    InvalidSecretInput,
    SecretDecryptionFailed,
)

ALGORITHM = "AES_256_GCM"
KEY_BYTES = 32
NONCE_BYTES = 12
MAX_SECRET_BYTES = 64 * 1024
AAD_PREFIX = b"cartel-credential-vault|v1"


def build_aad(
    *,
    user_id: UUID,
    connection_id: UUID,
    retailer_id: str,
    secret_type: str,
    version: int,
    reference: UUID,
) -> bytes:
    """Build deterministic associated data for one secret version.

    The same tuple is reconstructed on decryption. Any mismatch (for example a
    ciphertext moved to another connection or replayed under another version)
    makes GCM authentication fail.
    """

    fields = (
        str(user_id),
        str(connection_id),
        retailer_id,
        secret_type,
        str(version),
        str(reference),
    )
    return AAD_PREFIX + b"|" + "|".join(fields).encode("utf-8")


class AesGcmCodec:
    """Small wrapper around AES-256-GCM with explicit input validation."""

    def encrypt(
        self,
        *,
        plaintext: bytes,
        key: bytes,
        aad: bytes,
    ) -> tuple[bytes, bytes]:
        if not isinstance(plaintext, bytes) or not plaintext:
            raise InvalidSecretInput("empty_secret")
        if len(plaintext) > MAX_SECRET_BYTES:
            raise InvalidSecretInput("secret_too_large")
        if not isinstance(key, bytes) or len(key) != KEY_BYTES:
            raise InvalidSecretInput("invalid_key_length")
        nonce = secrets.token_bytes(NONCE_BYTES)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
        return nonce, ciphertext

    def decrypt(
        self,
        *,
        nonce: bytes,
        ciphertext: bytes,
        key: bytes,
        aad: bytes,
    ) -> bytes:
        if not isinstance(nonce, bytes) or len(nonce) != NONCE_BYTES:
            raise SecretDecryptionFailed("invalid nonce")
        if not isinstance(ciphertext, bytes) or len(ciphertext) < 16:
            raise SecretDecryptionFailed("invalid ciphertext")
        if not isinstance(key, bytes) or len(key) != KEY_BYTES:
            raise SecretDecryptionFailed("invalid key")
        try:
            return AESGCM(key).decrypt(nonce, ciphertext, aad)
        except InvalidTag as exc:
            raise SecretDecryptionFailed("ciphertext authentication failed") from exc
