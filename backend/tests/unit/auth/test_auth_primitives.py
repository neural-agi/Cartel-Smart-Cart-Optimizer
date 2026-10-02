from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v2.dependencies import require_owner
from app.auth.service import (
    AuthFailure,
    PASSWORD_HASHER,
    csrf_token_for_session,
    normalize_email,
    require_csrf,
    validate_password,
)


def test_email_identity_normalization_is_stable():
    assert normalize_email("  Shopper@Example.TEST ") == "shopper@example.test"


def test_password_policy_and_argon2id_hash():
    value = "a-long-password-that-is-not-persisted"
    validate_password(value)
    encoded = PASSWORD_HASHER.hash(value)
    assert encoded.startswith("$argon2id$")
    assert value not in encoded
    assert PASSWORD_HASHER.verify(encoded, value)
    with pytest.raises(AuthFailure):
        validate_password("short")


def test_csrf_is_derived_per_session_and_compared_as_hash():
    session_secret = "opaque-session-secret"
    csrf = csrf_token_for_session(session_secret)
    session = SimpleNamespace(csrf_hash=sha256(csrf.encode()).hexdigest())
    require_csrf(session, csrf)
    with pytest.raises(AuthFailure):
        require_csrf(session, "wrong-token")


def test_owner_mismatch_is_concealed_as_not_found():
    principal = SimpleNamespace(user=SimpleNamespace(id=uuid4()))
    with pytest.raises(HTTPException) as error:
        require_owner(principal, uuid4())
    assert error.value.status_code == 404
