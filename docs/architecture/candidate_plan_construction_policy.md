# CandidatePlan Construction Policy

## Status

**Owner approval required.** This document is a decision record for the
boundary between persisted candidate discovery and CandidatePlan construction.
It does not authorize runtime implementation until the required decisions and
data are approved.

The authoritative baseline for already-frozen Cart Optimization behavior is
[`cart_optimization_contract.md`](cart_optimization_contract.md). This record
captures only the additional decisions needed to cross the CandidatePlan
construction boundary.

## Frozen

The following behavior is already frozen by the Cart Optimization contract and
is not reopened here:

- persisted candidate discovery is deterministic and preserves listing and
  observation provenance;
- candidate readiness distinguishes allocation-ready candidates from
  candidates with missing or unsupported typed observed selling prices;
- `retailer_id` is opaque and `platform` must not be treated as
  `retailer_id`;
- `checkout_group_id` is authoritative for allocation membership within a
  CandidatePlan;
- item-level split allocation and integer fulfillment rules are frozen;
- `CandidatePlanIdentityBuilder` is the identity authority;
- feasibility remains one of `FEASIBLE`, `INFEASIBLE`, `UNRESOLVED`, or
  `INVALID`, with upstream ownership as defined by the contract;
- plan-level Effective Cost Evaluation is the economic authority;
- group Effective Cost Evaluation references are contextual and are not
  aggregated into plan cost or result-level `EvidenceReference` provenance;
- no candidate discovery endpoint constructs CandidatePlan or invokes Cart
  Optimization.

## Owner Decision Required

### A. Retailer identity

Approve the:

- owning entity and authoritative source of `retailer_id`;
- attachment point for the identifier;
- policy for one platform mapping to multiple retailers;
- policy for one retailer spanning multiple platforms;
- immutability requirements;
- behavior when retailer identity is unavailable.

`platform` is not an acceptable implicit source. No namespace or equivalence
may be invented during implementation.

### B. Checkout groups

Approve the:

- grouping dimension and grouping key;
- role of platform in grouping;
- role of fulfillment and delivery context;
- cross-platform and cross-retailer rules;
- behavior when one item spans multiple groups;
- deterministic derivation of `checkout_group_id`;
- behavior when grouping context is unavailable.

Each constructed `CheckoutGroup` must still contain
`checkout_group_id`, `retailer_id`, and `effective_cost_evaluation_id`, but
this document does not select how those values are derived.

### C. Candidate enumeration

Approve the behavior for:

- zero candidates;
- one candidate;
- multiple candidates for one item;
- alternatives versus allocations;
- combinations across items and candidates;
- split allocations;
- equivalent-plan elimination;
- deterministic enumeration and ordering.

Candidate count must not be treated as plan count without this decision.

### D. Typed-price eligibility

Approve the treatment of candidates with:

- a missing typed observed selling price;
- an unsupported currency;
- a malformed price.

The choice must explicitly state whether such candidates are excluded before
allocation, retained as preparation data, permitted in `UNRESOLVED` plans, or
handled by another policy. Prices must never be fabricated, defaulted, or
silently reparsed.

### E. Plan identity

`CandidatePlanIdentityBuilder` remains authoritative. Its existing
identity-bearing inputs include:

- `plan_id`;
- `inconvenience_penalty_units`;
- `retailer_preference_priority`;
- retailer allocations;
- item allocations and quantities;
- checkout groups and identity-bearing group ECE IDs;
- the plan-level ECE reference;
- constraint reference IDs.

Canonical collection ordering and listing-provenance exclusion follow the
existing builder and contract. Approve the owner, deterministic generation
convention, and collision behavior for newly assigned `plan_id` values. No
new hashing scheme is authorized by this record.

### F. Feasibility

Approve:

- the upstream component that assigns feasibility;
- evidence required for `FEASIBLE`, `INFEASIBLE`, `UNRESOLVED`, and `INVALID`;
- whether a plan may exist before feasibility is assigned;
- the effect of missing retailer, grouping, price, or ECE inputs on
  construction versus feasibility;
- hard-constraint ownership and evidence.

Cart Optimization must not independently evaluate hard constraints or infer
`FEASIBLE` from structural completeness.

### G. Inconvenience penalty

Approve the owner, source, units, default, whether zero is valid, scope
(user/configuration/planner/retailer/checkout), and availability timing for
`inconvenience_penalty_units`. The value is an explicit required plan input and
participates in identity and ranking; it must not be derived from plan shape.

### H. Retailer preference

Approve the owner, source, numeric meaning, preference direction, default,
scope (user/global/planner/metadata), and availability timing for
`retailer_preference_priority`. It participates in identity and ranking. It
must not be derived from platform names or lexical ordering.

### I. Plan-level Effective Cost Evaluation

Approve:

- the component that creates one Effective Cost Evaluation per plan;
- required inputs;
- whether every plan receives an ECE;
- whether infeasible plans receive ECEs;
- failure behavior;
- how the `EffectiveCostEvaluationReference` is attached.

The established authority boundary remains:

```text
CandidatePlan
  -> plan-level Effective Cost Evaluation
  -> EffectiveCostEvaluationReference
  -> CartOptimizationRequest
  -> Cart Optimization
```

Cost Intelligence owns ECE calculation. CandidatePlan stores a reference, not
an embedded evaluation.

## Required Upstream Data

