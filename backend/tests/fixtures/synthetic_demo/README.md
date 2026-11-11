# Cartel Demo synthetic journey fixture dataset

This directory is the deterministic **synthetic** dataset used by the
consumer-journey browser test and local demo mode. It is generated from the
retailer-independent `CARTEL_DEMO` source. It is not live retailer evidence and
must never be presented as live.

## Provenance

Generated with the synthetic seed path:

```bash
cd backend
DATA_DIR=../backend/tests/fixtures/synthetic_demo \
APP_ENV=development \
python3 -m app.dev.seed_synthetic_demo_cart
```

Every record is marked with:

- `platform: "CARTEL_DEMO"`;
- `parser_version` / `normalization_version`: `synthetic-v1`;
- `source_reference`: `synthetic://cartel-demo/<listing>`;
- completeness basis `synthetic-demo-catalog-v1`.

The live-evidence gate (`has_supported_retailer_evidence`) rejects this source.
Only an application started with `DEMO_FIXTURES_ENABLED=true` exposes it, and it
does so with `evidence_state` / `evidence_class` `synthetic_demo`.

The same generator is used for runtime demo data under `data/demo_catalog`, but
the two dataset roots are intentionally separate so test fixtures never become
runtime demo data by accident.

## Contents

Four product families, each with two exact pack-size variants and two synthetic
listings per variant:

| Product | Variants | Availability coverage |
| --- | --- | --- |
| Cartel Demo Toned Milk | 500 ml, 1 l | available / unavailable |
| Cartel Demo Whole Wheat Atta | 1 kg, 5 kg | available / unknown |
| Cartel Demo Basmati Rice | 1 kg, 5 kg | unavailable / available |
| Cartel Demo Sunflower Oil | 1 l, 2 l | available / unknown |

There are no checkout captures, fees, taxes, discounts, serviceability records,
or correlated ECE records. A synthetic optimization therefore returns
`unresolved`/`partial` with observed synthetic product prices and an explicit
statement that fees, taxes, serviceability, and checkout totals are unknown. It
never asserts savings, a payable amount, or an order instruction.

## Reproducing the browser journey

From the repository root:

```bash
python3 scripts/e2e/run_consumer_journey.py
```

The harness builds the current frontend, starts a disposable Redis/API/frontend
stack on the isolated Docker network against `cartel_test`, copies this fixture
root to the container data directory, and runs
`backend/tests/e2e/test_consumer_journey_browser.py`. It reads the test password
from `$HOME/.cartel-test-secrets/cartel-test-secret` by default and never targets
the `cartel` database. Pass `--skip-frontend-build` to reuse an existing
`cartel-e2e-frontend:local` image.
