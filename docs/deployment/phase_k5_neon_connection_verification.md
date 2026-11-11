# Phase K.5 — Neon Connection Verification (Read-Only)

**Date:** 2026-11-11
**Project (masked):** `my-first-project`
**Branch:** `production`
**Database:** `neondb`
**Role:** `neondb_owner`
**Region:** AWS US East 2 (Ohio), `aws-us-east-2`
**PostgreSQL:** 18.6 (live-verified via `current_setting('server_version')`)
**Plan:** Free
**Scope:** Read-only verification. No migration, write query, fixture seed, project creation/deletion, or other-provider configuration was performed.

**Result:** Static/offline verification **PASSES**, and the user completed the live read-only verification on 2026-11-11. Live results confirm `current_database() = neondb`, `current_user = neondb_owner`, `server_version = 18.6`, `alembic_version = NULL`, and **zero** non-system tables and **zero** rows in `pg_stat_user_tables`. The database was empty and ready for the first migration.

> **Post-verification addendum (2026-11-11):** the approved migration was subsequently executed by the user against this database over the direct endpoint. The user reported `alembic_version = 0009_credential_vault`, **18** application tables, no missing expected tables, and script verification passed. The emptiness findings above are the **pre-migration** state; they are now historical. See [`phase_k5_neon_migration_plan.md`](./phase_k5_neon_migration_plan.md) §12 for the execution record and for the post-migration checks that remain outstanding.

---

## 1. Inputs and authorization

The facts in the header come from the user's Neon Console inspection on 2026-11-11:

- Pooling OFF: direct endpoint confirmed; hostname does not contain `-pooler`.
- Pooling ON: pooled endpoint available.
- TLS required (`sslmode=require`).

No credential, connection string, password, or API key was supplied to the assistant. None is present in the repository or environment:

- `DATABASE_URL`, `CARTEL_DATABASE_URL`, `NEON_DATABASE_URL`, `PGHOST`, `PGDATABASE`, `PGUSER`: absent.
- `backend/.env`, `.env`, `.env.local`, `backend/.env.local`: no database keys.
- `neonctl`: not installed; no Neon CLI credentials.

The assistant did **not** ask for a password or connection string, and did not open the Neon Console.

---

## 2. Verification matrix

| # | Question | Method | Result |
| --- | --- | --- | --- |
| 1 | Default database and role | Console input + live query by the user | **Verified live: `neondb` / `neondb_owner`** |
| 2 | Application tables or user data exist | Live query by the user | **Verified live: zero non-system tables, zero rows** |
| 3 | Direct endpoint compatible with psycopg 3 | SQLAlchemy URL parsing + psycopg conninfo parsing + provider docs + code scan | **PASS (static)** |
| 4 | Pooled endpoint compatible with psycopg 3 | Same, plus Neon PgBouncer feature list | **PASS (static), with documented transaction-mode caveats** |
| 5 | PostgreSQL 18 compatible with models/Alembic | Support matrices + offline Alembic SQL + model DDL compile | **PASS (static/offline)** |
| 6 | Ohio vs Singapore | Provider region docs + architecture | **Recommendation: retain Ohio and co-locate Render in Ohio** |
| 7 | FastAPI vs Alembic endpoint | Neon pooling semantics + application code scan | **FastAPI: pooled; Alembic: direct** |
| 8 | Masked target recorded | This report | **Recorded** |

---

## 3. Default database and role

Console reports database `neondb` and role `neondb_owner`. Neon documents exactly this default behaviour:

> "A Postgres database that resides on the project's default branch. If you did not specify your own database name when creating the project, the database created is named `neondb`."

> "A Postgres role that is named for your database. For example, if your database is named `neondb`, the project is created with a default role named `neondb_owner`."

Source: https://neon.com/docs/manage/projects (accessed 2026-11-11).

Neon's signup guide also states the default branch `production` is selected with the default database `neondb` (https://neon.com/docs/get-started/signing-up, accessed 2026-11-11).

**Assessment:** the user's live query confirms `current_database() = neondb` and `current_user = neondb_owner`, exactly matching the documented defaults. The role's ability to create schema objects is confirmed indirectly by the successful execution of the inventory queries and by Neon's ownership model (`neondb_owner` owns the database); the migration's first DDL statement remains the definitive privilege proof.

---

## 4. Existing application tables or user data

**Verified live by the user on 2026-11-11: the database is empty.**

Confirmed results:

| Check | Result |
| --- | --- |
| `current_database()` | `neondb` |
| `current_user` | `neondb_owner` |
| `current_setting('server_version')` | `18.6` |
| `to_regclass('public.alembic_version')` | `NULL` (table absent) |
| Non-system table inventory | zero rows |
| `pg_stat_user_tables` | zero rows |

