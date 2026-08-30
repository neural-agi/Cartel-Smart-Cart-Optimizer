"""Small, explicit API security primitives.

The token registry is intentionally operator-configured. It is a deployment
bridge, not a replacement for an external identity provider.
"""

from __future__ import annotations

from hmac import compare_digest

from app.core.config import Settings


class AuthenticationError(RuntimeError):
    pass


def authenticate_bearer(authorization: str, settings: Settings) -> str:
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("bearer authentication is required")
    token = authorization[7:].strip()
    if not token:
        raise AuthenticationError("bearer authentication is required")
    for configured_token, user_id in settings.configured_auth_tokens.items():
        if compare_digest(token, configured_token):
            return user_id
    raise AuthenticationError("invalid bearer token")
