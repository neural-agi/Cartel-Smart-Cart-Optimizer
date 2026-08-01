# Cart Optimization Contract

## Status

This document is the canonical behavioral contract for Cart Optimization. It freezes the observable boundary between Effective Cost Evaluation and future cart decision-making.

Cart Optimization is not implemented by this document.

## Responsibility

Cart Optimization is the first layer permitted to compare alternatives and select a preferred plan.

It may:

- compare immutable candidate plans;
- apply explicit optimization constraints;
- rank feasible alternatives;
- select a plan when recommendation conditions are satisfied;
- preserve rationale, unknowns, assumptions, and provenance.

It must not:

- parse raw checkout, offer, fee, or membership text;
- perform product or variant matching;
- perform normalization;
- evaluate offers, fees, or memberships;
- recalculate effective cost;
- update canonical assertions;
- invent substitutions or candidate plans;
- silently estimate unknown values.

## Dependency Direction

```text
Product Intelligence
        ↓
Checkout Observation / Cost Context
        ↓
Offer, Fee, Membership Evaluation
        ↓
Effective Cost Evaluation
        ↓
Candidate Plan Set + Coverage Declaration
        ↓
Cart Optimization
```

Cart Optimization consumes structured outputs from upstream components. It does not call those components or duplicate their rules.

## CartOptimizationRequest

The request is immutable and contains:

- `request_id`: deterministic request identity;
- `optimization_policy_version`: explicit policy version supplied by the caller;
- canonical requested cart items and quantities;
- immutable candidate plans;
- candidate-plan coverage declaration;
- linked effective-cost evaluation results;
- explicit optimization constraints;
- provenance references.

The request must not duplicate raw observations, interpreted evaluator inputs, canonical product definitions, review state, assertion state, or calculated effective-cost values outside their owning models.

`optimization_policy_version` is required. It must not be obtained from configuration, environment variables, globals, module constants, timestamps, or hidden defaults. Missing, malformed, or unsupported policy versions fail closed.

## CandidatePlan

A candidate plan is an immutable aggregate containing:

- deterministic `plan_id`;
- retailer/platform allocations;
- canonical item allocations;
- checkout grouping;
- links to effective-cost evaluations;
- links to applicable constraints;
- feasibility state;
- unresolved components;
- provenance references.

Each requested item allocation must identify the canonical product variant, retailer/platform, checkout group, and effective-cost evaluation supporting it.

Candidate plans must not contain raw observations or independently recalculated costs.

The optimizer consumes the supplied candidate-plan set. Candidate-plan generation, substitution generation, and split-cart enumeration are upstream responsibilities.

## CandidatePlanCoverage

Coverage is an immutable declaration describing completeness for a declared optimization scope.

Canonical states:

- `COMPLETE`: every candidate plan permitted by the declared scope and constraints has been generated and validated;
- `PARTIAL`: the candidate set is known to omit one or more plans within the scope;
- `UNKNOWN`: completeness cannot be established;
- `INVALID`: the declaration is malformed, contradictory, or lacks required metadata.

Coverage is qualified and validated upstream. The optimizer must never infer coverage from candidate count, ordering, or feasibility.

Required coverage fields:

- `state`;
- `scope_reference`;
- `candidate_set_reference`;
- `coverage_basis`;
- `validation_reference`.

`COMPLETE` requires valid values for all required fields. Other states require deterministic rationale explaining the limitation or failure.

## Constraints

Initial supported constraint categories are:

- budget;
- retailer preference;
- maximum checkout groups;
- inconvenience penalty;
- delivery preference;
- substitution policy;
- membership preference.

Each constraint is explicit and immutable. It must define whether it is hard or soft and how missing information affects feasibility.

The optimizer must not infer preferences from retailer names, fee values, plan shape, or presentation order.

## Feasibility

A plan is `FEASIBLE` only when:

- all requested quantities are fulfilled;
- every allocation has valid canonical product and variant identity;
- required checkout evaluations exist;
- required payable cost components are known;
- all hard constraints are satisfied;
- no decision-relevant product, variant, availability, fee, offer, or membership dependency is unresolved.

A plan is `INFEASIBLE` when a requirement or hard constraint is deterministically disproven.

A plan is `UNRESOLVED` when feasibility cannot be proven because required information is unknown.