What this means:

- Cartel's 17 application tables and `alembic_version` are **absent**.
- No sample or manual objects (including `playing_with_neon`) exist in a non-system schema.
- No user data exists, so there is nothing to preserve or migrate.
- The assistant did not run any migration, DDL, or seeding against this project; the live check was performed by the user out-of-band.

The SELECT-only statements used were:

```sql
-- 1. Identity and version
SELECT current_database(), current_user,
       current_setting('server_version') AS server_version;

-- 2. Any non-system tables (returned zero rows)
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY 1, 2;

-- 3. Alembic marker (returned NULL)
SELECT to_regclass('public.alembic_version') AS alembic_version_table;

-- 4. Row counts (returned zero rows)
SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

The pre-migration emptiness gate is therefore **satisfied**. Any object appearing between this check and the approved migration is a stop condition; do not drop or recreate anything.

---

## 5. psycopg 3 endpoint compatibility

### 5.1 Installed driver/runtime (local verification environment)

| Component | Version |
| --- | --- |
| Python | 3.14.7 (local); Render target is 3.12 |
| psycopg | 3.3.4 (binary) |
| bundled libpq | 18.0.0 |
| SQLAlchemy | 2.0.52 |
| Alembic | 1.19.1 |

Provider support statements:

- psycopg 3 documentation: "PostgreSQL: from version 10 to 18" (https://www.psycopg.org/psycopg3/docs/basic/install.html, accessed 2026-11-11).
- SQLAlchemy 2.0 PostgreSQL dialect: supported PostgreSQL version `9.6+` (https://docs.sqlalchemy.org/en/20/dialects/postgresql.html, accessed 2026-11-11).

### 5.2 URL and conninfo parsing (no connection)

Both endpoint shapes were parsed with SQLAlchemy and psycopg's `conninfo_to_dict` using placeholder credentials:

| Shape | Host contains `-pooler` | `sslmode` preserved | `channel_binding` preserved | Database | Port |
| --- | --- | --- | --- | --- | --- |
| Direct | no | `require` | `require` | `neondb` | default 5432 |
| Pooled | yes | `require` | `require` | `neondb` | default 5432 |

Result: both URLs are accepted by SQLAlchemy 2.0.52 and psycopg 3.3.4. No credential value was printed.

### 5.3 Pooled-endpoint caveats

Neon uses PgBouncer in transaction mode:

> "Neon uses PgBouncer in transaction mode (`pool_mode=transaction`), which means connections are returned to the pool after each transaction completes. This limits some Postgres features that require persistent sessions."

Source: https://neon.com/docs/connect/connection-pooling (accessed 2026-11-11).

Not supported on pooled connections, per that page:

- `SET` / `RESET` session variables
- `LISTEN` / `NOTIFY`
- SQL-level `PREPARE` / `DEALLOCATE`
- temporary tables with `PRESERVE` / `DELETE ROWS`
- `LOAD`
- session-level advisory locks

Neon also documents protocol-level prepared statements as supported (PgBouncer 1.22.0+), with `max_prepared_statements=1000`. psycopg 3 uses protocol-level prepared statements, which is the supported form.

**Code scan of the Cartel database layer:** no `SET` session variables, no `search_path` changes, no `LISTEN`/`NOTIFY`, no SQL-level `PREPARE`/`DEALLOCATE`, no session advisory locks, no temporary tables. The only row-locking is `SELECT ... FOR UPDATE` inside ordinary transactions, which transaction pooling supports.

**Assessment:** the pooled endpoint is compatible with the current application. The direct endpoint is also compatible and avoids all transaction-mode caveats.

### 5.4 Live driver test status

The user's live checks above prove the database is reachable and empty, but they were run through the Neon SQL Editor, not through `psycopg` 3. A live `psycopg` connection through **both** endpoints is still unproven.

The **direct** endpoint will be exercised for real by the approved Alembic migration, which is the strongest possible proof. The **pooled** endpoint is first exercised when Render starts and calls `/ready`; that check performs a real PostgreSQL query and a Redis ping and is part of the hosted smoke gate.

Optional pre-flight driver test, run locally with the URLs already exported in your shell (do **not** paste them into chat):

```bash
python3 - <<'PY'
import os
import psycopg

for name in ("NEON_DIRECT_URL", "NEON_POOLED_URL"):
    url = os.environ[name].replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select current_database(), current_user, "
                "current_setting('server_version')"
            )
            print(name, cur.fetchone())
PY
```

To force protocol-level prepared statements on the pooled endpoint (read-only):

```bash
python3 - <<'PY'
import os
import psycopg