Before construction can begin, approved upstream components must provide the
data selected by the decisions above, including as applicable:

- an authoritative opaque `retailer_id`;
- deterministic grouping context and a derivation input for
  `checkout_group_id`;
- the complete candidate enumeration policy and its required candidate set;
- the approved handling state for typed-price-ineligible candidates;
- the assigned `plan_id` under the approved convention;
- `inconvenience_penalty_units`;
- `retailer_preference_priority`;
- feasibility evidence and the assigned feasibility state;
- plan-level ECE inputs and the attached
  `EffectiveCostEvaluationReference`.

Persisted candidate discovery currently supplies listing/observation identity,
canonical product/variant identity, quantity, deterministic ordering, and
readiness metadata. It does not supply the remaining values by implication.

## No Inference Rules

The following assumptions are prohibited:

- `platform` equals `retailer_id`;
- `platform` defines a checkout group;
- candidate count equals plan count;
- one candidate is automatically feasible;
- a missing price is zero price;
- a missing ECE is an implicit ECE;
- missing feasibility means `FEASIBLE`;
- lexical retailer ordering defines preference;
- a generated hash is an approved plan identity.

## Approval Matrix

| Decision | Current state | Owner decision | Required data | Blocks |
|---|---|---|---|---|
| Retailer identity | Opaque; platform is not an implicit source | Owner/source/scope/unavailable behavior | Approved retailer identifier | `CandidateItemAllocation`, `CheckoutGroup` |
| Checkout groups | Membership is frozen; construction is not | Grouping key, context, cross-entity rules | Grouping context and derivation inputs | `CheckoutGroup`, allocation construction |
| Candidate enumeration | Discovery is deterministic; plan mapping is open | Zero/one/multiple, alternatives, splits, combinations | Enumeration policy and complete candidate set | CandidatePlan enumeration |
| Typed-price eligibility | Readiness is explicit; plan treatment is open | Exclude, retain, unresolved, or other approved handling | Price eligibility policy | Allocation/plan construction |
| Plan identity | Existing builder is authoritative | `plan_id` owner, convention, collision behavior | Deterministic plan-ID inputs | CandidatePlan construction |
| Feasibility | States and upstream ownership exist | Evidence and assignment boundary | Feasibility evidence | CandidatePlan handoff |
| Inconvenience | Required identity/ranking input | Source, owner, default, zero, timing | Penalty per plan | CandidatePlan construction |
| Retailer preference | Required identity/ranking input | Source, owner, direction, default, timing | Priority per plan | CandidatePlan construction |
| Plan-level ECE | Cost Intelligence is authoritative | Creator, inputs, coverage, failure, attachment | ECE inputs/reference | Request construction and optimization |

## Blocked Implementation

Until the owner decisions and required upstream data are approved, this
boundary must not construct `CandidatePlan`, `CandidateItemAllocation`,
`ItemAllocation`, `CheckoutGroup`, `CartOptimizationRequest`, or Effective
Cost Evaluation. Candidate discovery ends at persisted candidate
readiness/provenance.

## Implementation Unlock Conditions

CandidatePlan construction may begin only when:

1. all nine decisions above have an explicit approved policy;
2. the required upstream owner and source for every required field are named;
3. deterministic enumeration, grouping, identity, feasibility, and ECE
   handoff rules are testable from supplied inputs;
4. unavailable-data behavior is specified for every required input;
5. the implementation can use existing domain types without fabricating values
   or introducing a second identity, retailer, checkout, feasibility, or ECE
   representation.

Until then, the pipeline remains:

```text
resolved cart
  -> persisted candidates
  -> candidate readiness/provenance
  -> [OWNER POLICY GATE]
  -> CandidatePlan construction
  -> plan-level economic evaluation
  -> Cart Optimization
```

## Owner-Decision Matrix

The following matrix is the approval record for the nine unresolved decisions.
Each row requires an explicit owner decision; no choice in the “Available
policy choices” column is selected by this document.

