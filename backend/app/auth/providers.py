"""Server-side OAuth/OIDC provider adapters."""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from authlib.jose import JsonWebKey, jwt

from app.core.config import Settings


@dataclass(frozen=True)
class VerifiedIdentity:
    provider: str
    subject: str
    email: str | None
    email_verified: bool


class IdentityProviderUnavailable(RuntimeError):
    pass


class IdentityProviderFailure(RuntimeError):
    pass


class GoogleVerifier:
    provider = "google"

    def __init__(self, settings: Settings) -> None:
        if not settings.google_oauth_configured:
            raise IdentityProviderUnavailable("google is not configured")
        self.settings = settings

    def authorization_url(self, state: str, nonce: str, code_challenge: str) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code", "scope": "openid email profile", "state": state,
            "nonce": nonce, "code_challenge": code_challenge, "code_challenge_method": "S256",
            "access_type": "online",
        })

    def verify(self, code: str, *, redirect_uri: str, nonce: str, code_verifier: str) -> VerifiedIdentity:
        try:
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                token = client.post("https://oauth2.googleapis.com/token", data={
                    "code": code, "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret.get_secret_value(),
                    "redirect_uri": redirect_uri, "grant_type": "authorization_code",
                    "code_verifier": code_verifier,
                })
                token.raise_for_status()
                raw_id_token = token.json().get("id_token")
                if not isinstance(raw_id_token, str):
                    raise IdentityProviderFailure("google did not return an ID token")
                jwks = client.get("https://www.googleapis.com/oauth2/v3/certs")
                jwks.raise_for_status()
                claims = jwt.decode(raw_id_token, JsonWebKey.import_key_set(jwks.json()))
                claims.validate()
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise IdentityProviderFailure("google authentication failed") from exc
        if claims.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}:
            raise IdentityProviderFailure("google issuer was invalid")
        if claims.get("aud") != self.settings.google_client_id or claims.get("nonce") != nonce:
            raise IdentityProviderFailure("google claims were invalid")
        subject, email = claims.get("sub"), claims.get("email")
        if not isinstance(subject, str) or not subject or not isinstance(email, str) or claims.get("email_verified") is not True:
            raise IdentityProviderFailure("google did not provide a verified email identity")
        return VerifiedIdentity(self.provider, subject, email, True)


class GitHubVerifier:
    provider = "github"

    def __init__(self, settings: Settings) -> None:
        if not settings.github_oauth_configured:
            raise IdentityProviderUnavailable("github is not configured")
        self.settings = settings

    def authorization_url(self, state: str, nonce: str, code_challenge: str) -> str:
        return "https://github.com/login/oauth/authorize?" + urlencode({
            "client_id": self.settings.github_client_id, "redirect_uri": self.settings.github_redirect_uri,
            "scope": "read:user user:email", "state": state, "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })

    def verify(self, code: str, *, redirect_uri: str, nonce: str, code_verifier: str) -> VerifiedIdentity:
        try:
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                token = client.post("https://github.com/login/oauth/access_token", data={
                    "client_id": self.settings.github_client_id,
                    "client_secret": self.settings.github_client_secret.get_secret_value(),
                    "code": code, "redirect_uri": redirect_uri, "code_verifier": code_verifier,
                }, headers={"Accept": "application/json"})
                token.raise_for_status()
                access_token = token.json().get("access_token")
                if not isinstance(access_token, str) or not access_token:
                    raise IdentityProviderFailure("github did not return an access token")
                headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"}
                profile = client.get("https://api.github.com/user", headers=headers); profile.raise_for_status()
                emails = client.get("https://api.github.com/user/emails", headers=headers); emails.raise_for_status()
                profile_data, email_data = profile.json(), emails.json()
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise IdentityProviderFailure("github authentication failed") from exc
        verified = next((item for item in email_data if item.get("primary") and item.get("verified")), None)
        if profile_data.get("id") is None or not isinstance(verified, dict) or not isinstance(verified.get("email"), str):
            raise IdentityProviderFailure("github did not provide a verified email identity")
        return VerifiedIdentity(self.provider, str(profile_data["id"]), verified["email"], True)


def configured_verifier(settings: Settings, provider: str):
    if provider == "google": return GoogleVerifier(settings)
    if provider == "github": return GitHubVerifier(settings)
    raise IdentityProviderUnavailable("provider is not available")


def provider_configuration(settings: Settings) -> dict[str, bool]:
    return {"google": settings.google_oauth_configured, "github": settings.github_oauth_configured, "apple": settings.apple_oauth_configured}