url = os.environ["NEON_POOLED_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
with psycopg.connect(url, prepare_threshold=0, connect_timeout=10) as conn:
    for _ in range(20):
        assert conn.execute("select 1").fetchone() == (1,)
print("pooled protocol-level prepared statements: OK")
PY
```

---

## 6. PostgreSQL 18 compatibility

### 6.1 Provider support

- Neon: "Neon supports Postgres 14, 15, 16, 17, and 18." (https://neon.com/docs/reference/compatibility, accessed 2026-11-11).
- Neon also states it supports the five latest major versions and automatically applies the latest minor release (https://neon.com/docs/postgresql/postgres-version-support, accessed 2026-11-11).
- psycopg 3: PostgreSQL 10–18.
- SQLAlchemy 2.0: PostgreSQL 9.6+.

### 6.2 Offline Alembic chain

`alembic heads` → single head `0009_credential_vault`.

`alembic upgrade head --sql` was generated **offline** against the `postgresql+psycopg` dialect with a placeholder URL. No database was contacted.

| Metric | Result |
| --- | --- |
| Exit code | 0 |
| Generated SQL lines | 427 |
| `CREATE TABLE` | 18 (17 application tables + `alembic_version`) |
| Indexes | 23 |
| Foreign keys | 18 |
| Unique constraints | 18 |
| Check constraints | 37 |
| Extensions (`CREATE EXTENSION`) | 0 |
| Enum types / `CREATE TYPE` | 0 |
| Identity columns | 0 |
| Generated columns | 0 |
| `NULLS NOT DISTINCT` / `EXCLUDE` | 0 |

### 6.3 Model metadata compile

All 17 model tables and their indexes were compiled with the PostgreSQL dialect:

- Table count: 17
- Compiled DDL: 15,232 characters
- Compile errors: 0

### 6.4 Types used

| Type | PostgreSQL representation | PG18 status |
| --- | --- | --- |
| `postgresql.UUID` | `uuid` | stable |
| `postgresql.JSONB` | `jsonb` | stable |
| `sa.LargeBinary` | `bytea` | stable |
| `sa.DateTime(timezone=True)` | `timestamptz` | stable |
| `sa.String` / `sa.Text` | `varchar` / `text` | stable |
| `sa.Integer` / `sa.Boolean` | `integer` / `boolean` | stable |
| `sa.func.now()` defaults | `now()` | stable |

Partial indexes use `postgresql_where` with simple boolean predicates (`status NOT IN (...)`, `status = 'ACTIVE'`), which are standard PostgreSQL and unchanged in PG18.

### 6.5 Residual risk

This is **static/offline** verification, not a live PG18 execution. The first real proof is the approved migration against Neon. The risk is assessed as **low** because:

- no extensions, custom types, enums, identity columns, generated columns, or session-level features are used;
- the DDL is plain `CREATE TABLE` / `CREATE INDEX` / `ALTER TABLE` / constraint syntax;
- the driver explicitly supports PostgreSQL 18;
- the same chain already passed on PostgreSQL 16.

The migration remains a separate approval and must stop on the first error.

---

## 7. Region assessment — Ohio vs Singapore

### 7.1 Provider constraints

- Neon: "To minimize latency between your Neon database and application, we recommend choosing the region closest to your application server." "You cannot change the region for an existing project… region is fixed when the project is created." (https://neon.com/docs/introduction/regions, accessed 2026-11-11).
- Neon offers Singapore (`aws-ap-southeast-1`) and Ohio (`aws-us-east-2`).
- Render offers Oregon, Ohio, Virginia, Frankfurt, and Singapore (https://render.com/docs/regions, accessed 2026-11-11).
- Render: "Render doesn't currently support changing the region for an existing service or database. Instead, create a new service or database in the desired region…" (same page).
- Vercel: static assets are served from the global CDN; Vercel Functions default to Washington, D.C. (`iad1`) for new projects, and Hobby allows a **single** function region (https://vercel.com/docs/functions/regions, accessed 2026-11-11).

### 7.2 Options

| Option | DB ↔ backend latency | Rework | Notes |
| --- | --- | --- | --- |
| **A. Retain Ohio + Render Ohio** | Lowest (same US East region) | None | Matches Neon project already created; matches Vercel's default US East function region; no new project |
| B. Singapore Neon + Render Singapore | Lowest (same Singapore region) | New Neon project + new Render service | Better for an India/Southeast Asia audience; requires creating a second Neon project before migrations |
| C. Ohio Neon + Render Singapore | High cross-region latency | None | **Do not do this** — every query crosses regions |

### 7.3 Recommendation

**Retain Ohio and create the Render backend in Ohio (US East).**

Reasons:

1. Neon's region is fixed; the project already exists in Ohio.
2. DB↔backend traffic is the latency-sensitive path; co-location matters more than the user's distance to the database.
3. Vercel's default function region is US East (`iad1`), and Hobby is limited to one function region, so Ohio is the closest practical match.
4. Render Free supports Ohio; no paid plan or region add-on is needed.
5. Zero rework and no second project, which keeps the ₹0/cardless path simple.

**When to choose Singapore instead:** if the primary audience is India/Southeast Asia and measured API latency from that audience is unacceptable, switch **before the migration and before any real user data**. That requires creating a Singapore Neon project and a Singapore Render service, then deleting or abandoning the Ohio project. Because Render and Neon cannot change region in place, this is a create-and-migrate operation, not a toggle. It is **not** authorized by this verification task and was not performed.

**Never** pair an Ohio database with a Singapore backend (or vice versa).

---

## 8. Endpoint recommendation

| Consumer | Endpoint | URL shape | Why |
| --- | --- | --- | --- |
| FastAPI on Render | **Pooled** | `postgresql+psycopg://neondb_owner:***@<endpoint-id>-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require` | PgBouncer transaction pooling protects Neon's connection limit across Render restarts and concurrency; application code uses no unsupported session features |
| Alembic migrations | **Direct** | `postgresql+psycopg://neondb_owner:***@<endpoint-id>.us-east-2.aws.neon.tech/neondb?sslmode=require` | DDL and migration transactions should use a stable direct session; avoids transaction-pooling caveats and pooler timeouts |

Runtime pool settings remain:

```
DB_POOL_SIZE=1
DB_MAX_OVERFLOW=0
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=300
```

Notes:

- Use the pooled host **only** for the FastAPI runtime and the direct host **only** for Alembic. Do not swap them.
- `sslmode=require` is the documented minimum. Neon's connection examples also show `channel_binding=require`; add it only if the read-only psycopg test succeeds on both endpoints. If it fails, keep `sslmode=require`.
- Never print or commit either URL. `infra/deployment/migrate_neon.sh` already refuses a `-pooler` host and masks the target.

---

## 9. Masked project/database target

```
provider:        Neon (Free)
project:         my-first-project
branch:          production
database:        neondb
role:            neondb_owner
region:          aws-us-east-2 (Ohio)
postgres:        18.x
tls:             unresolved (pg_stat_ssl.ssl=false vs sslmode=require)

direct host:     <endpoint-id>.us-east-2.aws.neon.tech
pooled host:     <endpoint-id>-pooler.us-east-2.aws.neon.tech

runtime URL:     postgresql+psycopg://neondb_owner:***@<endpoint-id>-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
migration URL:   postgresql+psycopg://neondb_owner:***@<endpoint-id>.us-east-2.aws.neon.tech/neondb?sslmode=require
```

The endpoint ID, password, and full connection strings are intentionally omitted.

---

## 10. Clear recommendation

1. **Retain the Ohio project.** Do not create a Singapore project now. Deploy the Render Free backend in **Ohio** so the database and backend share a region.
2. **Use the pooled endpoint for FastAPI** and the **direct endpoint for Alembic**, both with `sslmode=require`.
3. **Pre-migration emptiness gate: PASSED.** The user's live read-only checks confirmed `neondb` / `neondb_owner`, `18.6`, `alembic_version` absent, and zero non-system tables/rows. This was the state before the approved migration.
4. **PostgreSQL 18.6 is statically compatible** with the models and the full 0001→0009 chain. The migration was subsequently executed successfully by the user.
5. **Migration executed (2026-11-11):** reported revision `0009_credential_vault`, 18 tables, no missing expected tables, script verification passed. Post-migration row-emptiness, constraint/index/column, and encoding checks were **not provided** and remain outstanding (see the migration plan §12). TLS is unresolved: `pg_stat_ssl.ssl=false` was observed while `sslmode=require` is configured.
6. **Do not add a card** to Neon. The Free plan is permanent and cardless per provider documentation; any card request is a stop condition.

**Verification status:** static/offline verification complete and passing; live identity and emptiness verification complete and passing (user-executed, 2026-11-11, pre-migration). The approved migration was then executed by the user and reported successful at `0009_credential_vault` with 18 tables. A live `psycopg` connection through the pooled endpoint is still unproven and will be exercised by Render `/ready`; several post-migration SELECT-only checks were not reported.

---

## 11. What was not done

- The assistant opened no database connection; all live checks and the migration were executed by the user.
- The assistant did not execute the migration or any DDL.
- No seeding, DML, or demo-data load was performed.
- No table, schema, role, project, or database was dropped or recreated.
- No password, connection string, API key, or token was requested, printed, logged, or committed.
- No other provider was configured.
- No Git mutation was performed.
