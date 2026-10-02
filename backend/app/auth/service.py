"""Password, challenge, and server-managed session operations."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.email_delivery import EmailDelivery
from app.core.config import Settings
from app.db.models import AuditEvent, AuthSession, Identity, PasswordCredential, User, VerificationChallenge


PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16, type=Type.ID)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_DUMMY_HASH = PASSWORD_HASHER.hash(secrets.token_urlsafe(32))


class AuthFailure(Exception):
    def __init__(self, code: str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message


@dataclass(frozen=True)
class IssuedSession:
    user: User
    raw_token: str
    raw_csrf: str
    expires_at: datetime


def normalize_email(email: str) -> str:
    value = email.strip().casefold()
    if len(value) > 320 or not EMAIL_RE.fullmatch(value):
        raise AuthFailure("invalid_email", 422, "Enter a valid email address.")
    return value


def validate_password(password: str) -> None:
    if len(password) < 12 or len(password) > 1024:
        raise AuthFailure("invalid_password", 422, "Password must be between 12 and 1024 characters.")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def csrf_token_for_session(raw_token: str) -> str:
    return hmac.new(raw_token.encode("utf-8"), b"cartel-csrf-v1", hashlib.sha256).hexdigest()


def _audit(db: Session, user_id: UUID | None, event: str, request_id: str | None) -> None:
    db.add(AuditEvent(user_id=user_id, event_type=event, request_id=request_id))


def _challenge(
    db: Session,
    settings: Settings,
    user: User,
    identity: Identity,
    purpose: str,
) -> str:
    now = datetime.now(timezone.utc)
    db.execute(
        update(VerificationChallenge)
        .where(
            VerificationChallenge.user_id == user.id,
            VerificationChallenge.purpose == purpose,
            VerificationChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    raw = secrets.token_urlsafe(32)
    db.add(
        VerificationChallenge(
            user_id=user.id,
            identity_id=identity.id,
            purpose=purpose,
            token_hash=_digest(raw),
            expires_at=now + timedelta(minutes=settings.auth_challenge_minutes),
        )
    )
    return raw


def signup(db: Session, settings: Settings, mailer: EmailDelivery, email: str, password: str, request_id: str) -> None:
    normalized = normalize_email(email)
    validate_password(password)
    existing = db.scalar(select(Identity.id).where(Identity.provider == "email_password", Identity.subject == normalized))
    if existing:
        raise AuthFailure("account_exists", 409, "An account already exists for this email.")
    user = User()
    identity = Identity(user=user, provider="email_password", subject=normalized, email=normalized)
    credential = PasswordCredential(user=user, password_hash=PASSWORD_HASHER.hash(password))
    db.add_all([user, identity, credential])
    db.flush()
    raw = _challenge(db, settings, user, identity, "email_verification")
    _audit(db, user.id, "signup_requested", request_id)
    try:
        db.flush()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        duplicate = db.scalar(
            select(Identity.id).where(
                Identity.provider == "email_password",
                Identity.subject == normalized,
            )
        )
        if duplicate is not None:
            raise AuthFailure("account_exists", 409, "An account already exists for this email.") from exc
        raise
    link = f"{settings.public_origin.rstrip('/')}/verify-email#token={raw}"
    mailer.send(normalized, "Verify your Cartel email", f"Verify your email using this link: {link}\nThis link expires soon.")


def resend_verification(db: Session, settings: Settings, mailer: EmailDelivery, email: str) -> None:
    normalized = normalize_email(email)
    identity = db.scalar(select(Identity).where(Identity.provider == "email_password", Identity.subject == normalized))
    if identity is None or identity.email_verified_at is not None or identity.user.status != "active":
        return
    raw = _challenge(db, settings, identity.user, identity, "email_verification")
    db.commit()
    link = f"{settings.public_origin.rstrip('/')}/verify-email#token={raw}"
    mailer.send(normalized, "Verify your Cartel email", f"Verify your email using this link: {link}\nThis link expires soon.")


def _new_session(db: Session, settings: Settings, user: User, user_agent: str | None) -> IssuedSession:
    now = datetime.now(timezone.utc)
    raw_token = secrets.token_urlsafe(48)
    raw_csrf = csrf_token_for_session(raw_token)
    expires_at = now + timedelta(days=settings.auth_session_days)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=_digest(raw_token),
            csrf_hash=_digest(raw_csrf),
            expires_at=expires_at,
            user_agent_hash=_digest(user_agent[:512]) if user_agent else None,
        )
    )
    return IssuedSession(user, raw_token, raw_csrf, expires_at)


def verify_email(db: Session, settings: Settings, token: str, user_agent: str | None, request_id: str) -> IssuedSession:
    challenge = db.scalar(
        select(VerificationChallenge)
        .where(VerificationChallenge.token_hash == _digest(token), VerificationChallenge.purpose == "email_verification")
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now or challenge.attempt_count >= 5:
        if challenge:
            challenge.attempt_count += 1
            db.commit()
        raise AuthFailure("invalid_or_expired_challenge", 400, "This verification link is invalid or expired.")
    challenge.consumed_at = now
    identity = db.get(Identity, challenge.identity_id)
    user = db.get(User, challenge.user_id)
    if identity is None or user is None or user.status != "active":
        db.rollback()
        raise AuthFailure("invalid_or_expired_challenge", 400, "This verification link is invalid or expired.")
    identity.email_verified_at = now
    issued = _new_session(db, settings, user, user_agent)
    _audit(db, user.id, "email_verified", request_id)
    db.commit()
    return issued


def login(db: Session, settings: Settings, email: str, password: str, user_agent: str | None, request_id: str) -> IssuedSession:
    normalized = normalize_email(email)
    identity = db.scalar(select(Identity).where(Identity.provider == "email_password", Identity.subject == normalized))
    credential = db.get(PasswordCredential, identity.user_id) if identity else None
    stored_hash = credential.password_hash if credential else _DUMMY_HASH
    valid_password = False
    try:
        valid_password = PASSWORD_HASHER.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        pass
    if not valid_password or identity is None or credential is None or identity.email_verified_at is None or identity.user.status != "active":
        _audit(db, identity.user_id if identity else None, "login_failed", request_id)
        db.commit()
        raise AuthFailure("invalid_credentials", 401, "Email or password is incorrect, or the account is not verified.")
    if PASSWORD_HASHER.check_needs_rehash(credential.password_hash):
        credential.password_hash = PASSWORD_HASHER.hash(password)
    issued = _new_session(db, settings, identity.user, user_agent)
    _audit(db, identity.user_id, "login_succeeded", request_id)
    db.commit()
    return issued


def resolve_session(db: Session, raw_token: str, idle_days: int = 7) -> tuple[AuthSession, User] | None:
    if not raw_token or len(raw_token) > 256:
        return None
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == _digest(raw_token)))
    now = datetime.now(timezone.utc)
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        return None
    if session.last_seen_at + timedelta(days=idle_days) <= now:
        session.revoked_at = now
        session.revoke_reason = "idle_expired"
        db.commit()
        return None
    user = db.get(User, session.user_id)
    if user is None or user.status != "active" or user.deleted_at is not None:
        return None
    session.last_seen_at = now
    db.commit()
    return session, user


def require_csrf(session: AuthSession, supplied: str | None) -> None:
    from hmac import compare_digest

    if not supplied or not compare_digest(session.csrf_hash, _digest(supplied)):
        raise AuthFailure("csrf_failed", 403, "Request could not be verified.")


def rotate_session(db: Session, settings: Settings, current: AuthSession, user: User, user_agent: str | None) -> IssuedSession:
    current.revoked_at = datetime.now(timezone.utc)
    current.revoke_reason = "rotated"
    issued = _new_session(db, settings, user, user_agent)
    db.commit()
    return issued


def logout_current(db: Session, session: AuthSession, request_id: str) -> None:
    session.revoked_at = datetime.now(timezone.utc)
    session.revoke_reason = "logout"
    _audit(db, session.user_id, "logout_current", request_id)
    db.commit()


def logout_all(db: Session, user: User, request_id: str) -> None:
    now = datetime.now(timezone.utc)
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now, revoke_reason="logout_all")
    )
    _audit(db, user.id, "logout_all", request_id)
    db.commit()


def request_password_recovery(db: Session, settings: Settings, mailer: EmailDelivery, email: str) -> None:
    normalized = normalize_email(email)
    identity = db.scalar(select(Identity).where(Identity.provider == "email_password", Identity.subject == normalized))
    if identity is None or identity.email_verified_at is None or identity.user.status != "active":
        return
    raw = _challenge(db, settings, identity.user, identity, "password_recovery")
    db.commit()
    link = f"{settings.public_origin.rstrip('/')}/reset-password#token={raw}"
    mailer.send(normalized, "Reset your Cartel password", f"Reset your password using this link: {link}\nThis link expires soon.")


def reset_password(db: Session, token: str, new_password: str, request_id: str) -> None:
    validate_password(new_password)
    challenge = db.scalar(
        select(VerificationChallenge)
        .where(VerificationChallenge.token_hash == _digest(token), VerificationChallenge.purpose == "password_recovery")
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now or challenge.attempt_count >= 5:
        if challenge:
            challenge.attempt_count += 1
            db.commit()
        raise AuthFailure("invalid_or_expired_challenge", 400, "This recovery link is invalid or expired.")
    credential = db.get(PasswordCredential, challenge.user_id)
    user = db.get(User, challenge.user_id)
    if credential is None or user is None or user.status != "active":
        db.rollback()
        raise AuthFailure("invalid_or_expired_challenge", 400, "This recovery link is invalid or expired.")
    challenge.consumed_at = now
    credential.password_hash = PASSWORD_HASHER.hash(new_password)
    credential.password_changed_at = now
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now, revoke_reason="password_reset")
    )
    _audit(db, user.id, "password_reset", request_id)
    db.commit()
