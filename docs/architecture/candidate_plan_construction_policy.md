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

The following matrix is the original decision matrix. Its unresolved-question
wording is retained as historical evidence; the explicit approval records
below supersede it for all eleven decisions.

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
it frozen. The Batch 1 and Batch 2 approval records now supersede the
historical `OWNER DECISION REQUIRED` classifications in this evidence section;
the classifications remain preserved as historical evidence.

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

1. Supply CP-01/CP-02 retailer and grouping inputs without deriving either
   from incidental fields.
2. Supply CP-04 readiness inputs and CP-07/CP-08 plan values.
3. Implement CP-03 enumeration using the approved prerequisite inputs.
4. Validate CP-05 supplied plan IDs against final plan shapes.
5. Supply CP-06 feasibility evidence/state and CP-09 Cost Intelligence
   references.

This is runtime sequencing, not an additional approval requirement. It does
not authorize implementation by itself.

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

CandidatePlan implementation is authorized only when:

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

All policy approvals are now recorded. Until the remaining source, data, and
runtime handoff criteria are met, the only supported runtime boundary remains
persisted candidate discovery and readiness/provenance. No Python, API, model,
or frontend implementation may cross the policy gate in this batch.

## Owner Approval Record

This section is the explicit approval record for CP-01 through CP-09. The
records below contain the approved Batch 1 and Batch 2 policies. Concrete
upstream owners and source/data contracts remain implementation prerequisites
where the records explicitly say so.

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
- **Approved policy:** `retailer_id` must come from an authoritative upstream
  retailer source. `platform` is never equivalent to `retailer_id`.
  `retailer_id` remains opaque. Missing authoritative retailer identity blocks
  allocation construction rather than being guessed or derived.
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:** The same approved upstream retailer input yields
  the same opaque identifier; platform, listing IDs, ordering, and counts are
  never used as substitutes.
- **Unavailable-data behavior:** Allocation construction is blocked.
- **Effective date/version:** Owner-approved policy batch; implementation data
  contract remains required before construction.
- **Approval status:** `APPROVED`

### CP-02: Checkout-group construction

- **Decision ID:** CP-02
- **Decision:** Checkout-group dimension, grouping key, cross-entity rules, ID derivation, and unavailable-data behavior.
- **Approved policy:** Checkout groups are constructed only from explicit
  upstream grouping context. Membership is authoritative through
  `checkout_group_id`; every allocation belongs to one declared group and
  every declared group contains an allocation. Group IDs must be deterministic
  from approved grouping inputs. Cross-platform or cross-retailer grouping is
  permitted only when supported by that context.
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:** Equivalent approved grouping inputs yield the
  same group ID independent of allocation or collection order.
- **Unavailable-data behavior:** Group construction is blocked; no arbitrary
  or default group is selected.
- **Effective date/version:** Owner-approved policy batch; grouping source and
  inputs remain required before construction.
- **Approval status:** `APPROVED`

### CP-03: Candidate-to-plan enumeration

- **Decision ID:** CP-03
- **Decision:** Zero, one, and multiple candidate behavior, alternatives, splits, combinations, equivalence, and ordering.
- **Approved policy:** For a finite candidate set, enumerate the exhaustive
  Cartesian product of one allocation-ready candidate per requested logical
  item. Zero candidates for any requested item produce no complete plan and an
  explicit no-plan/unavailable preparation outcome. One candidate produces one
  alternative for that item but does not imply FEASIBLE. Multiple candidates
  produce deterministic alternatives; split allocations are not generated
  from arbitrary quantity partitions unless explicit allocation quantities are
  supplied by an approved upstream source. Cross-platform, cross-retailer, and
  cross-checkout-group combinations are retained when approved CP-01/CP-02
  inputs support them. D-02 governs preservation/equivalence; enumeration does
  not rank, calculate ECE, or assign feasibility.
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:** Candidate inputs are canonically ordered before
  enumeration. Reordered equivalent inputs produce the same complete plan set,
  allocation ordering, and plan ordering. Enumeration is exhaustive over the
  supplied finite candidate set; it does not apply an arbitrary bound.
- **Unavailable-data behavior:** A missing candidate, required approved input,
  or required grouping/retailer context prevents a complete plan from being
  emitted. Alternatives are not silently dropped.
- **Effective date/version:** Owner-approved Batch 2 policy.
- **Approval status:** `APPROVED`

### CP-04: Typed-price eligibility

- **Decision ID:** CP-04
- **Decision:** Treatment of candidates with missing, malformed, or unsupported typed observed selling prices.
- **Approved policy:** Only valid supported typed `Money` is allocation-ready.
  Missing, malformed, unsupported, or otherwise invalid observed prices remain
  explicit not-ready preparation data. No fabrication, defaulting, or silent
  reparsing is permitted. Not-ready candidates cannot create a normal
  allocation-ready economically evaluated plan.
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:** Identical persisted price data and governed
  currency configuration produce the same readiness state and reason.
