# Cartel Shipping Strategy & Deployment Sprint

**Version:** 1.0  
**Effective:** 2026-09-30  
**Status:** Frozen operating baseline

## 1. Strategy Overview

Cartel has reached the point where additional pre-deployment perfection has diminishing value. Development now optimizes for reaching a usable deployed product, validating the complete user journey, and using real-world feedback to drive subsequent fixes.

- **Primary objective:** deploy a usable Cartel product.
- **Secondary objective:** gather real-world feedback and defects.
- **Not the objective:** achieve zero bugs before deployment.

The release scope must match verified capabilities. A deployment may proceed without every planned retailer integration, but it must not claim checkout-derived results where authoritative checkout evidence is unavailable.

## 2. Current Project Position

This is a repository-based baseline, not a guarantee that every capability is reachable in every deployment environment.

- Core product, catalog, candidate-discovery, cart-planning, and optimization architecture is implemented.
- The automatic planning API and frontend integration exist; the repository includes API integration coverage for success and explicit failure states.
- Cost Intelligence and checkout-derived effective-cost evaluation are implemented. Live checkout evidence is a separate dependency and remains blocked by retailer access/cart-evidence limitations.
- MVP persistence uses filesystem-backed application stores and registries. Deployment durability, backup, capacity, and operational behavior still require validation in the target environment.
- Blinkit product acquisition is implemented and documented as operational. Actual reachability can vary by environment; this does not establish live checkout capture.
- The frontend is substantially implemented. Production build/deployment validation remains outstanding.
- Production deployment has not yet been completed.
- Health and readiness routes exist and must be exercised against the chosen deployment configuration.

At the time this document was prepared, the worktree was clean on `main`; pytest collected 636 tests. The README still reports 627 automated tests. Collection is not a passing test result; release reporting must use the results from the release candidate's actual validation run and correct stale metrics separately.

Live retailer access restrictions are an external integration dependency. They must not stall deployment of unrelated, verified functionality. The deployed product must represent unavailable retailer capabilities honestly.

## 3. New Development Philosophy

### 3.1 Ship first, iterate second

Use this operating loop:

**Implement -> validate critical behavior -> deploy -> observe -> create issues -> fix.**

Prefer the smallest change that establishes a usable, safe workflow. Preserve established architecture and contracts. Do not expand architecture or refactor stable areas without a concrete release need.

### 3.2 Bounded imperfection is acceptable

The following may be deferred when they do not violate a release invariant or make the advertised core workflow unusable:

- cosmetic defects and UX rough edges;
- incomplete non-critical edge cases;
- non-critical performance issues;
- convenience features and incomplete retailer coverage;
- minor test gaps outside critical behavior;
- operational improvements that have a safe interim procedure.

Record deferred work as actionable issues with impact, reproduction details, and a proposed priority.

### 3.3 Trust-breaking defects are not acceptable

Do not deploy with known defects that can cause fabricated prices or savings, incorrect checkout-cost semantics, credential/session leakage, cross-user or cross-request data contamination, unauthorized retailer mutation, persistent-data corruption, false-success messaging, unsafe fallback behavior, or a security boundary violation.

## 4. Definition of Deployable

Cartel is deployable when the selected release scope meets all of these conditions:

**Backend**

- The application starts using documented deployment configuration.
- Health and readiness endpoints return the documented results.
- Required API routes operate through the real application composition.
- Configured persistent storage can be read and written, and its deployment limitations are understood.
- Configuration and secrets are supplied through the intended environment mechanism, not source code or logs.
- Critical invalid, unavailable, unresolved, and access-denied paths fail honestly and safely.

**Frontend**

- The production application builds and starts in the target environment.
- A user can access the application and complete the supported cart, optimize, and result/error flows.
- Backend communication works with deployment URLs, CORS, and authentication/security settings as configured.
- Failure and unavailable states are distinguishable from a selected optimization result.

**System**

- The supported **Frontend -> Backend -> Planning -> Optimization** journey works as one deployed system.
- No financial result is fabricated from listing data when checkout evidence is missing.
- No known critical security issue or data-corruption issue remains.

Deployment does not require all planned retailer integrations. It does require that release messaging and UI accurately describe which retailer-dependent results are verified, unavailable, or not implemented.

## 5. Critical Path to Deployment

Proceed in this order. Do not turn the path into a broad architecture roadmap.

