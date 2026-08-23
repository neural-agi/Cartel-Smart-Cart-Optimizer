# Planning Persistence Contract Gap

## Scope

This document records the planning persistence boundary that is supported by
the current Cart Optimization models and repository conventions. It does not
define a planning lifecycle, workflow, retention policy, or API persistence
behavior.

## Authoritative Semantics

- `CartPlanningRequest.request_id` is the request identity.
- `CartOptimizationResult.optimization_id` is the result identity.
- `CartOptimizationResult.request_id` preserves request correlation.
- Both models are immutable Pydantic contracts and already have deterministic
  JSON serialization through `CartPlanningSerialization`.
- Existing filesystem stores establish idempotent identical writes, conflict
  rejection, atomic replacement, model validation on read, and missing-record
  lookup behavior.

The planning repositories apply these semantics independently:

- requests are keyed by `request_id`;
- results are keyed by `optimization_id`;
- identical identity and payload is an idempotent replay;
- different payload under the same identity fails closed;
- malformed stored payloads fail closed;
- missing records return `None`.

## Derivable Boundaries

- Request and result records can be stored independently without changing
  either domain model.
- A result retains its request correlation through its existing `request_id`.
- Persistence must not generate IDs, add timestamps, mutate payloads, or
  recalculate optimization output.
- Existing serialization is the sole payload encoding boundary.

## Undefined Decisions

The repository does not define:

- whether a request is an input snapshot, an execution record, or both;
- whether one request may have multiple results;
- ordering or versioning for multiple results under one request;
- request/result atomicity;
- planning lifecycle or status states;
- retry ownership and retry identity;
- retrieval by request ID;
- retention, deletion, or expiration;
- persistence ownership and access control;
- automatic persistence from `/api/v1/cart/plan`;
- API retrieval of persisted planning records.

## Implementation Boundary

Independent request and result repositories are safe and implemented using
the semantics above. A coherent planning persistence workflow must not be
added until the undefined decisions are explicitly frozen. In particular,
the existing repositories must not be interpreted as defining a one-to-one
request/result relationship or automatic API persistence.

## Explicit Non-Goals

This boundary does not add lifecycle states, timestamps, TTLs, retries,
deletion, database tables, background jobs, new endpoints, or feasibility
evidence fields on `CandidatePlan`.