| Decision ID | Current frozen contract | Question requiring approval | Available policy choices | Required upstream data | Owning component/team | Required deterministic behavior | Unavailable-data behavior | Downstream contract unlocked | Blocked until approval |
|---|---|---|---|---|---|---|---|---|---|
| CP-01 | `retailer_id` is opaque; `platform` is not an implicit source | Which entity owns and supplies the retailer identifier, and what is its scope and lifecycle? | Listing-owned; observation-owned; platform-configuration-owned; another named authoritative source | Approved opaque `retailer_id`, scope, immutability, and cross-platform rules | Owner must name the owning domain component | Same persisted candidate and approved source produce the same retailer ID; no platform inference | Exclude from construction; retain as blocked preparation; or another approved state | `CandidateItemAllocation` and `CheckoutGroup` inputs | Allocation and group construction |
| CP-02 | Group membership references are frozen; group construction is not | What dimension and key define a `CheckoutGroup`? | Retailer; platform; fulfillment context; delivery context; composite key; another named dimension | Grouping context, cross-entity rules, deterministic ID inputs | Owner must name the planning/grouping component | Equivalent approved grouping inputs yield the same `checkout_group_id`; ordering cannot affect grouping | Exclude; retain unresolved; or another approved behavior | Valid `CheckoutGroup` and authoritative allocation membership | Group and allocation construction |
| CP-03 | Candidate discovery is deterministic; it does not enumerate plans | How do zero, one, and multiple candidates become CandidatePlans and allocations? | No plan; unresolved preparation; infeasible plan; alternatives; split allocations; cross-item combinations; approved hybrid | Complete candidate set, quantity policy, equivalence rule, and ordering rule | Owner must name the candidate planner | Same ordered inputs produce the same plan set, allocation set, and ordering | Explicitly selected zero/invalid/unresolved behavior; never silent omission | CandidatePlan enumeration | CandidatePlan construction |
| CP-04 | Readiness records valid versus missing/unsupported typed observed price; no fabrication | What does a price-ineligible candidate mean at plan construction? | Exclude; retain as non-comparable preparation; permit unresolved plans; another named policy | Price eligibility policy and handling state | Owner must name the readiness/planning owner | Identical persisted price/readiness data yields identical eligibility and plan treatment | Explicit exclusion, unresolved, or other approved handling; never zero/default/reparse | Allocation provenance and any plan eligibility decision | Allocation and plan construction |
| CP-05 | `CandidatePlanIdentityBuilder` and its fields/order are authoritative | Who assigns `plan_id`, under what deterministic convention, and how are collisions handled? | Upstream supplied opaque ID; approved deterministic derivation from canonical plan data; another named convention | ID owner, canonical inputs, collision policy, and serialization convention | Owner must name the plan-generation component | Equivalent plans receive the same approved ID; distinct plans follow the approved collision rule | Do not construct a plan without an approved ID | CandidatePlan identity and request identity | CandidatePlan construction |
| CP-06 | Feasibility states exist and feasibility is upstream-owned | Which component assigns each state and what evidence is required? | Upstream assertion; upstream proof service; staged assignment before/after ECE; another named owner | Evidence for `FEASIBLE`, `INFEASIBLE`, `UNRESOLVED`, and `INVALID`, including missing-data rules | Owner must name the feasibility/constraint owner | Same evidence yields the same state; no structural completeness implies `FEASIBLE` | Explicit state or construction block per approved rule | CandidatePlan feasibility handoff and Cart Optimization input | Feasibility assignment and plan handoff |
| CP-07 | `inconvenience_penalty_units` is required and identity/ranking-bearing | Who supplies the value, in what units, with what default and timing? | User input; application configuration; planner-derived; retailer metadata; checkout-derived; another named source | Value, units, zero policy, default, owner, and availability timing | Owner must name the penalty owner | Same approved inputs yield the same integer value; no derivation from shape/count | Block construction or use another explicitly approved state | Complete CandidatePlan identity and ranking inputs | CandidatePlan construction |
| CP-08 | `retailer_preference_priority` is required and identity/ranking-bearing | Who supplies the value and which numeric direction represents preference? | User-specific; global; planner-derived; retailer metadata; another named source | Priority value, direction, default, scope, owner, and timing | Owner must name the preference owner | Same approved inputs yield the same value; no lexical/platform inference | Block construction or use another explicitly approved state | Complete CandidatePlan identity and ranking inputs | CandidatePlan construction |
| CP-09 | Cost Intelligence owns plan-level ECE; CandidatePlan stores a reference | Which component creates one ECE per plan, with what inputs and failure behavior? | Cost Intelligence service; named application handoff; another approved creator | Complete plan inputs, required checkout observations, ECE coverage, result ID, and attachment rule | Cost Intelligence owner plus named application handoff owner | Same plan and governed inputs yield the same ECE reference/result association; group ECEs remain contextual | Block request handoff; explicit unresolved/infeasible behavior; or another approved failure state | `EffectiveCostEvaluationReference`, `CartOptimizationRequest`, and Cart Optimization | ECE handoff and request construction |

## Repository-Grounded Decision Analysis

This analysis separates repository evidence from owner approval. Existing
runtime behavior is not approval unless the Cart Optimization contract marks
it frozen.

### CP-01: Retailer identity

- **Existing evidence:** `retailer_id` is required by `CandidatePlan`,
  `ItemAllocation`, `RetailerAllocation`, and `CheckoutGroup` in
  `backend/app/cart_optimization/types.py`. The contract makes it opaque and
  prohibits treating `platform` as retailer identity. Candidate discovery
  supplies platform/listing identity, not a retailer identifier.
- **Classification:** FROZEN for opacity and platform non-equivalence;
  UNKNOWN / NOT ESTABLISHED for source, owner, scope, lifecycle, and missing
  data behavior.
- **Repository-supported proposal:** None; no legitimate retailer source was
  found in the discovery boundary.
- **Owner decision required:** Authoritative owner/source, namespace,
  cross-platform rules, immutability, and unavailable behavior.
- **Required upstream data:** Approved opaque `retailer_id` per candidate.
- **Dependencies:** Blocks CP-02, CP-03, CP-05, and allocation construction.

### CP-02: Checkout-group construction

- **Existing evidence:** `CheckoutGroup` requires
  `checkout_group_id`, `retailer_id`, and `effective_cost_evaluation_id` in
  `types.py`. `CartOptimizationService._validate_fulfillment_structure`
  enforces declared membership and non-empty groups. The identity builder
  includes group identity fields.
- **Classification:** FROZEN for membership/completeness and identity;
  OWNER DECISION REQUIRED for grouping dimension, key, cross-platform and
  cross-retailer rules, and ID derivation.
- **Repository-supported proposal:** None; test construction does not establish
  why allocations share a group.
- **Owner decision required:** Grouping context and unavailable behavior.
- **Required upstream data:** Approved grouping inputs and deterministic ID
  derivation data.
