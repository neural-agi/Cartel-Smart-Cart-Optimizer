# Local Authenticated E2E

The production Compose file requires an external SMTP relay and keeps the API
internal to the Compose network. For disposable local auth validation, use the
explicit `docker-compose.local-test.yml` override:

```bash
docker compose -f docker-compose.yml -f docker-compose.local-test.yml up --build -d
```

The override does not bypass authentication. It changes only local runtime
delivery: verification and recovery messages are written as `.eml` files to
the named `cartel-test-email` volume. A test runner reads the verification
link from that volume and visits the normal `/verify-email` flow. The API uses
the same signup, verification, login, session, and logout handlers as every
other environment.

The file mailer is rejected when `APP_ENV=production`. The override also uses
`AUTH_COOKIE_SECURE=false` because this disposable stack is served over local
HTTP, and sets `PUBLIC_ORIGIN` to the Compose frontend hostname for in-network
browser tests. No mail, account, catalog, or retailer data is intended to be
kept after the test stack is removed.

To remove the disposable database and captured mail volume:

```bash
docker compose -f docker-compose.yml -f docker-compose.local-test.yml down -v
```
