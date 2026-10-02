# Cartel Frontend

The frontend is a Next.js application. In production Compose, it is the only service published to the host and proxies same-origin `/api/*` requests to the private backend service using `BACKEND_INTERNAL_URL` (default `http://api:8000`). The browser must not be configured to call the private backend hostname directly.

## Local Development

From this directory, install the exact dependency graph in `package-lock.json` and run:

```bash
npm ci
npm run dev
```

For direct local backend access during development only, `NEXT_PUBLIC_API_BASE_URL` may be set in `.env.local` (for example `http://localhost:8000`). Leave it unset in the Compose deployment so API requests use the same-origin proxy. Production login validates the operator-provided bearer token through `/api/v1/auth/session`; subsequent API requests use that token from browser session storage.

## Validation

```bash
npm ci
npm run lint
npm run typecheck
npm run build
```

The production container uses the lockfile, Next.js standalone output, and the Compose proxy configuration. Public TLS, DNS, and secret provisioning are deployment-platform responsibilities; see the repository root README for the single-host Compose instructions.
