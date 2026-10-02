"""Provider extension point; real provider verifiers are added independently."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VerifiedIdentity:
    provider: str
    subject: str
    email: str | None
    email_verified: bool


class IdentityProviderVerifier(Protocol):
    provider: str

    def verify(self, credential: str, *, redirect_uri: str, nonce: str) -> VerifiedIdentity: ...


class IdentityProviderUnavailable(RuntimeError):
    """Raised until a real, configured provider verifier is installed."""