- **Unavailable-data behavior:** Preserve readiness/provenance and block the
  normal allocation-ready economic path; unresolved-plan treatment remains
  outside this batch.
- **Effective date/version:** Owner-approved policy batch.
- **Approval status:** `APPROVED`

### CP-05: CandidatePlan plan ID

- **Decision ID:** CP-05
- **Decision:** Ownership, convention, deterministic generation, and collision behavior for newly assigned `plan_id` values.
- **Approved policy:** CandidatePlan IDs are supplied by the authoritative
  upstream plan-enumeration boundary and must be non-empty and unique within a
  request. `CandidatePlanIdentityBuilder` remains authoritative for canonical
  identity validation and serialization. The supplied ID is not generated from
  a payload containing itself; no new hashing scheme is introduced. Existing
  identity-bearing fields and canonical collection ordering remain unchanged,
  and listing provenance remains excluded from plan identity. IDs are assigned
  after all identity-bearing plan fields, including the plan-level ECE
  reference, are available and before feasibility-state consumption. Collision
  or duplicate IDs fail closed.
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:** The upstream plan boundary supplies the same ID
  for the same approved plan identity, independent of input ordering.
- **Unavailable-data behavior:** CandidatePlan construction is blocked when an
  authoritative non-empty unique ID is unavailable or collides.
- **Effective date/version:** Owner-approved Batch 2 policy.
- **Approval status:** `APPROVED`

### CP-06: Feasibility assignment and handoff

- **Decision ID:** CP-06
- **Decision:** Feasibility owner, evidence for all four states, assignment timing, missing-data treatment, and hard-constraint ownership.
- **Approved policy:** Feasibility is assigned upstream after the CandidatePlan
  shape and required evidence exist. `FEASIBLE` requires explicit evidence
  satisfying the approved feasibility contract. `INFEASIBLE` requires explicit
  evidence of infeasibility. `UNRESOLVED` represents unavailable or
  contradictory required evidence and remains distinct from `INFEASIBLE`.
  `INVALID` is reserved for structural contract violations. Structural
  completeness alone never creates `FEASIBLE`; Cart Optimization consumes and
  validates the supplied state and does not independently evaluate hard
  constraints.
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:** The same plan and evidence produce the same
  feasibility state. Conflicting semantic evidence is `UNRESOLVED` unless an
  already-frozen structural rule requires `INVALID` or known fulfillment
  mismatch requires effective `INFEASIBLE`.
- **Unavailable-data behavior:** Missing evidence cannot become FEASIBLE or
  silently become INFEASIBLE; the plan remains UNRESOLVED or is blocked under
  the upstream evidence contract. CP-04 not-ready candidates cannot support a
  normal FEASIBLE allocation-ready plan. Missing ECE is handled independently
  under CP-09 and does not redefine feasibility.
- **Effective date/version:** Owner-approved Batch 2 policy.
- **Approval status:** `APPROVED`

### CP-07: Inconvenience penalty

- **Decision ID:** CP-07
- **Decision:** Source, owner, units, default, zero policy, scope, and availability timing for `inconvenience_penalty_units`.
- **Approved policy:** `inconvenience_penalty_units` must come from an explicit
  upstream source. It must not be derived from checkout count, platform count,
  retailer count, allocation count, plan shape, or collection ordering. The
  source must define units, scope, default behavior, unavailable behavior, and
  timing.
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:** The same approved upstream inputs yield the same
  integer value.
- **Unavailable-data behavior:** Construction is blocked unless an explicitly
  owner-approved default exists.
- **Effective date/version:** Owner-approved policy batch; no producer or
  default is created by this approval.
- **Approval status:** `APPROVED`

### CP-08: Retailer preference

- **Decision ID:** CP-08
- **Decision:** Source, owner, numeric meaning, preference direction, default, scope, and availability timing for `retailer_preference_priority`.
- **Approved policy:** `retailer_preference_priority` must come from an
  explicit approved upstream source. Higher priority values remain preferred.
  Preference must not be derived from retailer IDs, platform names, lexical or
  collection ordering, or retailer counts. The source must define scope,
  default, unavailable behavior, direction, and timing.
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:** The same approved upstream inputs yield the same
  priority value and ranking direction.
- **Unavailable-data behavior:** Construction is blocked unless an explicitly
  owner-approved default exists.
- **Effective date/version:** Owner-approved policy batch; no producer or
  default is created by this approval.
- **Approval status:** `APPROVED`

### CP-09: Plan-level Effective Cost Evaluation

