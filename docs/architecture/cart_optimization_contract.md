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
- explicit `inconvenience_penalty_units`;
- explicit `retailer_preference_priority`;
- feasibility state;
- unresolved components;
- provenance references.

Each requested item allocation must identify the canonical product variant, retailer/platform, checkout group, and effective-cost evaluation supporting it.

Candidate plans must not contain raw observations or independently recalculated costs.

`inconvenience_penalty_units` and `retailer_preference_priority` are explicit plan inputs. The optimizer must never derive either value from checkout count, retailer names, fees, or allocation shape. They are required plan attributes and participate in plan identity because changing either can change ranking or selection.

Each candidate plan must contain exactly one plan-level effective-cost evaluation linkage representing the complete plan cost. Checkout groups may retain contextual references, but the optimizer must not sum or otherwise aggregate multiple effective-cost results.

The optimizer consumes the supplied candidate-plan set. Candidate-plan generation, substitution generation, and split-cart enumeration are upstream responsibilities.

Effective-cost linkage validity is deterministic:

- zero linked evaluations: `INVALID`;
- exactly one valid linkage: eligible for plan validation;
- duplicate references: `INVALID`;
- multiple linked evaluations: `INVALID`;
- dangling linkage: `INVALID`;
- duplicate evaluation IDs in the request: request validation fails closed as `INVALID`.

Invalid linkage is a structural contract failure, not an unresolved business outcome. The linked result must have a known `effective_cost` and no decision-relevant unknown component for the plan to be `FEASIBLE`. A missing or unknown effective cost makes the plan `UNRESOLVED`. A plan declared `FEASIBLE` while its linked result is missing, unknown, or contains decision-relevant unknowns is `INVALID`.

All linked effective-cost results in one request must use the same currency. Currency mismatch makes the request `INVALID`; the optimizer must not convert currencies.

## Current Validation and Ownership Boundary

Cart Optimization independently validates the following executable input conditions:

- the optimization policy version is supported;
- candidate plan identities are present and unique;
- `INVALID` candidate-plan feasibility is rejected;
- request effective-cost evaluation IDs are unique;
- the plan-level effective-cost reference resolves;
- a `FEASIBLE` plan has a known linked effective cost;
- a `FEASIBLE` plan has no linked effective-cost unknown components;
- linked plan-level effective-cost currencies are consistent.

The semantic meaning of `FEASIBLE` remains the definition in this contract. The current Cart Optimization service does not independently prove every semantic condition represented by that state. Unless explicitly reassigned by a later contract decision, upstream candidate-plan responsibilities include:

- candidate-plan construction;
- split-cart enumeration;
- fulfillment construction;
- canonical Product and ProductVariant validation;
- unresolved dependency resolution;
- generation of the supplied feasibility state.

This boundary does not authorize upstream components to change the meaning of `FEASIBLE`, and it does not authorize Cart Optimization to infer unresolved structural policy.

## Fulfillment Semantics

Item-level split allocation is supported. A `CartItemRequest` may be represented by one or more `ItemAllocation` records. The logical request-item key is exactly the pair `(item_id, canonical_variant_id)`.

Every `FEASIBLE` candidate plan must fulfill every requested logical item. For each request-item key, the sum of matching allocation quantities must equal the corresponding `CartItemRequest.quantity`. An omitted item, under-allocation, or over-allocation cannot produce a `FEASIBLE` plan.

Each `ItemAllocation.quantity` must be a positive integer. Zero and negative allocation quantities are structurally invalid. Exact duplicate allocation records are structurally invalid; multiple non-identical allocations for one logical request item are valid intentional split allocations.

Quantity fulfillment uses integer arithmetic only. Cart Optimization does not introduce pack, consumer-unit, platform-unit, inventory, substitution, or quantity-conversion semantics.

Allocation identity, quantity fulfillment, and checkout-group ECE handling are
Cart Optimization contract concerns. Constraint-reference resolution and the
remaining semantic conditions represented by `FEASIBLE` remain outside this
frozen slice.

## Open Policy Decisions

The following decisions remain OPEN. No implementation rule may be inferred for them until the relevant policy is explicitly frozen:

Every `ItemAllocation.checkout_group_id` must match a declared `CheckoutGroup.checkout_group_id` within the same candidate plan. Every declared checkout group must contain at least one item allocation. Multiple non-identical item allocations may reference the same checkout group. `checkout_group_id` is authoritative for allocation membership within a candidate plan.

