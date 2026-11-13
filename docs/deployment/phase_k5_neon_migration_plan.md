# Phase K.5 — Neon Remote Migration Execution Plan

**Date:** 2026-11-11
**Status:** **EXECUTED (2026-11-11)** — Alembic `upgrade head` completed against Neon `neondb` over the **direct** endpoint, reported by the user. See §12 for the execution record.
**Scope:** One Alembic `upgrade head` against the Neon Free database over the **direct** endpoint. No application deploy, no seeding, no Render/Vercel/Git action.

> This document was written as a plan. It now records the user-executed migration result in §12. Only the checks explicitly listed as confirmed there are confirmed; the remaining post-migration checks were **not provided** and remain outstanding.

---

## 1. Authorization state

| Item | State |
| --- | --- |
| Read-only Neon verification | **Complete and passing** (user-executed 2026-11-11) |
| Emptiness gate | **Passed before migration** — zero non-system tables, zero rows, `alembic_version` absent |
| Migration approval | **Given** (explicit, 2026-11-11) |
| Migration executed | **Yes** — user-run, direct endpoint (see §12) |
| Migration revision | **`0009_credential_vault`** (reported) |
| Table count | **18** (reported) |
| Seeding executed | **No** |
| Application deployed | **No** |

Execution was approved for this single action only. Seeding, provider configuration, deployment, snapshots, and Git operations remain separate and were not performed.

---

## 2. Target database confirmation

Masked target — endpoint ID, password, and full URL are intentionally omitted:

```
provider:      Neon (Free plan, cardless)
project:       my-first-project
branch:        production
database:      neondb
role:          neondb_owner
region:        aws-us-east-2 (Ohio)
postgres:      18.6
tls:           required (sslmode=require)

endpoint used: DIRECT  →  <endpoint-id>.us-east-2.aws.neon.tech
endpoint NOT used for migration: pooled → <endpoint-id>-pooler.us-east-2.aws.neon.tech

migration URL shape:
  postgresql+psycopg://neondb_owner:***@<endpoint-id>.us-east-2.aws.neon.tech/neondb?sslmode=require
```

Confirmation rules:

- The host **must not** contain `-pooler`. `infra/deployment/migrate_neon.sh` refuses a pooled host.
- The scheme **must** be `postgresql+psycopg://` (psycopg 3). The script refuses any other scheme.
- The database path **must** be `/neondb`.
- TLS **must** be present. Keep `sslmode=require`; add `channel_binding=require` only if a read-only psycopg test already succeeded on both endpoints.
- The runtime (FastAPI on Render) uses the **pooled** endpoint. The two endpoints must not be swapped.
- The secret is exported into the shell only. It is never committed, pasted into chat, or printed; the script masks the target before echoing it.

---

## 3. Preflight — read-only, immediately before execution

Re-run these SELECT-only checks in the Neon SQL Editor (or `psql`) in the same maintenance window as the migration. Any deviation is a **stop condition**.

```sql
-- Identity, version, TLS, encoding
SELECT current_database()                                   AS database,
       current_user                                         AS role,
       current_setting('server_version')                    AS server_version,
       current_setting('server_encoding')                   AS server_encoding,
       current_setting('client_encoding')                   AS client_encoding,
       current_setting('TimeZone')                          AS timezone;

SELECT ssl, version
FROM pg_stat_ssl
WHERE pid = pg_backend_pid();

-- Ownership and CREATE privilege
SELECT datname, pg_get_userbyid(datdba) AS owner
FROM pg_database
WHERE datname = current_database();

SELECT has_schema_privilege(current_user, 'public', 'CREATE')   AS can_create_public,
       has_database_privilege(current_database(), 'CREATE')     AS can_create_database;

-- Emptiness gate (both must be empty)
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY 1, 2;

SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- Alembic marker (must be NULL)
SELECT to_regclass('public.alembic_version') AS alembic_version_table;
```

Expected preflight result:

| Check | Required value |
| --- | --- |
| `database` | `neondb` |
| `role` | `neondb_owner` |
| `server_version` | `18.6` |
| `ssl` | `t` |
| `can_create_public` | `t` |
| `can_create_database` | `t` (owner) |
| non-system tables | **zero rows** |
| `pg_stat_user_tables` | **zero rows** |
| `alembic_version_table` | `NULL` |

Local preflight (no database contact):

```bash
cd /path/to/Cartel-Smart-Cart-Optimizer
command -v alembic                     # must resolve
python3 -c "import psycopg, sqlalchemy, alembic; print(psycopg.__version__, sqlalchemy.__version__, alembic.__version__)"
cd backend && alembic -c alembic.ini heads   # must print exactly one head: 0009_credential_vault (head)
```

Expected local versions: psycopg `3.3.4`, SQLAlchemy `2.0.52`, Alembic `1.19.1`, single head `0009_credential_vault`.

---

## 4. Expected migration head

| Item | Value |
| --- | --- |
| Current remote revision | none (`alembic_version` absent) |
| Repository head | `0009_credential_vault` |
| Head count | exactly 1 |
| Chain executed | `0001_consumer_identity` → `0002_shopping_lists` → `0003_optimization_records` → `0004_oauth_challenges` → `0005_idempotency_records` → `0006_background_jobs` → `0007_email_outbox` → `0008_retailer_connections` → `0009_credential_vault` |
| Tables after migration | 18 (17 application tables + `alembic_version`) |
| Application rows after migration | 0 (schema only) |

---

## 5. Exact execution procedure (do not run until approved)

Run from the repository root, in a shell where the direct URL is exported. Do **not** paste the URL into chat or a tracked file.

```bash
# 1. Export the DIRECT Neon URL (no -pooler) for this shell only.
#    Prefer reading it from your password manager / Neon console directly into the
#    variable so it never appears in shell history or logs.
export DATABASE_URL='postgresql+psycopg://neondb_owner:<password>@<endpoint-id>.us-east-2.aws.neon.tech/neondb?sslmode=require'

# 2. Guarded one-time migration. Masks the target, refuses pooled/non-psycopg
#    URLs, requires exactly one head, upgrades, then verifies revision + tables.
cd /path/to/Cartel-Smart-Cart-Optimizer
infra/deployment/migrate_neon.sh

# 3. Clear the secret from the shell when finished.
unset DATABASE_URL
```

What the script does, in order:

1. Refuses to run if `DATABASE_URL` is unset, non-`postgresql+psycopg://`, or contains `-pooler`.
2. Prints a masked target (`neondb_owner:***@<host>:5432/neondb?sslmode=require`).
3. Runs `alembic heads` and requires exactly one `(head)` line.
4. Prints `alembic current` (empty before upgrade).
5. Runs `alembic -c alembic.ini upgrade head`.
6. Prints `alembic current` again.
7. Opens a verification connection, reads `alembic_version.version_num`, counts tables, checks the expected set, and fails if the revision is not `0009_credential_vault` or any expected table is missing.

Transaction semantics: `backend/app/db/migrations/env.py` wraps the online run in a single `context.begin_transaction()`. PostgreSQL DDL is transactional, so a failure at any migration step rolls back the **entire** run and leaves the database empty. The migrations are not run per-migration in separate transactions.

---

## 6. Expected output (masked)

```text
migration target: postgresql+psycopg://neondb_owner:***@<endpoint-id>.us-east-2.aws.neon.tech:5432/neondb?sslmode=require
repository head: 0009_credential_vault (head)
current revision before upgrade:
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_consumer_identity, ...
... (one line per migration) ...
INFO  [alembic.runtime.migration] Running upgrade 0008_retailer_connections -> 0009_credential_vault, ...
current revision after upgrade:
0009_credential_vault (head)
alembic_version=0009_credential_vault
table_count=18
missing_expected_tables=none
migration verification passed
```

Any other `alembic_version`, a `table_count` other than 18, a non-empty `missing_expected_tables`, a non-zero exit, or an error line is a **failure**. Stop and report; do not retry blindly, do not drop tables, do not recreate the database.