- **Dependencies:** Depends on CP-01 if retailer data participates; blocks
  CP-03 and CP-09 inputs.

### CP-03: Candidate-to-plan enumeration

- **Existing evidence:** Candidate discovery returns deterministic candidates
  and does not construct plans. Cart Optimization consumes supplied plans.
  Fulfillment permits one or more allocations per logical item, while
  `CandidatePlanCoverage` describes supplied coverage rather than generating
  combinations.
- **Classification:** FROZEN that generation is upstream and splits are
  contractually permitted; OWNER DECISION REQUIRED for zero/one/multiple
  behavior, alternatives, combinations, equivalence, and ordering scope.
- **Repository-supported proposal:** Preserve deterministic input ordering;
  exhaustive enumeration is not established and requires approval.
- **Owner decision required:** Alternatives versus allocations, split rules,
  cross-item combinations, zero-candidate meaning, and deduplication.
- **Required upstream data:** Complete candidates, quantities, approved
  grouping/retailer data, price policy, and equivalence rules.
- **Dependencies:** Requires CP-01, CP-02, CP-04, CP-07, and CP-08 policy
  inputs; produces the plan shapes needed by CP-05.

### CP-04: Typed-price eligibility

- **Existing evidence:** Discovery exposes `ready_for_allocation` and
  `not_ready_for_allocation`, preserving missing/unsupported prices. The
  candidate provenance model requires typed `Money`; Cost Intelligence uses
  typed monetary inputs.
- **Classification:** FROZEN that prices are never fabricated, defaulted, or
  silently reparsed; OWNER DECISION REQUIRED for plan treatment.
- **Repository-supported proposal:** Preserve readiness at discovery and defer
  allocation consequences; no stronger proposal is established.
- **Owner decision required:** Exclude, retain as preparation data, permit
  unresolved plans, or another explicit behavior.
- **Required upstream data:** Readiness status and typed price/currency when
  required by the approved policy.
- **Dependencies:** Policy approval precedes CP-03 and CP-06; it does not
  assign feasibility.

### CP-05: Plan identity

- **Existing evidence:** `CandidatePlanIdentityBuilder` in
  `backend/app/cart_optimization/identity.py` defines identity inputs and
  canonicalizes collections. Direct identity tests cover nested fields,
  reordering, and provenance exclusion. `plan_id` is supplied on the model
  and used by ranking and result construction.
- **Classification:** FROZEN for builder authority, fields, and ordering;
  OWNER DECISION REQUIRED for assigning new IDs and collision behavior.
- **Repository-supported proposal:** Reuse the existing builder; introduce no
  new hash or serialization scheme.
- **Owner decision required:** Upstream-supplied opaque IDs versus another
  explicitly approved deterministic convention.
- **Required upstream data:** Final plan shape, identity-bearing values, and
  approved ID convention.
- **Dependencies:** Requires CP-03 output and CP-01, CP-02, CP-07, CP-08
  values; precedes request identity.

### CP-06: Feasibility

- **Existing evidence:** Four `PlanFeasibility` states are defined in
  `backend/app/cart_optimization/enums.py`. Plans supply feasibility; the
  service consumes it and applies only established fulfillment and plan-level
  ECE checks. The contract assigns generation upstream.
- **Classification:** FROZEN for states and ownership boundary; OWNER
  DECISION REQUIRED for evidence and assignment of generated plans.
- **Repository-supported proposal:** Keep assignment outside Cart Optimization;
  preserve all four states and do not infer `FEASIBLE` from structure.
- **Owner decision required:** Assigning component, evidence per state,
  construction-before-state behavior, missing-data treatment, and hard-
  constraint ownership.
- **Required upstream data:** Assigned state and evidence under the approved
  policy.
- **Dependencies:** Policy approval may precede enumeration; state assignment
  follows CP-03/CP-05 and is an input to CP-09.

### CP-07: Inconvenience penalty

- **Existing evidence:** `CandidatePlan` requires
  `inconvenience_penalty_units`; identity and `_ranking_key` use it. The
  contract prohibits deriving it from shape, count, names, or fees. No
  authoritative producer was found.
- **Classification:** FROZEN as required identity/ranking input; UNKNOWN /
  NOT ESTABLISHED for source, units, default, owner, and timing.
- **Repository-supported proposal:** Require an upstream-supplied integer and
  preserve it; source and default remain open.
- **Owner decision required:** Source, units, zero/default policy, owner, and
  availability.
- **Required upstream data:** One approved value per plan.
- **Dependencies:** Policy approval precedes enumeration; value availability
  is needed before CP-05.

### CP-08: Retailer preference

- **Existing evidence:** `CandidatePlan` requires
  `retailer_preference_priority`; identity and `_ranking_key` use it. The
  contract prohibits lexical or platform derivation. No authoritative
  producer was found in the inspected path.
- **Classification:** FROZEN as required identity/ranking input; UNKNOWN /
  NOT ESTABLISHED for source, scope, default, and owner.
- **Repository-supported proposal:** Require an upstream numeric priority and
  preserve the existing ranking direction; source/default remain open.
- **Owner decision required:** Owner, source, numeric meaning, direction,
  scope, default, and timing.
- **Required upstream data:** One approved priority per plan.
- **Dependencies:** Policy approval precedes enumeration; value availability
  is needed before CP-05 and ranking.