- **Decision ID:** CP-09
- **Decision:** ECE creator, required inputs, per-plan coverage, infeasible-plan treatment, failure behavior, and reference attachment.
- **Approved policy:** Cost Intelligence is the sole creator and economic
  authority. After CandidatePlan construction and upstream feasibility
  assignment, the designated application handoff requests one authoritative
  plan-level ECE per CandidatePlan and attaches its reference. Every plan that
  crosses into CartOptimizationRequest requires a linked plan-level ECE
  reference/result. ECE creation failure or a missing reference blocks normal
  request handoff and does not fabricate a cost or alter feasibility. Group
  ECEs remain contextual, are never aggregated into plan-level cost, and are
  not created or mutated by CandidatePlan construction. Linked currencies must
  remain consistent under existing Cart Optimization validation. Invalid plans
  do not cross the request boundary; coverage for infeasible and unresolved
  plans is supplied by the same approved ECE handoff rather than inferred by
  the optimizer.
- **Owner:**
- **Authoritative source:**
- **Required input/data:**
- **Deterministic behavior:** The same finalized plan and governed economic
  inputs produce one stable ECE reference/result association independent of
  collection ordering.
- **Unavailable-data behavior:** Missing or failed plan-level ECE blocks
  CartOptimizationRequest handoff; no implicit ECE, group aggregation, or
  fallback cost is created.
- **Effective date/version:** Owner-approved Batch 2 policy.
- **Approval status:** `APPROVED`

## Cross-Cutting Approval Record

The following cross-cutting input/admissibility decisions are approved by the
same owner policy batch. This approval does not authorize CandidatePlan
construction and does not supply the still-required upstream owner/source data.

### D-01: Dual-identity mismatch

- **Decision ID:** D-01
- **Approved policy:** When canonical variant identity and persisted
  listing/association identity are both available, they must resolve to the
  same canonical Variant. Disagreement fails closed at the earliest boundary
  where both identities are available. Neither identity is silently rewritten,
  and no alternative canonical Variant is inferred. Single-identity paths are
  unchanged. The mismatch representation must be deterministic and explicit.
- **Authoritative source:** The approved identity-consistency policy plus the
  existing canonical catalog and persisted association resolution paths.
- **Required input/data:** Both identities and their resolved canonical
  results, when both are supplied.
- **Deterministic behavior:** Identical inputs and authoritative persisted data
  produce the same agreement or mismatch result.
- **Unavailable-data behavior:** A mismatch is a fail-closed identity
  violation; it is not converted to `UNRESOLVED` merely for convenience.
- **Effective date/version:** Owner-approved policy batch.
- **Approval status:** `APPROVED`

### D-02: Candidate duplicate/equivalence

- **Decision ID:** D-02
- **Approved policy:** Association-level conflict handling remains distinct
  from candidate-level equivalence. Distinct candidate evidence is preserved
  unless an already-established association conflict applies. Candidates are
  not deduplicated merely because they share logical variant identity,
  platform, observed price, commercial attributes, or apparent marketplace
  equivalence. Same-listing observations, different observed prices,
  cross-platform candidates, cross-retailer candidates, and provenance-only
  differences remain distinct evidence until a future enumeration stage applies
  explicitly approved identity dimensions. No new candidate identity is
  introduced by this decision.
- **Authoritative source:** The existing association conflict rules and this
  approved candidate-evidence preservation policy.
- **Required input/data:** Persisted candidate and association identities,
  observation identity, and provenance sufficient to preserve distinct records.
- **Deterministic behavior:** Identical persisted records produce the same
  preserved candidate set and ordering; no collection-order deduplication is
  performed.
- **Unavailable-data behavior:** Preserve the evidence until enumeration has
  an approved equivalence rule; do not silently drop or collapse candidates.
- **Effective date/version:** Owner-approved policy batch.
- **Approval status:** `APPROVED`

### Approval-state summary

```text
CP-01: APPROVED
CP-02: APPROVED
CP-03: APPROVED
CP-04: APPROVED
CP-05: APPROVED
CP-06: APPROVED
CP-07: APPROVED
CP-08: APPROVED
CP-09: APPROVED
```

### Approval-gated implementation rule

All CP-01 through CP-09 policy decisions and D-01/D-02 are approved. The
runtime implementation gate remains closed until the required upstream owners,
authoritative sources, input data, and handoff components are supplied and
validated. Policy approval alone does not authorize CandidatePlan construction.

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

The owner-approved batch above establishes policy for CP-01, CP-02, CP-04,
CP-07, CP-08, D-01, and D-02. It does not supply the upstream owners, sources,
or runtime data required to implement those policies. CP-03, CP-05, CP-06,
and CP-09 remain pending; no inspected field, fixture, test helper, or
permissive constructor is evidence of approval for those decisions.