This membership rule does not define or validate `retailer_id` relationships. It does not resolve, compare, aggregate, require uniqueness for, or otherwise interpret checkout-group effective-cost evaluation IDs.

### Retailer allocation semantics

For MVP, `retailer_id` is an opaque optimization-domain identifier. It is not
defined as a platform, seller, marketplace, or execution capability.

`RetailerAllocation` is informational identity/provenance data. It is not
authoritative for `ItemAllocation` or `CheckoutGroup` membership.

Cart Optimization does not require:

- `ItemAllocation.retailer_id` to equal `CheckoutGroup.retailer_id`;
- `RetailerAllocation.retailer_id` to equal either allocation retailer ID;
- every item allocation to have a retailer allocation;
- every checkout group to have a retailer allocation.

Multiple checkout groups may share the same opaque `retailer_id`. Cart
Optimization does not derive, normalize, or validate retailer relationships.

This policy does not define constraint-reference resolution, hard-constraint
ownership, or checkout execution capability.

### Checkout-group effective-cost references

`CheckoutGroup.effective_cost_evaluation_id` is an opaque contextual
traceability reference. Cart Optimization does not resolve it against
`CartOptimizationRequest.effective_cost_evaluations`; missing or unresolved
group references do not independently affect optimization behavior.

Multiple checkout groups may share a group ECE ID. Group ECE IDs need not be
unique within a candidate plan and need not equal the plan-level
`effective_cost_evaluation_reference`.

Group ECEs have no independent economic authority. Only the plan-level ECE
represents complete plan cost and participates in ranking or cost comparison.
Group ECE IDs remain part of candidate-plan identity, but they are not
converted into `EvidenceReference` values or aggregated into
`CartOptimizationResult.provenance_references`.

### Constraint-reference and feasibility ownership

`CandidatePlan.constraint_references` are opaque upstream references. Cart
Optimization does not resolve them against `CartOptimizationRequest.constraints`.
Missing or unresolved references do not independently change optimization
behavior. Registry scope, duplicate-reference semantics, and lookup behavior
are outside this contract.

Hard-constraint evaluation is upstream-owned. Upstream supplies
`CandidatePlan.feasibility` as `FEASIBLE`, `INFEASIBLE`, or `UNRESOLVED`.
Cart Optimization consumes that classification and does not independently
evaluate `OptimizationConstraint` variants. It does not reinterpret supplied
feasibility except for the established structural fulfillment and plan-level
effective-cost validations.

The existing ranking and selection behavior remains based on the resulting
feasibility classification and the authoritative plan-level effective cost.

Existing fixtures and demos that omit allocations or use contextual checkout-group data are not evidence for resolving the remaining OPEN decisions. They must not weaken the contractual semantic requirements above and may require migration after the policies are frozen.

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

A plan is `INVALID` when its structure violates this contract, including invalid effective-cost linkage. `INVALID` is a structural validation state, not a business decision. An invalid request fails closed and must not produce a recommendation or optimization outcome.

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

The comparison uses the single linked plan-level effective cost. Effective-cost aggregation across multiple results is never permitted in Cart Optimization.

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

Unresolved candidate plans remain semantically distinct from infeasible plans.
They are excluded from `ranked_plan_ids`, are never represented in
`rejected_plans`, and cannot produce `chosen_plan`. No separate
`unresolved_plans` result field is used. When unresolved plans can affect the
decision, `OptimizationOutcome.UNRESOLVED` is authoritative. Their plan IDs
are preserved in deterministic `rationale`, and their unknown components are
preserved in `unknowns`. `RejectedPlan` is reserved for deterministically
infeasible plans.

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
- explicit plan-level ranking attributes;
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

For selected-plan listing and observation provenance, the authoritative
representation is `chosen_plan.item_allocations[*].listing_provenance`. Cart
Optimization does not convert `CandidateListingProvenance` into
`EvidenceReference`, add it to `CartOptimizationResult.provenance_references`,
or aggregate listing provenance from rejected or unresolved candidate plans.
`CartOptimizationResult.provenance_references` remains limited to its existing
`EvidenceReference` sources.

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

## CandidatePlan Construction Policy Gate

This section is an owner-facing decision package for the boundary between
persisted cart candidate discovery and CandidatePlan construction. It records
questions that are not established by the current contract or implementation.
It is not an implementation authorization. No default, fallback, or policy may
be inferred from the presence of a model field, a fixture, a demo, or current
permissive behavior.