### CP-09: Plan-level Effective Cost Evaluation

- **Existing evidence:** `EffectiveCostEvaluationService` and its orchestrator
  create `EffectiveCostEvaluationResult` from cost-intelligence inputs.
  `CartOptimizationRequestBuilder` attaches an existing result, while
  `CartOptimizationService` resolves the plan reference and ranks by its
  effective cost. No inspected component creates an ECE from discovered cart
  candidates or defines infeasible-plan ECE coverage.
- **Classification:** FROZEN for Cost Intelligence ownership, reference-only
  linkage, and plan-level authority; OWNER DECISION REQUIRED for creator,
  inputs, coverage, failure, and attachment timing.
- **Repository-supported proposal:** Keep calculation in Cost Intelligence and
  pass a reference; do not infer one-ECE coverage or failure semantics.
- **Owner decision required:** Creator, inputs, infeasible-plan treatment,
  failure behavior, and reference attachment.
- **Required upstream data:** Final plan, governed cost inputs, required
  observations/checkout inputs, result identity, and reference.
- **Dependencies:** Requires CP-03, CP-05, and approved CP-06 coverage; final
  economic handoff before `CartOptimizationRequest` construction.

## Recommended Approval Order

1. Approve CP-01 and CP-02 without deriving grouping from retailer identity.
2. Approve CP-04 independently of feasibility assignment.
3. Approve CP-07 and CP-08 sources and numeric meanings.
4. Approve CP-03 enumeration using the approved prerequisite inputs.
5. Approve CP-05 ID assignment against actual enumerated plan shapes.
6. Approve CP-06 feasibility evidence and ownership; assign state only after a
   concrete plan exists.
7. Approve CP-09 creator, inputs, coverage, failure, and reference attachment.

Each item remains OWNER DECISION REQUIRED until explicitly approved. This
order does not approve downstream semantics by implication.

## Decision Dependencies

The decisions have separate policy-approval, data-availability, and runtime
sequencing dependencies. Approval of a policy does not assign a runtime state
or provide missing data.

### Phase 1: prerequisite policy decisions

CP-01 retailer identity, CP-02 checkout-group construction, CP-04 typed-price
eligibility, CP-07 inconvenience penalty, and CP-08 retailer preference must
have approved policies before candidates can be interpreted for enumeration.
These decisions define required inputs and eligibility rules; they do not
construct plans.

### Phase 2: candidate enumeration

CP-03 uses the approved Phase 1 policies to determine actual CandidatePlan
shapes, allocation combinations, split behavior, zero/one/multiple candidate
behavior, and equivalent-plan elimination. CP-03 may produce plans that later
receive different feasibility states; it must not be read as requiring only
feasible plans.

### Phase 3: plan identity

CP-05 depends on the actual plan shape produced by CP-03 and the approved
identity-bearing inputs from CP-01, CP-02, CP-07, and CP-08. A plan ID must not
be generated until its convention and collision behavior are explicitly
approved.

### Phase 4: feasibility classification

CP-06 policy approval may occur before enumeration. A feasibility **state** is
assigned only after the resulting CandidatePlan and its required evidence
exist. Structural completeness does not imply `FEASIBLE`. Missing ECE,
retailer, grouping, or price data does not imply `INFEASIBLE` or `UNRESOLVED`
unless the owner approves that rule. The four existing states remain
`FEASIBLE`, `INFEASIBLE`, `UNRESOLVED`, and `INVALID`.

### Phase 5: economic evaluation

CP-09 depends on the finalized CandidatePlan structure and the approved
feasibility and ECE coverage rules. This document does not assume that only
`FEASIBLE` plans receive ECEs, nor that `INFEASIBLE` plans receive ECEs. Cost
Intelligence remains the owner of ECE calculation, and CandidatePlan stores
the reference rather than an embedded evaluation.

### Phase 6: CartOptimizationRequest

Only after the required CandidatePlan fields, feasibility state, and required
plan-level ECE reference are available under the approved policies may the plan
cross into `CartOptimizationRequest` construction.

The runtime dependency diagram is:

```text
CP-01 ─┐
CP-02 ─┤
CP-04 ─┤
CP-07 ─┤
CP-08 ─┼──> CP-03 Candidate Enumeration
       │             │
       │             v
       └──────────> CP-05 Plan Identity
                     │
                     v
                  CP-06 Feasibility
                     │
                     v
                  CP-09 ECE
                     │
                     v
              CartOptimizationRequest
                     │
                     v
               Cart Optimization
```

The diagram describes sequencing after policies are approved; it does not
make feasibility policy approval depend on enumeration, and it does not
derive retailer identity, grouping, feasibility, or economic cost from plan
shape.

## Approval and Implementation Unlock Criteria

CandidatePlan construction is unlocked only when:

- CP-01 through CP-09 each has an approved owner decision, not merely a
  selected implementation convenience;
- every required data source and owning component is named;
- deterministic behavior and unavailable-data behavior are specified for each
  decision;
- dependencies are approved in an order that makes the downstream decision
  inputs available;
- the plan-ID convention is approved without introducing an unapproved hashing
  scheme;
- feasibility evidence and hard-constraint ownership are explicit;
- the plan-level ECE creator, inputs, failure behavior, and reference
  attachment are explicit;
- focused contract/regression tests can be written for each approved rule.