1. **Git/rebase cleanup:** resolve any active rebase; review the final diff; create small logical commits. Acceptance: clean, understood branch state with no accidental artifacts.
2. **Backend production validation:** verify configuration, startup, readiness, API contracts, persistence behavior, and critical failure paths in a production-like environment. Acceptance: documented commands and passing release-relevant backend checks.
3. **Frontend production validation:** run lint, typecheck, production build, and startup using deployment configuration. Acceptance: application loads and communicates with the backend; environmental failures are distinguished from code failures.
4. **Full user-journey validation:** exercise cart entry through optimization and result/error presentation. Acceptance: selected, unresolved, and unavailable outcomes are shown correctly; no checkout-derived financial claim appears without checkout evidence.
5. **Deployment environment:** configure secrets, storage, networking, health checks, logs, backups/retention, and rollback procedure. Acceptance: configuration is explicit and smoke-testable; no development-only fixture/provider is enabled.
6. **Deploy:** deploy the agreed scope. Acceptance: deployment completes with no known P0 issue.
7. **Smoke test:** exercise health/readiness and the highest-value supported user path. Acceptance: live deployment behavior matches the validated release candidate; failures are observable and honest.
8. **First real users:** release to a controlled initial audience where practical. Acceptance: feedback and operational issues have an owner and are recorded for triage.

## 6. Retailer Strategy

**Primary principle:** an externally blocked retailer integration must not stall unrelated deployment work. Never bypass retailer security, authentication, anti-bot, or access controls.

Label each retailer capability accurately:

- **SUPPORTED + VERIFIED:** the intended capability has been exercised successfully in a relevant runtime and its evidence/limitations are known.
- **SUPPORTED + ENVIRONMENT-BLOCKED:** the integration is implemented, but the current environment prevents validating or reaching it. Do not describe it as currently operational in that environment.
- **IMPLEMENTED + RETAILER-BLOCKED:** application integration exists, but retailer-side access, required evidence, or behavior prevents the operation from completing. Fail closed and identify the limitation.
- **NOT YET IMPLEMENTED:** no complete integration exists. Do not imply support based on shared models, test fixtures, or planned work.

These labels apply to individual capabilities, not to Cartel as a whole. For example, product acquisition may be available while checkout capture remains blocked. Do not conflate listing observations with checkout evidence.

## 7. Bug Policy

- **P0 - Release blocker:** security/privacy breach, fabricated financial output, false success, cross-user contamination, data corruption, unauthorized retailer mutation, or core failure with no safe behavior. Stop release and fix or remove the affected capability from scope.
- **P1 - Serious post-deployment issue:** a major workflow or user segment is impaired, but deployment remains safe because scope is limited, a clear workaround exists, or the capability can be honestly marked unavailable. Assign an owner and near-term follow-up.
- **P2 - Normal bug:** localized functional defect with limited impact and no invariant violation. Record and prioritize against user impact.
- **P3 - Polish:** cosmetic, convenience, or low-impact UX improvement. Record for later iteration.

Severity is based on impact and trust, not implementation effort. Reclassify when new evidence changes the impact.

## 8. Issue-First Development

For every discovered issue:

1. Record the observed behavior, reproduction steps, affected scope, and evidence.
2. Assign P0-P3 and identify whether it violates a non-negotiable invariant.
3. If P0, stop the affected release path and fix it or remove that capability from the release.
4. If deployment remains safe, create/update the issue with an owner or priority and continue the critical path.
5. Revisit priority when user feedback, frequency, or impact changes.

Finding a bug is not by itself a reason to stop all work. The decision is whether it makes the current release unsafe, dishonest, or unusable for its declared scope.

## 9. Codex/Agent Operating Rules

**Before deployment:** inspect the relevant code and current worktree; preserve unrelated changes; implement the smallest necessary change; run focused tests first and broader validation when practical; report verified behavior, failures, and environmental blockers. Stop when the requested slice is complete. Avoid speculative architecture work, unrelated cleanup, and broad refactoring.

**After deployment:** work in issue-sized slices: **issue -> inspect -> implement -> validate affected behavior -> report**. Use production feedback to choose work. Keep changes scoped, preserve established contracts, and do not expand a fix into unrelated redesign.

Agents must not claim a capability is verified without executing the relevant path. They must distinguish code/test evidence from live deployment evidence and must not fabricate retailer data or bypass retailer controls.

