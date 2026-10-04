# Consumer OAuth Identity

Cartel keeps one `users` record per account and attaches authentication methods
through `identities`. The existing unique constraint on `(provider, subject)`
is the account-ownership anchor; email is not used as an external identity
key. Password identities continue to use the existing verification and session
flow.

Google and GitHub use server-side authorization-code callbacks. Cartel stores
only a short-lived, one-use OAuth challenge containing a hash of `state`, the
nonce, PKCE verifier, redirect URI, and safe relative destination. Provider
tokens are exchanged and validated server-side and are not persisted or sent
to the browser. Google ID tokens are checked against Google JWKS, issuer,
audience, expiry, nonce, subject, and verified email. GitHub identity is keyed
by its stable numeric account ID and requires a primary verified email.

When a provider subject is already linked, Cartel signs in that user. A new
provider subject whose verified email belongs to an existing password account
is rejected with an explicit account-linking-required result; accounts are
never silently merged. A provider without a verified email is rejected.

Apple configuration fields are present for future Sign in with Apple support,
including team/key/private-key settings, but no Apple callback is enabled until
an Apple adapter is implemented and all credentials are configured. Provider
buttons are rendered only for configured providers. Blank configuration leaves
email/password authentication unchanged.

Configuration is supplied through the backend environment or secret manager:
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, equivalent
GitHub fields, and Apple readiness fields. Never put secrets in frontend code.