Unknown availability, fees, offers, memberships, or payable costs must never be treated as zero, false, or absent.

Only feasible plans may be selected.

## Ranking

Ranking is deterministic and lexicographic:

1. feasible plans before unresolved and infeasible plans;
2. lower known effective cost;
3. fewer checkout groups;
4. lower explicit inconvenience penalty;
5. higher explicit retailer-preference priority;
6. lower canonical `plan_id`.

Relative ranking does not change the candidate coverage state. Ranking available candidates under incomplete coverage is descriptive only.

No hidden heuristic, insertion-order behavior, or implicit preference is permitted.

## Recommendation

The result contains both the descriptive ranking and a recommendation when permitted.

A `chosen_plan` may be produced only when:

- coverage is `COMPLETE`;
- at least one plan is feasible;
- no unresolved plan can affect the decision;
- all hard constraints are satisfied;
- the selected plan is the highest-ranked feasible plan.

For `PARTIAL`, `UNKNOWN`, or `INVALID` coverage:

- `chosen_plan_id` must be `None`;
- available plans may be ranked for diagnostics;
- the result must preserve coverage state and rationale;
- no plan may be presented as globally optimal.

If all candidates are infeasible, the optimization outcome is `INFEASIBLE`. If decision-relevant uncertainty remains, the outcome is `UNRESOLVED`.

## Split Carts

Single-cart plans must be included by the upstream candidate-plan generator whenever they are within scope.

Split-cart plans may be supplied up to the explicit `maximum_checkout_groups` constraint. The optimizer does not generate additional split combinations.

Every checkout group remains individually traceable to its effective-cost evaluation and provenance.

## Identity

### Request identity

Request identity includes:

- canonical cart item identities and quantities;
- canonical candidate-plan identities;
- canonical constraint values;
- linked effective-cost evaluation identities;
- `optimization_policy_version`.

It excludes timestamps, formatting, rationale, metadata, and presentation order.

### Candidate-plan identity

Plan identity includes:

- canonical item allocations;
- retailer/platform identifiers;
- checkout grouping;
- effective-cost evaluation identities;
- constraint-relevant plan attributes.

Allocations are canonically ordered by product variant identity, retailer/platform identity, and checkout group identity.

### Chosen-plan identity

The chosen plan uses the candidate plan identity. Selection status is metadata and does not alter plan identity.

### Optimization-result identity

`optimization_id` includes:

- request identity;
- canonical ordered candidate-plan identities;
- canonical ordered evaluation identities;
- `optimization_policy_version`.

It excludes totals, unknown labels, rationale, timestamps, formatting, and iteration order.

## Result Contract

`CartOptimizationResult` is immutable.

Required fields:

- `optimization_id`;
- `request_id`;
- `outcome`;
- nullable `chosen_plan_id`;
- nullable `chosen_plan`;
- rationale;
- unknowns;
- assumptions;
- provenance references.

Optional fields:

- ranked plan identifiers;
- retained alternative plans;
- rejected plans;
- deterministic rejection reasons.

Rejected and unresolved plans must retain their reasons. Unknowns must not disappear because a plan was not selected.

## Provenance

Optimization outputs must preserve links to:

- effective-cost evaluation identifiers;
- Cost Context identifiers;
- Checkout Observation evidence references;
- Product and ProductVariant assertions;
- platform listings and listing observations;
- matching and review decision references where applicable.

Provenance is merged by exact identity while preserving canonical first-seen order. The optimizer may aggregate provenance but must not reinterpret or discard it.

## Replayability

Given identical:

- immutable request inputs;
- candidate plans;
- coverage declaration;
- effective-cost results;
- constraints;
- optimization policy version;
- rule definitions;

independent implementations must produce identical:

- plan feasibility states;
- plan ordering;
- chosen plan;
- optimization outcome;
- rationale and rejection reasons;
- unknowns and assumptions;
- provenance ordering;
- serialized result;
- optimization identity.

The implementation must not depend on clocks, randomness, global state, hidden configuration, insertion order, or mutable storage.

## Frozen Boundary

Cart Optimization is implementation-ready under this contract. It is a deterministic decision layer over supplied candidate plans and structured Effective Cost Evaluation results. It does not replace or extend Product Intelligence, Cost Context, evaluator, review, assertion, or persistence responsibilities.