Until these criteria are met, the only supported runtime boundary is persisted
candidate discovery and readiness/provenance. No Python, API, model, or
frontend implementation may cross the policy gate.

## Owner Approval Record

This section is the explicit approval record for CP-01 through CP-09. It is a
blank owner-input template. No policy, owner, source, default, or unavailable-
data behavior is approved by the presence of this template.

An approval is valid only when the owner has explicitly supplied the policy and
the required source/data behavior. Presence of an implementation, model
default, fixture, test helper, or permissive runtime behavior does not
constitute approval.

Once a CP decision is approved, future implementation slices must treat that
decision as frozen unless this document is deliberately amended through another
explicit owner approval record.

### CP-01: Retailer identity

- **Decision ID:** CP-01
- **Decision:** Retailer identity source, ownership, scope, lifecycle, and unavailable-data behavior.
- **Approved policy:**
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:**
- **Unavailable-data behavior:**
- **Effective date/version:**
- **Approval status:** `PENDING OWNER APPROVAL`

### CP-02: Checkout-group construction

- **Decision ID:** CP-02
- **Decision:** Checkout-group dimension, grouping key, cross-entity rules, ID derivation, and unavailable-data behavior.
- **Approved policy:**
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:**
- **Unavailable-data behavior:**
- **Effective date/version:**
- **Approval status:** `PENDING OWNER APPROVAL`

### CP-03: Candidate-to-plan enumeration

- **Decision ID:** CP-03
- **Decision:** Zero, one, and multiple candidate behavior, alternatives, splits, combinations, equivalence, and ordering.
- **Approved policy:**
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:**
- **Unavailable-data behavior:**
- **Effective date/version:**
- **Approval status:** `PENDING OWNER APPROVAL`

### CP-04: Typed-price eligibility

- **Decision ID:** CP-04
- **Decision:** Treatment of candidates with missing, malformed, or unsupported typed observed selling prices.
- **Approved policy:**
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:**
- **Unavailable-data behavior:**
- **Effective date/version:**
- **Approval status:** `PENDING OWNER APPROVAL`

### CP-05: CandidatePlan plan ID

- **Decision ID:** CP-05
- **Decision:** Ownership, convention, deterministic generation, and collision behavior for newly assigned `plan_id` values.
- **Approved policy:**
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:**
- **Unavailable-data behavior:**
- **Effective date/version:**
- **Approval status:** `PENDING OWNER APPROVAL`

### CP-06: Feasibility assignment and handoff

- **Decision ID:** CP-06
- **Decision:** Feasibility owner, evidence for all four states, assignment timing, missing-data treatment, and hard-constraint ownership.
- **Approved policy:**
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:**
- **Unavailable-data behavior:**
- **Effective date/version:**
- **Approval status:** `PENDING OWNER APPROVAL`

### CP-07: Inconvenience penalty

- **Decision ID:** CP-07
- **Decision:** Source, owner, units, default, zero policy, scope, and availability timing for `inconvenience_penalty_units`.
- **Approved policy:**
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:**
- **Unavailable-data behavior:**
- **Effective date/version:**
- **Approval status:** `PENDING OWNER APPROVAL`

### CP-08: Retailer preference

- **Decision ID:** CP-08
- **Decision:** Source, owner, numeric meaning, preference direction, default, scope, and availability timing for `retailer_preference_priority`.
- **Approved policy:**
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:**
- **Unavailable-data behavior:**
- **Effective date/version:**
- **Approval status:** `PENDING OWNER APPROVAL`

### CP-09: Plan-level Effective Cost Evaluation

- **Decision ID:** CP-09
- **Decision:** ECE creator, required inputs, per-plan coverage, infeasible-plan treatment, failure behavior, and reference attachment.
- **Approved policy:**
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:**
- **Unavailable-data behavior:**
- **Effective date/version:**
- **Approval status:** `PENDING OWNER APPROVAL`

### Approval-state summary

```text
CP-01: PENDING
CP-02: PENDING
CP-03: PENDING
CP-04: PENDING
CP-05: PENDING
CP-06: PENDING
CP-07: PENDING
CP-08: PENDING
CP-09: PENDING
```

### Approval-gated implementation rule

CandidatePlan construction remains blocked unless CP-01 through CP-09 each
has:

- an explicit approved policy;
- a named owner;
- an authoritative source;
- a required input/data definition;
- deterministic behavior;
- unavailable-data behavior.

No runtime component may infer a missing value or treat an unfilled approval
record as authorization to construct CandidatePlan objects.

## Owner Decision Evidence Index

This index supplies concrete repository facts for owner review. It does not
approve any CP decision, select a proposal, or alter the approval records
above.

### CP-01: Retailer identity

- **Decision ID:** CP-01
- **Evidence:** `retailer_id` is a required field on `ItemAllocation`,
  `RetailerAllocation`, `CheckoutGroup`, and `CandidatePlan`.
- **Classification:** FROZEN CONTRACT / EXISTING IMPLEMENTATION
- **Repository location:** `backend/app/cart_optimization/types.py`, the
  allocation, group, and plan models; `docs/architecture/cart_optimization_contract.md`,
  retailer allocation semantics.
- **What it establishes:** The value is required at the Cart Optimization
  model boundary and is opaque; platform is not an implicit equivalent.
- **What it does not establish:** The owning entity, authoritative source,
  namespace, cross-platform scope, immutability, or unavailable-data behavior.

### CP-02: Checkout-group construction