The approved pipeline is:

```text
resolved cart
  -> persisted candidates
  -> candidate readiness/provenance
  -> [OWNER POLICY GATE]
  -> CandidatePlan construction
  -> plan-level economic evaluation
  -> Cart Optimization
```

### 1. Retailer identity

The existing contract defines `retailer_id` as an opaque optimization-domain
identifier. `platform` must not be treated as `retailer_id`.

Before CandidatePlan construction, the owner must approve:

- the domain entity that owns `retailer_id`;
- the authoritative source of the identifier;
- whether the identifier is attached to a persisted listing, observation,
  platform configuration, or another domain object;
- whether one platform may contain multiple retailer identifiers;
- whether one retailer may span multiple platforms;
- whether retailer identity is immutable for a persisted listing candidate;
- the behavior when retailer identity is unavailable.

Until approved, retailer identity is unavailable for plan construction unless
an upstream-approved source supplies it. No identifier namespace or platform
equivalence is introduced by this contract.

### 2. Checkout-group construction

Every `CheckoutGroup` requires:

- `checkout_group_id`;
- `retailer_id`;
- `effective_cost_evaluation_id`.

The existing membership policy remains authoritative: every allocation group
reference must match a declared group in the same plan, every declared group
must contain an allocation, and `checkout_group_id` is authoritative for
allocation membership. This section does not change that policy.

The owner must still approve the construction rule for:

- the grouping dimension and grouping key;
- whether platform participates in grouping;
- whether fulfillment or delivery context participates;
- whether different retailers may share a group;
- whether different platforms may share a group;
- whether one item may span groups;
- deterministic derivation of `checkout_group_id`;
- behavior when grouping context is unavailable.

No grouping rule may be derived from `retailer_id`, `platform`, checkout count,
or field-name similarity without that decision.

### 3. Candidate-to-plan enumeration

The owner must approve the enumeration semantics for:

- zero candidates for a cart item;
- exactly one candidate;
- multiple candidates;
- multiple candidates for one item;
- split allocations;
- combinations across candidates;
- elimination of equivalent plans.

The existing fulfillment contract permits split allocations, but it does not
select an enumeration strategy for persisted candidates. Candidate discovery
does not construct plans and does not imply that multiple candidates are
alternatives, splits, or combinations.

### 4. Typed-price-ineligible candidates

Candidate discovery distinguishes these states:

1. a persisted candidate exists;
2. the candidate has a valid typed observed selling price;
3. the candidate lacks a valid typed observed selling price.

Missing, malformed, or unsupported prices must not be fabricated, defaulted, or
silently converted. The owner must choose whether a price-ineligible candidate
is:

- excluded before allocation;
- retained as non-comparable preparation data;
- allowed to produce an unresolved plan;
- or handled by another explicitly defined policy.

The current readiness metadata records this condition but does not choose its
CandidatePlan meaning.

### 5. CandidatePlan identity and plan IDs

`CandidatePlanIdentityBuilder` is the existing identity authority. Its
identity-bearing inputs are:

- `plan_id`;
- `inconvenience_penalty_units`;
- `retailer_preference_priority`;
- retailer allocations;
- item allocations, including allocation quantities;
- checkout groups, including their identity-bearing ECE IDs;
- the plan-level effective-cost evaluation reference;
- constraint reference IDs.

Collections are canonically ordered before serialization. Listing provenance is
preserved on item allocations but is not independently identity-bearing where
the existing builder excludes it. No new hashing or plan identity scheme is
introduced here.

The owner must approve how newly enumerated plans receive `plan_id`. Until
approved, CandidatePlan construction must not generate plan IDs.

### 6. Feasibility handoff

The allowed feasibility states remain `FEASIBLE`, `INFEASIBLE`, `UNRESOLVED`,
and `INVALID`. Feasibility is upstream-owned. Cart Optimization consumes the
supplied classification and applies only the already-established structural
fulfillment and plan-level effective-cost validations.

The owner must specify:

- which component assigns feasibility;
- the evidence required for each state;
- whether a plan may be constructed before feasibility is assigned;
- how missing retailer identity, grouping context, typed price, or ECE inputs
  affect construction versus feasibility.

This section does not assign meanings to missing data and does not expand
Cart Optimization's feasibility responsibility.

### 7. Inconvenience penalty

