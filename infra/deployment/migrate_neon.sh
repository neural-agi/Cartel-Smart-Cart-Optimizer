#!/usr/bin/env bash
# Cartel — approved one-time Neon migration (Architecture A).
#
# This script never prints the connection string. It requires DATABASE_URL to be
# exported explicitly (never inferred from a .env file) and refuses to run if
# the repository does not have exactly one Alembic head.
#
# Usage (after explicit approval for this action):
#   export DATABASE_URL='postgresql+psycopg://...@<neon-direct-host>/<db>?sslmode=require'
#   infra/deployment/migrate_neon.sh
#
# Do not use the pooled ("-pooler") host for this command.

set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: export DATABASE_URL explicitly with the Neon DIRECT endpoint." >&2
  exit 2
fi

case "$DATABASE_URL" in
  postgresql+psycopg://*) ;;
  *)
    echo "ERROR: DATABASE_URL must use the postgresql+psycopg:// scheme." >&2
    exit 2
    ;;
esac

if [[ "$DATABASE_URL" == *"-pooler"* ]]; then
  echo "ERROR: use the DIRECT Neon endpoint (no '-pooler') for migrations." >&2
  exit 2
fi

masked_target="$(DATABASE_URL="$DATABASE_URL" python3 - <<'PY'
import os
from urllib.parse import urlsplit

parsed = urlsplit(os.environ["DATABASE_URL"])
user = parsed.username or "<user>"
host = parsed.hostname or "<host>"
port = parsed.port or 5432
path = parsed.path or "/<db>"
query = parsed.query or "sslmode=require"
print(f"{parsed.scheme}://{user}:***@{host}:{port}{path}?{query}")
PY
)"
echo "migration target: $masked_target"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd "$script_dir/../../backend" && pwd)"
cd "$backend_dir"

head_output="$(alembic -c alembic.ini heads)"
head_count="$(printf '%s\n' "$head_output" | grep -c '(head)')"
if [[ "$head_count" -ne 1 ]]; then
  echo "ERROR: expected exactly one Alembic head, found $head_count." >&2
  printf '%s\n' "$head_output" >&2
  exit 3
fi
echo "repository head: $(printf '%s\n' "$head_output" | head -n 1)"

echo "current revision before upgrade:"
alembic -c alembic.ini current

alembic -c alembic.ini upgrade head

echo "current revision after upgrade:"
alembic -c alembic.ini current

DATABASE_URL="$DATABASE_URL" python3 - <<'PY'
import os
from sqlalchemy import create_engine, inspect, text

url = os.environ["DATABASE_URL"]
engine = create_engine(url, pool_pre_ping=True)
expected = {
    "alembic_version",
    "audit_events",
    "background_jobs",
    "credential_secrets",
    "email_outbox_events",
    "idempotency_records",
    "identities",
    "oauth_challenges",
    "optimization_allocations",
    "optimization_plans",
    "optimization_requests",
    "password_credentials",
    "retailer_connections",
    "sessions",
    "shopping_list_items",
    "shopping_lists",
    "users",
    "verification_challenges",
}
with engine.connect() as connection:
    revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    tables = set(inspect(connection).get_table_names())
missing = sorted(expected - tables)
print(f"alembic_version={revision}")
print(f"table_count={len(tables)}")
print("missing_expected_tables=" + (",".join(missing) if missing else "none"))
if revision != "0009_credential_vault":
    raise SystemExit(f"unexpected alembic revision: {revision}")
if missing:
    raise SystemExit("expected tables missing")
PY

echo "migration verification passed"