- **Decision ID:** CP-02
- **Evidence:** `CheckoutGroup` requires `checkout_group_id`, `retailer_id`,
  and `effective_cost_evaluation_id`; service validation checks declared group
  membership and non-empty groups; identity serialization includes group IDs
  and group ECE IDs.
- **Classification:** FROZEN CONTRACT / EXISTING IMPLEMENTATION
- **Repository location:** `backend/app/cart_optimization/types.py::CheckoutGroup`;
  `backend/app/cart_optimization/service.py::_validate_fulfillment_structure`;
  `backend/app/cart_optimization/identity.py::CandidatePlanIdentityBuilder`.
- **What it establishes:** Group structure, membership/completeness, and
  identity participation already have defined boundaries.
- **What it does not establish:** The grouping dimension, grouping key,
  platform or fulfillment participation, cross-retailer/platform rules, or ID
  derivation.

### CP-03: Candidate-to-plan enumeration

- **Decision ID:** CP-03
- **Evidence:** Candidate discovery returns deterministic per-item persisted
  candidates and readiness metadata. Cart Optimization accepts supplied
  `CandidatePlan` objects and does not enumerate them. Fulfillment permits
  multiple allocations for one logical item.
- **Classification:** FROZEN CONTRACT / EXISTING IMPLEMENTATION
- **Repository location:** `backend/app/services/cart_candidate_discovery.py`;
  `backend/app/cart_optimization/service.py::CartOptimizationService.optimize`;
  `backend/app/cart_optimization/types.py::CandidatePlanCoverage` and
  fulfillment models.
- **What it establishes:** Discovery and optimization are separate boundaries;
  deterministic candidate order and split-allocation capability exist.
- **What it does not establish:** Zero/one/multiple candidate semantics,
  candidate-to-plan cardinality, combinations, exhaustive scope, equivalent
  plan elimination, or plan ordering.

### CP-04: Typed-price eligibility

- **Decision ID:** CP-04
- **Evidence:** Discovery exposes `ready_for_allocation` and
  `not_ready_for_allocation`; missing or unsupported observed prices are
  preserved with readiness metadata. `CandidateListingProvenance` requires a
  typed `Money` value.
- **Classification:** FROZEN CONTRACT / EXISTING IMPLEMENTATION / TEST EVIDENCE
- **Repository location:** `backend/app/services/cart_candidate_discovery.py`;
  `backend/app/cart_optimization/types.py::CandidateListingProvenance`;
  candidate-discovery integration tests in
  `backend/tests/integration/api/test_scrape_api.py`.
- **What it establishes:** Invalid prices are not fabricated, defaulted, or
  silently converted, and readiness is explicit.
- **What it does not establish:** Whether price-ineligible candidates are
  excluded, retained for preparation, or allowed to produce unresolved plans.

### CP-05: CandidatePlan plan ID

- **Decision ID:** CP-05
- **Evidence:** `CandidatePlanIdentityBuilder` serializes plan identity with
  deterministic collection canonicalization; `plan_id` is a required plan
  field and is used by ranking and result construction. Direct identity tests
  cover identity-bearing nested fields and reordering.
- **Classification:** FROZEN CONTRACT / EXISTING IMPLEMENTATION / TEST EVIDENCE
- **Repository location:** `backend/app/cart_optimization/identity.py`;
  `backend/app/cart_optimization/types.py::CandidatePlan`;
  `backend/tests/unit/cart_optimization/test_candidate_allocation_provenance.py`.
- **What it establishes:** The existing builder and identity fields are the
  authority, including deterministic ordering and provenance exclusion.
- **What it does not establish:** Who assigns new plan IDs, the assignment
  convention, or collision behavior for enumerated plans.

### CP-06: Feasibility assignment and handoff

- **Decision ID:** CP-06
- **Evidence:** `PlanFeasibility` defines `FEASIBLE`, `INFEASIBLE`,
  `UNRESOLVED`, and `INVALID`; `CandidatePlan` carries the supplied state;
  Cart Optimization consumes it while applying established structural and
  plan-level ECE checks.
- **Classification:** FROZEN CONTRACT / EXISTING IMPLEMENTATION
- **Repository location:** `backend/app/cart_optimization/enums.py::PlanFeasibility`;
  `backend/app/cart_optimization/types.py::CandidatePlan`;
  `backend/app/cart_optimization/service.py` validation and selection flow.
- **What it establishes:** The state vocabulary, upstream ownership boundary,
  and limited service validation.
- **What it does not establish:** Evidence or assigning component for plans
  created from discovered candidates, construction-before-state behavior, or
  missing-data classification.

### CP-07: Inconvenience penalty

- **Decision ID:** CP-07
- **Evidence:** `inconvenience_penalty_units` is required on `CandidatePlan`,
  participates in identity, and is used in the service ranking key. The
  contract prohibits deriving it from plan shape or checkout count.
- **Classification:** FROZEN CONTRACT / EXISTING IMPLEMENTATION
- **Repository location:** `backend/app/cart_optimization/types.py::CandidatePlan`;
  `backend/app/cart_optimization/identity.py::CandidatePlanIdentityBuilder`;
  `backend/app/cart_optimization/service.py::_ranking_key`.
- **What it establishes:** It is an explicit integer plan input affecting
  identity and ranking.
- **What it does not establish:** Source, owner, units policy, default,
  whether zero is valid, scope, or availability timing.