---

## 7. Post-migration verification — SELECT-only

Run these after the script reports success. None writes data.

### 7.1 Revision and table inventory

```sql
SELECT version_num FROM alembic_version;
-- expected: 0009_credential_vault

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
-- expected: 18 rows (17 application tables + alembic_version)
```

Expected 18 tables: `alembic_version`, `audit_events`, `background_jobs`, `credential_secrets`, `email_outbox_events`, `idempotency_records`, `identities`, `oauth_challenges`, `optimization_allocations`, `optimization_plans`, `optimization_requests`, `password_credentials`, `retailer_connections`, `sessions`, `shopping_list_items`, `shopping_lists`, `users`, `verification_challenges`.

### 7.2 Zero application rows (schema-only migration)

```sql
SELECT 'audit_events' AS t, count(*) FROM audit_events
UNION ALL SELECT 'background_jobs', count(*) FROM background_jobs
UNION ALL SELECT 'credential_secrets', count(*) FROM credential_secrets
UNION ALL SELECT 'email_outbox_events', count(*) FROM email_outbox_events
UNION ALL SELECT 'idempotency_records', count(*) FROM idempotency_records
UNION ALL SELECT 'identities', count(*) FROM identities
UNION ALL SELECT 'oauth_challenges', count(*) FROM oauth_challenges
UNION ALL SELECT 'optimization_allocations', count(*) FROM optimization_allocations
UNION ALL SELECT 'optimization_plans', count(*) FROM optimization_plans
UNION ALL SELECT 'optimization_requests', count(*) FROM optimization_requests
UNION ALL SELECT 'password_credentials', count(*) FROM password_credentials
UNION ALL SELECT 'retailer_connections', count(*) FROM retailer_connections
UNION ALL SELECT 'sessions', count(*) FROM sessions
UNION ALL SELECT 'shopping_list_items', count(*) FROM shopping_list_items
UNION ALL SELECT 'shopping_lists', count(*) FROM shopping_lists
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'verification_challenges', count(*) FROM verification_challenges;
-- expected: every count = 0
```

### 7.3 Key 0009 constraints

```sql
SELECT conname
FROM pg_constraint
WHERE conname IN (
  'ck_retailer_connections_blocked_metadata',
  'ck_retailer_connections_blocked_source',
  'ck_retailer_connections_blocked_category',
  'uq_retailer_connections_id_user',
  'uq_retailer_connections_id_user_retailer',
  'uq_credential_secrets_reference_version',
  'fk_credential_secrets_connection_owner_retailer'
)
ORDER BY conname;
-- expected: all 7 present
```

### 7.4 Key 0009 indexes

```sql
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'ix_credential_secrets_user_connection',
    'ix_credential_secrets_user_retailer',
    'ix_credential_secrets_reference_owner',
    'uq_credential_secrets_active_reference',
    'ix_retailer_connections_user_created',
    'ix_retailer_connections_user_retailer_status'
  )
ORDER BY indexname;
-- expected: all 6 present
```

`uq_credential_secrets_active_reference` is a partial unique index over active, non-deleted rows; its presence confirms the vault's one-active-version-per-reference rule.