## Owner Decision Package

This section is the repository evidence package that preceded the approved
batch. For CP-01, CP-02, CP-04, CP-07, CP-08, D-01, and D-02, the approved
records above supersede the historical unresolved-question wording below.
All CP-01 through CP-09 and D-01/D-02 are now approved. This section does not
open the CandidatePlan implementation gate.

| Decision ID | Exact unresolved question | Repository evidence | What remains undecided | Required owner decision | Required authoritative source | Required upstream data | Downstream implementation blocked |
|---|---|---|---|---|---|---|---|
| CP-01 | What authoritative source owns `retailer_id`; what does it identify; what namespace/scope and immutability apply; what happens when unavailable? | **FROZEN CONTRACT:** `retailer_id` is opaque and `platform` is not equivalent. **EXISTING IMPLEMENTATION:** Cart Optimization models require the field, while candidate discovery supplies no retailer ID. | Entity meaning, source, namespace, cross-platform scope, lifecycle, and unavailable behavior. | Select the owner, source, identifier meaning/scope, immutability, and unavailable-data outcome. | Named upstream retailer-domain source or approved persisted association. | One approved opaque `retailer_id` per candidate/group input. | `CandidateItemAllocation`, `CheckoutGroup`, and CandidatePlan construction. |
| CP-02 | What defines a checkout group; which allocations belong together; can groups cross retailers/platforms; how is `checkout_group_id` derived; what happens when grouping data is unavailable? | **FROZEN CONTRACT:** declared-group membership and completeness are enforced; group ECEs are contextual. **EXISTING IMPLEMENTATION:** `CheckoutGroup` requires group ID, retailer ID, and group ECE ID. | Grouping dimension, grouping key, cross-entity rules, deterministic derivation, and missing-context behavior. | Approve grouping semantics and deterministic ID derivation without inferring from field names. | Named grouping/planning component and its approved input contract. | Grouping context plus approved retailer/group inputs where applicable. | `CheckoutGroup`, allocation membership, and CandidatePlan construction. |
| CP-03 | What candidate combinations must be enumerated; are splits permitted; what are zero/one/multiple behaviors; are combinations exhaustive or bounded; what equivalence and ordering rules apply? | **FROZEN CONTRACT:** split allocations are permitted and fulfillment is deterministic once plans are supplied. **EXISTING IMPLEMENTATION:** discovery returns ordered candidates; Cart Optimization does not enumerate plans. **TEST EVIDENCE:** item/candidate ordering is tested. | Candidate-to-plan cardinality, split distribution, combination scope, completeness bounds, equivalence, and ordering beyond discovery. | Select enumeration scope, candidate-count behavior, split/combinations policy, equivalence handling, and ordering. | Named candidate-planning component and enumeration specification. | Complete candidate set, quantities, readiness states, grouping/retailer inputs, and equivalence inputs. | CandidatePlan enumeration and CandidatePlanCoverage construction. |
| CP-04 | What happens to candidates with missing, malformed, or unsupported observed selling prices: exclude, retain as preparation data, permit unresolved plans, or another state? | **FROZEN CONTRACT:** prices are not fabricated, defaulted, or silently reparsed. **EXISTING IMPLEMENTATION:** readiness is explicit. **TEST EVIDENCE:** missing and unsupported prices remain represented as not-ready candidates. | Plan-level treatment of each readiness state and whether price-ineligible candidates can enter any plan state. | Approve exact behavior for `ready_for_allocation` and `not_ready_for_allocation` candidates. | Named readiness/planning owner and typed-price contract. | Readiness status, readiness reason, and typed price/currency when available. | Allocation eligibility, CandidatePlan construction, and feasibility handoff. |
| CP-05 | Who assigns `plan_id`; is it supplied or generated; what exact identity inputs and collision behavior apply; must `CandidatePlanIdentityBuilder` remain authoritative? | **FROZEN CONTRACT:** the existing identity builder and identity-bearing fields are authoritative; canonical ordering is required. **EXISTING IMPLEMENTATION / TEST EVIDENCE:** builder behavior and nested identity fields are directly tested. | Assignment ownership, generation convention, and collision behavior for newly enumerated plans. | Approve the assignment source/convention and collision rule while retaining or explicitly replacing builder authority. | Named plan-generation owner and identity specification. | Final plan shape and all approved identity-bearing values. | CandidatePlan construction, request identity, and replayability. |
| CP-06 | Who assigns `PlanFeasibility`; what evidence supports each state; when is state assigned; who owns hard constraints; what happens with incomplete evidence? | **FROZEN CONTRACT:** states are `FEASIBLE`, `INFEASIBLE`, `UNRESOLVED`, and `INVALID`; feasibility is upstream-owned. **EXISTING IMPLEMENTATION:** Cart Optimization consumes supplied feasibility and applies established structural/ECE checks. | Evidence, assigning component, timing, incomplete-evidence behavior, and hard-constraint ownership. | Approve state ownership, evidence requirements, assignment timing, and incomplete-evidence outcomes. | Named feasibility/constraint owner and evidence contract. | Concrete CandidatePlan plus evidence sufficient for its assigned state. | Feasibility assignment, plan handoff, recommendation semantics, and ECE coverage decisions. |
| CP-07 | What produces `inconvenience_penalty_units`; what are its units and numeric meaning; is zero valid; is there a default; who owns it and when must it exist? | **FROZEN CONTRACT:** it is a required explicit identity/ranking input and is not derived from plan shape. **EXISTING IMPLEMENTATION:** the model, identity builder, and ranking key consume it. | Source, owner, units, zero/default policy, scope, and availability timing. | Approve the producer, numeric contract, zero/default behavior, ownership, and timing. | Named configuration, user-preference, planner, or other approved source. | One approved value per CandidatePlan. | Complete CandidatePlan identity and ranking. |
| CP-08 | What produces `retailer_preference_priority`; what numeric direction and zero meaning apply; what is its scope/default; who owns it and when must it exist? | **FROZEN CONTRACT:** it is an explicit identity/ranking input and is not derived from platform names or lexical order. **EXISTING IMPLEMENTATION:** the model, identity builder, and ranking key consume it. | Source, owner, direction, zero/default meaning, scope, and timing. | Approve the producer, numeric meaning/direction, scope, default, ownership, and timing. | Named user/global/planner/metadata source and preference contract. | One approved priority per CandidatePlan. | Complete CandidatePlan identity and ranking. |
| CP-09 | Who creates plan-level ECEs; what inputs are required; does every plan receive one; what happens for infeasible/unresolved/invalid plans; what happens on failure; when is the reference attached? | **FROZEN CONTRACT:** Cost Intelligence owns calculation; CandidatePlan stores a reference; plan-level ECE is economic authority. **EXISTING IMPLEMENTATION:** Cost Intelligence produces results and Cart Optimization resolves/ranks linked references. | Creator handoff, required inputs, coverage by feasibility state, failure behavior, and attachment timing. | Approve creator, input contract, per-plan coverage, state-specific treatment, failure behavior, and reference attachment. | Cost Intelligence plus the explicitly named application handoff owner. | Final CandidatePlan, governed cost inputs, required observations/checkout inputs, result identity, and reference. | ECE handoff, `CartOptimizationRequest`, and Cart Optimization execution. |