## 10. Validation Policy

**Before deployment:**

- Run focused tests for changed behavior and integration tests for critical boundaries.
- Run the relevant backend suite and frontend lint/typecheck/build for the release candidate; record what ran and the result.
- Exercise startup, health/readiness, configured storage, and the end-to-end supported user journey in a production-like environment.
- Test representative failure states, including unavailable external dependencies.
- Run security/configuration checks appropriate to the deployment and review logs/responses for secret or PII leakage.
- Record environmental blockers separately; do not disguise them as code success. If a required validation cannot run, explicitly assess the risk and obtain a release decision rather than claiming it passed.

**After deployment:**

- Smoke-test the deployed build and critical path.
- Monitor errors, availability, and user-reported failures at a level appropriate to the release.
- Add regression coverage when fixing user-impacting or invariant-related defects.
- Do not require exhaustive speculative edge-case coverage before shipping a bounded, safe release.

## 11. Deployment Definition of Done

A deployment is complete only when all applicable items are checked:

- [ ] Release scope and known retailer limitations are documented for operators and users.
- [ ] No known P0 defect remains in the deployed scope.
- [ ] Backend and frontend production startup/build checks passed or an explicit release exception is recorded.
- [ ] Health/readiness and API smoke tests pass in the target environment.
- [ ] The supported user journey and honest failure states have been exercised.
- [ ] Production configuration uses no test fixture, demo provider, or development seed path.
- [ ] Secrets are managed outside source and are not exposed in responses or logs.
- [ ] Storage, persistence limits, backup/retention expectations, and rollback procedure are understood.
- [ ] Monitoring/log access and an operational contact/owner are established.
- [ ] Deferred issues are recorded with severity and next action.
- [ ] The deployed version and smoke-test result are recorded.

## 12. Post-Deployment Loop

Use a short feedback loop:

**Observe real usage -> capture the issue -> classify severity -> fix P0/P1 promptly -> schedule P2/P3 by impact -> validate the fix -> release -> observe again.**

Real user behavior, production telemetry, and reproducible reports become a higher-value source of direction than speculative pre-deployment perfection. Protect privacy: collect only the operational data needed to diagnose and improve the product.

## 13. Deferred Work

The following may remain outside the first deployment when the released scope works safely without them:

- live checkout capture for a retailer whose access/evidence boundary is blocked;
- additional retailer integrations and broader retailer coverage;
- cosmetic polish, minor UX refinements, and convenience features;
- non-critical performance optimization and scaling work;
- low-risk edge-case coverage and minor test gaps;
- operational automation that can initially be handled by a documented safe procedure.

Deferred does not mean forgotten: track work with impact and revisit it using real feedback. Do not defer an invariant violation, a critical security issue, a data-integrity risk, or a capability required for the specific release claims. If live checkout evidence is absent, do not advertise checkout-derived totals or savings as verified.

## 14. Non-Negotiable Invariants

These invariants apply before and after deployment:

- **Checkout-derived financial truth:** checkout cost, totals, fees, discounts, and savings claims must come from authoritative checkout evidence and established Cost Intelligence semantics. Listing prices are not checkout totals. Missing evidence remains unknown; it is never silently changed to zero or an estimate.
- **Provenance:** financial and retailer observations retain their source/evidence references. Data from test fixtures is not production evidence.
- **Request/plan correlation:** request identity and plan identity remain distinct. Checkout evidence is correlated using the established request+plan ownership; no cross-request or plan-only fallback is allowed.
- **Fail closed:** missing, invalid, conflicting, or unavailable authority must not be replaced with inferred/default data or a fabricated success.
- **Honest outcomes:** only a selected optimization result is success/ready. Unresolved and unavailable remain distinguishable in API and UI behavior.
- **Security and privacy:** credentials, session state, payment data, and customer PII are protected and excluded from unsafe logs/responses. No cross-user/request contamination.
- **Authorized retailer interaction:** do not submit unauthorized mutations, place orders, or bypass retailer access/security controls.
- **Data integrity:** persistence must not silently overwrite or corrupt evidence. Recovery and operational actions must respect the established storage contract.
- **Contract stability:** preserve established identity, feasibility, enumeration, ranking, ECE, and provenance semantics. Change them only through an explicit, reviewed contract decision required by a concrete product need.