### 7.5 `credential_secrets` shape

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'credential_secrets'
ORDER BY ordinal_position;
-- expected 18 columns: id, reference, version, user_id, connection_id,
-- retailer_id, secret_type, status, algorithm, key_version, nonce,
-- ciphertext, rotated_from_id, created_at, updated_at, superseded_at,
-- revoked_at, deleted_at
```

### 7.6 Connection security

```sql
SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid();
SHOW server_encoding;
SHOW client_encoding;
-- expected: ssl = t, server_encoding = UTF8
```

### 7.7 CLI cross-check

```bash
cd backend && alembic -c alembic.ini current
# expected: 0009_credential_vault (head)
```

Post-migration acceptance is all of: revision `0009_credential_vault`, 18 tables, zero application rows, all key constraints/indexes present, 18 `credential_secrets` columns, TLS on. Anything else → stop and report.

---

## 8. Rollback and recovery

### 8.1 Failure during the run (preferred, automatic)

Because the online run is a single transaction and PostgreSQL DDL is transactional:

- An error at any migration step aborts the transaction.
- The database returns to its pre-run state: **empty, `alembic_version` absent**.
- No partial schema remains and no manual cleanup is needed.
- Re-running after fixing the cause is safe because the start state is still empty.

This is the only rollback path that should be used before data exists.

### 8.2 `alembic downgrade` — available but restricted

Every migration (`0001`–`0009`) defines `downgrade()`, and the chain can step back revision by revision. Limits:

- `downgrade base` **drops all tables**, including any user data. It is destructive.
- Downgrades are only acceptable while the database is still empty (i.e. immediately after this migration, before any user signs up or any list/optimization row is written).
- **Do not** use drop/recreate of the database, schema, or role as a rollback. That destroys ownership, privileges, and audit history.

### 8.3 Neon instant restore

- Neon Free retains a change history window of **up to 6 hours** (point-in-time restore). It is branch-level.
- If a bad state appears within that window, restoring the `production` branch to a pre-migration timestamp returns it to empty.
- After 6 hours, the pre-migration state is no longer restorable through the Free window.

### 8.4 Manual snapshots — not used

Manual snapshots are billed at **$0.09/GB-month**, which breaks the ₹0/cardless constraint. They are **not** part of this plan. Recovery relies on transactional rollback plus the Free 6-hour instant-restore window.

### 8.5 Recovery decision table

| Situation | Action |
| --- | --- |
| Migration errors mid-run | Let the transaction roll back; verify empty; fix cause; re-run only after re-approval |
| Migration succeeds but verification fails, no data written | Inspect; if needed, `alembic downgrade` to the last good revision, or restore the branch; never drop/recreate |
| Migration succeeds, then a defect is found within 6 h, no real user data | Neon instant restore to pre-migration timestamp |
| Any real user data exists | Treat schema as **one-way**; fix forward with a new migration; restore/downgrade risks data loss and needs separate approval |
| More than 6 h later with no data and a bad schema | Fix forward with a new migration; snapshot/restore outside Free window is not available cardlessly |

**One-way warning:** once the first real account, session, list, or optimization row is written, downgrade and restore become data-destructive. From that point, schema changes must be forward-only migrations.

---

## 9. Stop conditions

Stop immediately and report — do not retry, drop, recreate, or "fix" by hand — if any of these occur:

1. Preflight is not `neondb` / `neondb_owner` / `18.6` / TLS on / `can_create_public = t`.
2. Any non-system table or row exists before the migration, or `alembic_version` is already present.
3. The host contains `-pooler`, the scheme is not `postgresql+psycopg://`, or TLS is absent.
4. `alembic heads` shows zero or more than one head, or the head is not `0009_credential_vault`.
5. The script exits non-zero, an error appears, or a migration step fails.
6. Post-migration `alembic_version` is not `0009_credential_vault`.
7. `table_count` is not 18 or any expected table is missing.
8. Any application table has a non-zero row count after migration.
9. Any key 0009 constraint or index is missing, or `credential_secrets` does not have 18 columns.
10. TLS is off, or encoding is not UTF8.
11. Neon presents a card requirement, paid activation, or any charge — including a manual snapshot prompt.
12. The task would require touching Render, Vercel, GitHub, DNS, OAuth settings, or Git history; those are separate approvals.

---

## 10. Approval disclosure — migration execution

Requesting approval for **exactly one** action: run `infra/deployment/migrate_neon.sh` (Alembic `upgrade head`) against Neon `neondb` over the **direct** endpoint.