### Cross-cutting: dual-identity consistency

- **Evidence:** **EXISTING IMPLEMENTATION:** `CartItemResolutionRequest`
  accepts canonical variant identity together with platform/listing identity;
  `_resolve_item` does not compare the association mapping with the requested
  canonical mapping. **TEST EVIDENCE:** existing tests exercise the identity
  forms independently.
- **APPROVED POLICY:** Both identities must agree; mismatch fails closed at
  the earliest boundary where both are available, without silent rewriting or
  convenient reinterpretation as `UNRESOLVED`.
- **Required source/data:** An explicit resolution consistency rule and
  mismatch outcome.
- **Blocked:** The resolution-to-discovery handoff and any later candidate
  preparation that relies on the resolved association.

### Cross-cutting: candidate duplicate/equivalence semantics

- **Evidence:** **EXISTING IMPLEMENTATION / TEST EVIDENCE:** association
  storage is idempotent for identical registration, rejects listing
  reassignment and observation-ID conflicts, and candidate discovery preserves
  matching records in deterministic order.
- **APPROVED POLICY:** Preserve distinct candidate evidence except for
  already-established association conflicts. Future enumeration alone may
  apply explicitly approved equivalence dimensions.
- **Required source/data:** An explicit candidate equivalence key and handling
  rule, if any.
- **Blocked:** Candidate enumeration, equivalence elimination, and any later
  CandidatePlan construction. No choice is made here.

### Dependency and gating summary

- **Blocks enumeration:** CP-03; approved D-01, D-02, CP-01, CP-02, and CP-04
  are prerequisites, not remaining approvals.
- **Blocks plan identity:** CP-03 and CP-05, using approved CP-01, CP-02,
  CP-07, and CP-08 inputs.
- **Blocks feasibility:** CP-03 and CP-06, using approved D-01 and CP-04
  admissibility rules.
- **Blocks ranking:** CP-05, CP-07, CP-08, and CP-09's cost handoff.
- **Blocks ECE handoff:** CP-03, CP-05, CP-06, and CP-09, using approved CP-02
  grouping policy.