`inconvenience_penalty_units` is a required explicit CandidatePlan attribute.
It participates in CandidatePlan identity and ranking. The optimizer does not
derive it from checkout count, retailer names, fees, or allocation shape.

The owner must approve its source, owner, default behavior, whether zero is
valid, whether it is user/configuration/planner/retailer/checkout-derived, and
when it becomes available.

### 8. Retailer preference

`retailer_preference_priority` is a required explicit CandidatePlan attribute.
It participates in CandidatePlan identity and ranking. Its preference direction
and source are not inferred from platform names or lexical ordering.

The owner must approve its source, owner, default behavior, whether lower or
higher values are preferred under ranking, whether it is user-specific,
global, metadata-derived, or planner-derived, and when it becomes available.

### 9. Economic evaluation handoff

The established lifecycle is:

```text
candidate discovery/readiness
  -> CandidatePlan construction
  -> plan-level Effective Cost Evaluation
  -> CandidatePlan.effective_cost_evaluation_reference
  -> CartOptimizationRequest
  -> Cart Optimization
```

CandidatePlan stores an `EffectiveCostEvaluationReference`, not an embedded
evaluation. The plan-level ECE is the economic authority. Checkout-group ECEs
remain contextual and are never aggregated into plan cost. Cost Intelligence
owns ECE calculation.

The owner must approve:

- which component creates one ECE per plan;
- the required ECE inputs;
- whether every plan receives an ECE;
- whether infeasible plans receive ECEs;
- failure behavior;
- how the reference is attached to the plan.

This gate does not modify Cost Intelligence or plan-level ECE validation.

### 10. Implementation gate

| Decision | Current contract | Owner decision required | Required upstream data | Blocked implementation area |
|---|---|---|---|---|
| retailer identity | Opaque identifier; platform is not retailer identity | Owner/source/scope/unavailable behavior | Approved retailer identifier on or linked to candidate data | CandidateItemAllocation and CheckoutGroup construction |
| checkout grouping | Membership references are frozen; construction dimension is not | Grouping key, context, cross-retailer/platform rules, unavailable behavior | Approved grouping context and deterministic derivation inputs | CheckoutGroup and allocation construction |
| zero candidates | Candidate discovery reports explicit no-candidate state; plan meaning is not frozen | Unresolved, infeasible, invalid, or excluded behavior | Approved zero-candidate policy | CandidatePlan enumeration |
| one candidate | Candidate discovery preserves one candidate; plan consequence is not frozen | Whether one candidate necessarily yields a plan | Required plan attributes and feasibility evidence | CandidatePlan enumeration |
| multiple candidates | Candidate discovery preserves deterministic candidates; alternative/split semantics are not frozen | Alternatives, splits, combinations, and equivalence rules | Enumeration policy and complete candidate data | CandidatePlan enumeration |
| split allocation | Fulfillment permits split allocations; persisted-candidate enumeration is not defined | Split eligibility, quantity distribution, and equivalence rules | Approved allocation policy | ItemAllocation/CandidatePlan construction |
| plan identity | Existing builder and identity fields are frozen | Assignment convention for newly generated `plan_id` | Deterministic plan identity inputs | CandidatePlan construction |
| feasibility | States and upstream ownership are frozen | Assigning component and evidence for generated plans | Feasibility evidence and unresolved-dependency policy | CandidatePlan construction/handoff |
| inconvenience | Required explicit identity/ranking input; derivation is prohibited | Source, default, zero, owner, availability | Penalty value for each plan | CandidatePlan construction |
| retailer preference | Required explicit identity/ranking input; lexical derivation is prohibited | Source, default, direction, owner, availability | Priority value for each plan | CandidatePlan construction |
| plan-level ECE | Reference is required by CandidatePlan; Cost Intelligence owns calculation | Creator, inputs, coverage, failure, attachment | ECE result/reference per policy | ECE handoff and CartOptimizationRequest construction |

Until the blocked decisions and required upstream data are approved, the
implementation gate remains closed. No CandidatePlan, CandidateItemAllocation,
ItemAllocation, CheckoutGroup, CartOptimizationRequest, or Effective Cost
Evaluation is constructed from persisted discovery candidates by this boundary.

## Frozen Boundary

Cart Optimization is implementation-ready under this contract. It is a deterministic decision layer over supplied candidate plans and structured Effective Cost Evaluation results. It does not replace or extend Product Intelligence, Cost Context, evaluator, review, assertion, or persistence responsibilities.