| # | Disclosure | Detail |
| --- | --- | --- |
| 1 | **What** | Execute the 0001→0009 Alembic chain, creating 17 application tables plus `alembic_version` in the `public` schema of `neondb`. |
| 2 | **Where** | Neon Free, project `my-first-project`, branch `production`, region `aws-us-east-2`, direct host `<endpoint-id>.us-east-2.aws.neon.tech`, database `neondb`, role `neondb_owner`, TLS required. Masked URL only; no secret in chat or Git. |
| 3 | **Writes** | DDL only: `CREATE TABLE`, `CREATE INDEX`, `ALTER TABLE ... ADD COLUMN`, constraints. **No DML, no seeding, no user rows.** The database is currently empty; it will contain schema and zero application rows afterward. |
| 4 | **Free / cardless** | Uses the existing Neon Free plan and existing project. No new project, no paid plan, no card, no snapshot. If a card or charge appears, stop. |
| 5 | **Reversible** | A mid-run failure auto-rolls back to empty (single transaction, transactional DDL). After success with no data, `alembic downgrade` or a Neon instant restore (≤6 h window) can return to empty. Once real data exists, changes are forward-only. |
| 6 | **What remains after** | The database holds schema only. Render, Vercel, Redis, GitHub OAuth, seeding, and the hosted smoke test are **separate** approvals. Git is not modified. |

**Not authorized by this approval:** seeding or demo data, creating a second account, deploying Render/Vercel, configuring Upstash/Redis, changing OAuth callbacks, creating snapshots, any Git commit/push, or any paid action.

---

## 11. What was not done

- The assistant did not execute the migration; the approved script was run by the user out-of-band.
- No seeding, DML, or demo-data load was performed.
- No table, schema, role, project, or database was dropped or recreated.
- No snapshot, branch, or paid resource was created.
- No password, connection string, token, or API key was requested, printed, logged, or committed.
- No Render, Vercel, Upstash, GitHub, or DNS configuration was changed.
- No Git mutation was performed.

---

## 12. Execution record (2026-11-11)

The user executed `infra/deployment/migrate_neon.sh` against the Neon Free `neondb` database over the **direct** endpoint and reported success.

### 12.1 Confirmed by the user

| Check | Result |
| --- | --- |
| Target | Existing Neon Free `neondb`, **direct** (non-pooled) endpoint |
| Alembic revision | `0009_credential_vault` |
| Table count (17 application tables + `alembic_version`) | **18** |
| Missing expected tables | **none** |
| Script verification | **passed** |

These map to the script's own final assertions (`alembic_version=0009_credential_vault`, `table_count=18`, `missing_expected_tables=none`, `migration verification passed`). The revision and table count are therefore confirmed for this run.

### 12.2 Not provided — not yet verified

The following post-migration checks from §7 were **not** included in the reported output. They are **not confirmed** and must not be recorded as passing until the SELECT-only queries are run:

| Check | Status |
| --- | --- |
| Zero application rows across all 17 tables | **Not verified** |
| All 7 key 0009 constraints present | **Not verified** |
| All 6 key 0009 indexes present | **Not verified** |
| `credential_secrets` has 18 columns | **Not verified** |
| TLS active at query time (`pg_stat_ssl.ssl = t`) | **Unresolved** — `pg_stat_ssl.ssl=false` observed vs `sslmode=require` |
| `server_encoding = UTF8` | **Not verified post-migration** |
| `alembic current` CLI cross-check | **Not verified** |

The script verifies revision and table names only. It does not query row counts, constraints, indexes, columns, or TLS. The pre-migration live checks confirmed the database was empty and PG 18.6 with TLS required, but those were before the run.

**To close this gap**, run the SELECT-only block in §7 (7.1–7.7) and record the results. Until then the correct status is: schema migration confirmed at `0009_credential_vault` with 18 tables; row-emptiness, constraint/index/column presence, and TLS/encoding are outstanding. TLS is unresolved (`pg_stat_ssl.ssl=false` vs `sslmode=require`); do not treat it as verified.

### 12.3 Not performed (by design)

No seeding, no DML, no second migration run, no snapshot, no provider configuration, no deploy, and no Git operation. The migration is not re-run as part of recording this result.