- **Collectively opens CandidatePlan construction:** CP-03, CP-05, CP-06, and
  CP-09 must also be approved, with required source/data behavior supplied;
  the approved batch alone does not open the gate.

Approval of one CP item does not implicitly approve another item or either
cross-cutting prerequisite.

## Owner Decision Draft — Proposed Defaults for Explicit Approval

This section records the proposed defaults now approved for D-01, D-02, CP-01,
CP-02, CP-04, CP-07, CP-08, CP-03, CP-05, CP-06, and CP-09. It remains
non-runtime documentation and does not open the CandidatePlan implementation
gate.

### D-01 — Dual-identity mismatch

- **Proposed default:** Require `canonical_variant_id` and the persisted
  listing/association identity to resolve to the same canonical Variant. If
  they disagree, fail closed at the earliest boundary where both identities
  are available. Do not rewrite either identity or infer an alternative
  canonical Variant.
- **What is already frozen:** Canonical request identity is
  `(item_id, canonical_variant_id)`; listing and observation provenance remain
  distinct evidence; no silent identity reconciliation is authorized.
- **What is already implemented:** Resolution accepts canonical identity and
  platform/listing identity, but the current boundary does not establish an
  agreement rule for conflicting results.
- **What this decision does NOT authorize:** It does not select canonical or
  listing authority independently, define retailer semantics, or construct a
  CandidatePlan.
- **Dependencies:** Precedes candidate readiness handoff and CP-03; informs
  CP-04 and feasibility evidence.
- **Failure/unavailable behavior:** Fail closed when both identities are
  present but resolve differently; preserve the existing single-identity
  paths unless separately changed by approved policy.
- **Owner approval required:** Approved in this policy batch.

### D-02 — Candidate duplicate/equivalence

- **Proposed default:** Preserve distinct candidate evidence unless an
  already-established association-level conflict rule applies. Do not
  deduplicate candidates merely because logical variant, platform, price, or
  commercial attributes appear equivalent. Apply candidate equivalence only
  at enumeration using explicitly approved identity dimensions.
- **What is already frozen:** Association-level conflict handling is distinct
  from candidate-level equivalence; commercial equivalence is not inferred.
- **What is already implemented:** Identical association registration is
  idempotent; conflicting listing reassignment and observation conflicts are
  rejected; discovery preserves matching records deterministically.
- **What this decision does NOT authorize:** It does not define a new
  candidate identity, commercial equivalence, ranking rule, or plan identity.
- **Dependencies:** Required by CP-03 before candidate combinations or
  equivalent-plan elimination.
- **Failure/unavailable behavior:** Preserve records until an approved
  enumeration rule classifies them; do not silently drop or collapse them.
- **Owner approval required:** Approved in this policy batch.

### CP-01 — Retailer identity

- **Proposed default:** `retailer_id` must come from an authoritative upstream
  retailer source. `platform` is never `retailer_id`. Missing retailer
  identity makes a candidate unavailable for allocation rather than guessed;
  `retailer_id` remains opaque.
- **What is already frozen:** `retailer_id` is opaque and platform identity
  must not be treated as retailer identity. Retailer relationships are not
  validated by the current contract.
- **What is already implemented:** The allocation and checkout-group models
  require retailer fields; candidate discovery does not produce a retailer
  identifier.
- **What this decision does NOT authorize:** It does not define platform,
  seller, marketplace, execution, or retailer capability semantics.
- **Dependencies:** Required by CP-02 and CandidateItemAllocation
  construction.
- **Failure/unavailable behavior:** Block allocation construction when the
  authoritative retailer ID is unavailable; never derive it from platform.
- **Owner approval required:** Approved in this policy batch; eventual upstream
  source and data-contract details remain required implementation inputs.

### CP-02 — Checkout-group construction

- **Proposed default:** Construct groups only from explicit upstream grouping
  context. Never derive grouping from platform name, retailer count, checkout
  count, or allocation order. Each allocation belongs to exactly one declared
  group; each declared group contains at least one allocation; group IDs are
  deterministic from approved grouping inputs. Cross-platform or
  cross-retailer grouping requires explicit upstream approval.
- **What is already frozen:** Allocation membership is authoritative through
  `checkout_group_id`; references must resolve to declared groups; declared
  groups cannot be empty; group ECEs are contextual.
- **What is already implemented:** `CheckoutGroup` requires group ID, retailer
  ID, and group ECE ID; service validation enforces membership and
  completeness.
- **What this decision does NOT authorize:** It does not introduce checkout
  execution, platform adapters, retailer authority, or group ECE economics.
- **Dependencies:** Requires CP-01 and approved grouping context; feeds CP-03
  and CP-09.
