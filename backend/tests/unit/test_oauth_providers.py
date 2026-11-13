from urllib.parse import parse_qs, urlsplit

import pytest

from app.auth.providers import GoogleVerifier, IdentityProviderUnavailable, provider_configuration
from app.core.config import Settings


def test_social_providers_are_disabled_without_credentials():
    settings = Settings(_env_file=None)

    assert provider_configuration(settings) == {"google": False, "github": False, "apple": False}
    with pytest.raises(IdentityProviderUnavailable):
        GoogleVerifier(settings)


def test_google_authorization_url_contains_state_nonce_and_pkce():
    settings = Settings(
        _env_file=None,
        google_client_id="google-client",
        google_client_secret="google-secret",
        google_redirect_uri="http://localhost:3000/api/v2/auth/google/callback",
    )
    query = parse_qs(urlsplit(GoogleVerifier(settings).authorization_url("state", "nonce", "challenge")).query)

    assert query["state"] == ["state"]
    assert query["nonce"] == ["nonce"]
    assert query["code_challenge"] == ["challenge"]
    assert query["code_challenge_method"] == ["S256"]