### CP-08: Retailer preference

- **Decision ID:** CP-08
- **Evidence:** `retailer_preference_priority` is required on `CandidatePlan`,
  participates in identity, and is compared explicitly by `_ranking_key`. The
  contract prohibits lexical or platform-derived preference.
- **Classification:** FROZEN CONTRACT / EXISTING IMPLEMENTATION
- **Repository location:** `backend/app/cart_optimization/types.py::CandidatePlan`;
  `backend/app/cart_optimization/identity.py::CandidatePlanIdentityBuilder`;
  `backend/app/cart_optimization/service.py::_ranking_key`.
- **What it establishes:** It is an explicit numeric plan input affecting
  identity and ranking.
- **What it does not establish:** Source, owner, scope, default, preference
  direction beyond current ranking behavior, or availability timing.

### CP-09: Plan-level Effective Cost Evaluation

- **Decision ID:** CP-09
- **Evidence:** Cost Intelligence has an
  `EffectiveCostEvaluationService` and orchestrator that produce
  `EffectiveCostEvaluationResult`; Cart Optimization resolves a plan-level
  `EffectiveCostEvaluationReference` and ranks by the linked effective cost.
  The request builder attaches existing results rather than creating them.
- **Classification:** FROZEN CONTRACT / EXISTING IMPLEMENTATION
- **Repository location:** `backend/app/cost_intelligence/effective_cost/`;
  `backend/app/cost_intelligence/pipeline/service.py`;
  `backend/app/cart_optimization/request_builder.py`;
  `backend/app/cart_optimization/service.py`.
- **What it establishes:** Cost Intelligence owns calculation, CandidatePlan
  uses a reference, and the plan-level ECE is the economic authority.
- **What it does not establish:** Creator handoff for discovered plans, exact
  inputs, whether every or infeasible plan receives an ECE, failure behavior,
  or reference attachment timing.

### Cross-cutting prerequisite: dual-identity consistency

- **Decision ID:** Cross-cutting prerequisite
- **Evidence:** `CartItemResolutionRequest` permits
  `canonical_variant_id` together with `platform` and
  `platform_listing_id`. `CartResolutionService._resolve_item` validates the
  canonical variant/product path and performs the listing-association lookup,
  but does not compare the association's canonical product/variant mapping
  with the requested canonical identity.
- **Classification:** EXISTING IMPLEMENTATION / TEST EVIDENCE / OWNER DECISION REQUIRED
- **Repository location:** `backend/app/services/cart_resolution.py::CartItemResolutionRequest`;
  `backend/app/services/cart_resolution.py::CartResolutionService._resolve_item`;
  `backend/tests/integration/api/test_scrape_api.py::test_cart_resolution_resolves_variant_and_listing_items_in_input_order`.
- **What it establishes:** The API accepts both identity forms, and existing
  tests exercise the forms independently while preserving input order.
- **What it does not establish:** Whether both identities must agree, which
  identity is authoritative, or whether a mismatch must be rejected, returned
  as unresolved, or handled by another explicit policy. This prerequisite is
  upstream of CandidatePlan construction and is not a CP-01 through CP-09
  approval.

### Cross-cutting prerequisite: candidate duplicate/equivalence semantics

- **Decision ID:** Cross-cutting prerequisite
- **Evidence:** Association registration is idempotent for identical records,
  rejects listing reassignment and conflicting observation-ID mappings, and
  `FilesystemCanonicalListingAssociationRegistry.all()` validates persisted
  conflicts before returning deterministic ordering. Candidate discovery then
  preserves all matching persisted records and sorts them by platform, listing
  ID, and observation ID.
- **Classification:** FROZEN CONTRACT / EXISTING IMPLEMENTATION / TEST EVIDENCE /
  OWNER DECISION REQUIRED
- **Repository location:** `backend/app/product_intelligence/catalog/association_storage.py::FilesystemCanonicalListingAssociationRegistry.register`;
  `backend/app/product_intelligence/catalog/association_storage.py::FilesystemCanonicalListingAssociationRegistry.all`;
  `backend/app/services/cart_candidate_discovery.py::CartCandidateDiscoveryService._discover_item`;
  `backend/tests/unit/product_intelligence/catalog/test_resolution.py::test_resolved_association_persists_and_reloads_with_history`;
  `backend/tests/unit/product_intelligence/catalog/test_resolution.py::test_conflicting_association_fails_closed_without_reassignment`;
  `backend/tests/integration/api/test_scrape_api.py::test_cart_candidate_discovery_preserves_deterministic_item_and_candidate_order`.
- **What it establishes:** Association-level conflict handling and candidate
  ordering are deterministic. Identical association registration is
  idempotent, listing reassignment is rejected, and observation-ID conflicts
  are rejected.
- **What it does not establish:** Candidate-level treatment of identical
  records, one listing represented by multiple observations, or other
  equivalent records. The repository does not choose preservation,
  deduplication, or rejection for those candidate records. Association-level
  conflict handling must not be treated as a candidate duplicate policy.

### Evidence limitations

The repository provides enough evidence to preserve the existing Cart
Optimization boundaries, but it does not provide authoritative answers for the
owner fields in CP-01 through CP-09. In particular, no inspected field,
fixture, test helper, or permissive constructor is evidence of a missing
retailer source, grouping rule, plan enumeration policy, plan-ID convention,
feasibility assignment policy, ranking-input source, or ECE coverage policy.