- **Failure/unavailable behavior:** Block group construction when required
  grouping context is unavailable; never choose a first allocation or derive a
  group from ordering.
- **Owner approval required:** Approved in this policy batch; eventual grouping
  source and derivation inputs remain required implementation data.

### CP-03 — Candidate enumeration

- **Proposed default:** Enumerate the exhaustive Cartesian product of one
  allocation-ready candidate per requested logical item over the finite
  candidate set. Zero candidates produce no complete plan and an explicit
  no-plan/unavailable preparation outcome. One candidate produces one
  alternative but does not imply FEASIBLE. Splits are not generated from
  arbitrary quantity partitions without explicit upstream allocation inputs.
  Enumeration is deterministic, does not rank or calculate ECE, and uses D-02
  for candidate preservation/equivalence.
- **What is already frozen:** Split fulfillment is supported once plans are
  supplied; Cart Optimization does not generate combinations or rank during
  discovery.
- **What is already implemented:** Candidate discovery preserves deterministic
  candidate ordering; no CandidatePlan enumeration exists.
- **What this decision does NOT authorize:** It does not define retailer,
  checkout, feasibility, plan-ID, or economic semantics by itself.
- **Dependencies:** Requires D-02, CP-01, CP-02, CP-04, CP-07, and CP-08
  inputs.
- **Failure/unavailable behavior:** Do not silently omit zero-candidate or
  incomplete combinations; use only the explicitly approved outcome.
- **Owner approval required:** Approved in Batch 2.

### CP-04 — Typed-price treatment

- **Proposed default:** Only valid supported `Money` is allocation-ready.
  Missing, malformed, or unsupported observed price remains explicit
  not-ready metadata. No fabrication, defaulting, or silent reparsing is
  permitted. Not-ready candidates cannot create an economically evaluated
  allocation-ready plan unless an explicitly approved unresolved-plan policy
  permits it.
- **What is already frozen:** Observed price is evidence/provenance; invalid
  values are never fabricated or silently repaired; plan-level ECE remains
  economic authority.
- **What is already implemented:** Candidate discovery exposes readiness and
  readiness reasons; `CandidateListingProvenance` requires typed `Money`.
- **What this decision does NOT authorize:** It does not recalculate prices,
  create ECEs, or introduce quantity or pack semantics.
- **Dependencies:** Feeds CP-03 and CP-09; interacts with CP-06 evidence.
- **Failure/unavailable behavior:** Preserve not-ready preparation data, but
  block allocation-ready economic plans unless the owner approves another
  explicit state.
- **Owner approval required:** Approved in this policy batch; unresolved-plan
  treatment remains outside this batch.

### CP-05 — Plan ID

- **Proposed default:** Plan IDs are supplied by the authoritative upstream
  plan boundary and are non-empty and unique within a request.
  `CandidatePlanIdentityBuilder` remains authoritative; the supplied ID is not
  generated from a payload containing itself. Existing identity fields,
  canonical ordering, and provenance exclusion remain unchanged. IDs are
  available after identity-bearing plan fields, including plan-level ECE, are
  finalized.
- **What is already frozen:** The existing identity builder and its current
  identity-bearing fields are authoritative; listing provenance is preserved
  but excluded from current plan identity serialization.
- **What is already implemented:** Supplied plan IDs must be non-empty and
  unique; the builder canonicalizes collection ordering; no plan-ID generator
  exists.
- **What this decision does NOT authorize:** It does not change identity
  fields, add observation identity, or introduce a new hashing scheme without
  approval.
- **Dependencies:** Depends on final plan shape from CP-03 and inputs from
  CP-01, CP-02, CP-07, and CP-08.
- **Failure/unavailable behavior:** Do not construct a plan without an
  approved ID convention; collision or ambiguous identity fails closed.
- **Owner approval required:** Approved in Batch 2.

### CP-06 — Feasibility

- **Proposed default:** Feasibility is assigned upstream after plan shape and
  evidence exist. FEASIBLE and INFEASIBLE require explicit evidence;
  UNRESOLVED represents unavailable or contradictory evidence; INVALID is a
  structural violation. Structural completeness never creates FEASIBLE, and
  Cart Optimization remains a consumer/validator rather than a hard-constraint
  evaluator.
- **What is already frozen:** The four states and upstream ownership are
  established; the optimizer applies only established structural fulfillment
  and plan-level ECE checks.
- **What is already implemented:** The service partitions supplied states,
  rejects invalid plans, and prevents structurally infeasible plans from
  ranking as FEASIBLE.
- **What this decision does NOT authorize:** It does not add independent hard
  constraint evaluation or reinterpret opaque constraint references.
- **Dependencies:** Depends on CP-03 plan shapes and interacts with CP-04 and
  CP-09 evidence/coverage.
