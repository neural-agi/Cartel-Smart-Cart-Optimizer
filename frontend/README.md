# Cartel Frontend

The frontend is a Next.js application. In production Compose, it is the only service published to the host and proxies same-origin `/api/*` requests to the private backend service using `BACKEND_INTERNAL_URL` (default `http://api:8000`). The browser must not be configured to call the private backend hostname directly.

Run the production browser flow through Compose (`docker compose up --build`) so the frontend container can resolve the private `api` service name. A host-side `npm run dev` process is not a supported deployment path when `BACKEND_INTERNAL_URL=http://api:8000`; that hostname exists only on the Compose network. Do not point the browser at `api:8000` or expose the backend port merely to make host development appear healthy.

## Local Development

From this directory, install the exact dependency graph in `package-lock.json` and run:

```bash
npm ci
npm run dev
```

Consumer sign-in uses `/api/v2/auth/*`, verified email/password, and a server-managed `HttpOnly` session cookie. The frontend keeps only the CSRF token in memory; it does not persist consumer credentials or session tokens in browser storage. Same-origin mutations send a CSRF header. Operator/service bearer credentials are separate from the consumer login flow. In Compose, leave `NEXT_PUBLIC_API_BASE_URL` unset so the browser uses the same-origin proxy; point `BACKEND_INTERNAL_URL` at the private API service.

## Validation

```bash
npm ci
npm run lint
npm run typecheck
npm run build
```

The production container uses the lockfile, Next.js standalone output, and the Compose proxy configuration. Public TLS, DNS, and secret provisioning are deployment-platform responsibilities; see the repository root README for the single-host Compose instructions.