- **Failure/unavailable behavior:** Missing evidence cannot become FEASIBLE or
  silently become INFEASIBLE. The upstream feasibility owner assigns
  `UNRESOLVED` or blocks handoff under this evidence policy. Structural
  violations remain `INVALID`, and established fulfillment mismatch handling
  remains effective `INFEASIBLE`.
- **Owner approval required:** Approved in Batch 2.

### CP-07 — Inconvenience penalty

- **Proposed default:** `inconvenience_penalty_units` comes from an explicit
  upstream source. It is never derived from checkout count, platform count,
  retailer count, allocation count, or plan shape. The source defines units,
  scope, default, unavailable behavior, and timing. If required and
  unavailable, construction fails closed unless an explicit default is
  approved.
- **What is already frozen:** The field is a required identity/ranking input;
  the optimizer does not derive it from plan shape.
- **What is already implemented:** The model, identity builder, and ranking
  key consume the supplied integer.
- **What this decision does NOT authorize:** It does not create scoring logic
  or infer inconvenience from checkout/execution behavior.
- **Dependencies:** Required before CP-03 can produce complete plans and CP-05
  can produce complete identity inputs.
- **Failure/unavailable behavior:** Block construction unless an approved
  source or default supplies the value.
- **Owner approval required:** Approved in this policy batch; no producer or
  default value is created by this documentation change.

### CP-08 — Retailer preference

- **Proposed default:** `retailer_preference_priority` comes from an explicit
  approved source. Preserve current ranking direction of higher priority first
  unless the owner explicitly changes it. Never derive preference from retailer
  IDs, platform names, lexical ordering, or collection order. The source must
  define scope, default, unavailable behavior, and timing.
- **What is already frozen:** The field is explicit and identity/ranking
  bearing; lexical/platform inference is prohibited.
- **What is already implemented:** Current ranking prefers higher priority
  values through its ranking key; no producer exists in the candidate flow.
- **What this decision does NOT authorize:** It does not create retailer
  semantics, platform ordering, or execution behavior.
- **Dependencies:** Required before CP-03 and CP-05 can produce complete plan
  inputs.
- **Failure/unavailable behavior:** Block construction unless an approved
  source or default supplies the value.
- **Owner approval required:** Approved in this policy batch; no producer or
  default value is created by this documentation change.

### CP-09 — Plan-level ECE

- **Proposed default:** Cost Intelligence is the sole creator. After plan
  construction and feasibility assignment, one plan-level ECE reference/result
  is required for every plan crossing into CartOptimizationRequest. Missing or
  failed ECE creation blocks handoff. Group ECEs remain contextual and are
  never aggregated; CandidatePlan construction does not create ECEs.
- **What is already frozen:** Cost Intelligence owns calculation; plan-level
  ECE is authoritative; group ECEs are contextual and non-aggregated.
- **What is already implemented:** The service resolves linked references,
  rejects missing evaluations, validates currencies, and ranks using plan-level
  effective cost.
- **What this decision does NOT authorize:** It does not add ECE calculation
  to CandidatePlan construction, interpret group ECEs economically, or change
  ECE identity semantics.
- **Dependencies:** Depends on CP-02, CP-03, CP-05, and CP-06 outputs.
- **Failure/unavailable behavior:** Block normal economic handoff when the
  required plan-level reference/result is unavailable for any non-`INVALID`
  plan. No state-specific implicit ECE or fallback cost exists; changing this
  rule requires an explicit policy amendment.
- **Owner approval required:** Approved in Batch 2.

## Approval Checklist

Checking or approving an item below is an explicit OWNER DECISION. An
unchecked item is not approved, and this document must not interpret it as
approved merely because a recommendation is written above.

- [x] D-01 — Dual-identity mismatch (approved owner decision)
- [x] D-02 — Candidate duplicate/equivalence (approved owner decision)
- [x] CP-01 — Retailer identity (approved owner decision)
- [x] CP-02 — Checkout-group construction (approved owner decision)
- [x] CP-03 — Candidate enumeration (approved owner decision)
- [x] CP-04 — Typed-price treatment (approved owner decision)
- [x] CP-05 — Plan ID (approved owner decision)
- [x] CP-06 — Feasibility (approved owner decision)
- [x] CP-07 — Inconvenience penalty (approved owner decision)
- [x] CP-08 — Retailer preference (approved owner decision)
- [x] CP-09 — Plan-level ECE (approved owner decision)

All CP-01 through CP-09 and D-01/D-02 policy decisions are now approved.
CandidatePlan implementation remains blocked until the required upstream
owners, authoritative sources, input data, and runtime handoff components are
actually supplied. Policy approval does not authorize fabricating those
inputs or implementing them in this documentation-only batch.
