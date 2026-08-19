# Cart Optimization Planning Handoff Contract

This document defines a non-approving application handoff shape for the
existing Cart Candidate Discovery and Cart Optimization boundaries. It does
not create producers, defaults, inference rules, or new policy. The approved
policy remains authoritative in
`docs/architecture/candidate_plan_construction_policy.md`.

## Scope

The proposed handoff is:

```text
CartCandidateDiscoveryResult
  -> explicit upstream enrichment and plan inputs
  -> CandidateAllocationSet / CandidatePlanConstructionInput
  -> CandidatePlanConstructionService
  -> CartOptimizationRequest
  -> CartOptimizationService
```

The repository currently has no production caller that supplies the complete
bundle. This document records the minimum interface that such a caller must
eventually satisfy.

## Existing Discovery Input

`CartCandidateDiscoveryResult` is the existing discovery output. For each
`CartCandidateDiscoveryItem`, the handoff may consume:

- `item_id`;
- `quantity`;
- `canonical_product_id`;
- `canonical_variant_id`;
- discovery `status` and `reason`;
- candidates in the backend's deterministic order.

Each `PersistedListingCandidate` supplies:

- `platform`;
- `platform_listing_id`;
- `canonical_product_id`;
- `canonical_variant_id`;
- `observation_id`;
- persisted `NormalizedObservation`;
- explicit readiness;
- explicit readiness reason when not ready.

These fields are candidate evidence. They do not supply `retailer_id`,
`checkout_group_id`, plan identity, feasibility, penalty, preference, or a
plan-level ECE.

Only candidates with `ready_for_allocation` may enter the normal allocation
input path. Not-ready candidates remain preserved preparation data and must
not be silently converted into an allocation-ready candidate.

## Supplied Enrichment And Plan Inputs

The following values must be supplied by authoritative owners or callers. The
handoff must not derive them from discovery fields.

| Scope | Required input | Existing repository shape | Required rule |
| --- | --- | --- | --- |
| Allocation | `retailer_id` | `CandidateItemAllocation.retailer_id` and `CandidateAllocationEnrichment` | Explicit opaque retailer identity; never platform-derived. |
| Allocation | `checkout_group_id` | `CandidateItemAllocation.checkout_group_id` | Explicit group membership; never derived from platform, retailer, count, or order. |
| Allocation | quantity | `CandidateAllocationSet.quantity` and candidate allocation `quantity` | Preserve the requested quantity and reject mismatch; no split generation. |
| Allocation | canonical identity | discovery item and candidate fields | Preserve and validate exact logical identity; do not rewrite mismatches. |
| Plan | `plan_id` | `CandidatePlanConstructionInput.plan_id` | Supplied, non-empty, unique within the request; no local generation. |
| Plan | `inconvenience_penalty_units` | `CandidatePlanConstructionInput` / `CandidatePlan` | Explicit supplied value; no plan-shape calculation or default. |
| Plan | `retailer_preference_priority` | `CandidatePlanConstructionInput` / `CandidatePlan` | Explicit supplied value; preserve higher-is-better ranking semantics. |
| Plan | feasibility and evidence | `PlanFeasibility` and `feasibility_evidence` | Supplied upstream evidence; construction does not evaluate hard constraints. |
| Plan | plan-level ECE reference/result | `EffectiveCostEvaluationReference` and `EffectiveCostEvaluationResult` | Supplied matching reference/result; construction does not create or calculate ECE. |
| Group | declared groups | `CheckoutGroup` | Explicit groups with authoritative membership and group ECE linkage. |

`CandidateAllocationEnrichmentService` is the existing explicit conversion
boundary for allocation-level retailer and checkout-group inputs. It accepts
an enrichment object supplied by a caller; it is not a retailer or grouping
producer.

## Boundary Responsibilities

### Discovery

`CartCandidateDiscoveryService` owns persisted candidate lookup, canonical
identity matching against the request, deterministic candidate ordering, and
readiness classification. It does not construct allocations or plans.

### Enrichment

`CandidateAllocationEnrichmentService` validates that a supplied enrichment
matches the discovery item and candidate, then preserves candidate identity,
quantity, and provenance while attaching the explicitly supplied retailer and
checkout-group IDs. It must fail closed for missing or mismatched values and
must preserve distinct candidates.

### Enumeration

`CandidatePlanConstructionService.enumerate_allocations` consumes explicit
allocation-ready candidate sets. It orders inputs deterministically and
enumerates the supported full-quantity candidate combinations. It does not
infer quantities, generate splits, deduplicate candidates, rank plans, assign
feasibility, or calculate ECEs.

### Construction

`CandidatePlanConstructionInput` is the explicit plan envelope. Its caller
supplies plan ID, plan inputs, groups, feasibility evidence, and matching ECE
reference/result. Construction validates required structural inputs and
creates the existing `CandidatePlan` model without creating upstream data.

### Cost Intelligence

Cost Intelligence remains the creator and economic authority for ECEs. Its
existing pipeline requires a caller-supplied `CheckoutObservation` and
`CartOptimizationRequest`. Listing-level candidate observations are not
checkout observations and cannot be promoted into one.

### Optimization

`CartOptimizationService` consumes the completed request, validates plan
structure and linked ECE data under its existing contract, partitions supplied
feasibility states, and ranks eligible plans. It does not become the producer
of missing upstream inputs.

## Determinism And Identity

- Discovery item order and candidate order remain deterministic.
- Enrichment preserves the candidate records supplied to it and does not
  deduplicate them.
- Enumeration canonicalizes candidate-set and candidate ordering before
  producing combinations.
- Plan construction orders multiple supplied plans by their authoritative
  supplied `plan_id`.
- ECE references and results must match by evaluation identity; conflicting
  results for one evaluation identity fail closed.
- No ordering operation may alter identity-bearing collection semantics.
- `CandidatePlanIdentityBuilder` remains the existing identity/serialization
  authority. This handoff contract does not change its fields or generate IDs.

## Failure Behavior

The future caller must fail closed and return an explicit error or unavailable
state when any required input is absent or invalid, including:

- no allocation-ready candidate for a required logical item;
- missing or mismatched canonical identity or quantity;
- missing retailer or checkout-group context;
- blank or duplicate supplied plan ID;
- missing feasibility evidence;
- invalid feasibility state;
- missing or mismatched plan-level ECE reference/result;
- unavailable checkout evidence required before ECE creation.

No fallback may use platform identity, listing identity, collection order,
candidate count, price, plan shape, or a default economic/ranking value.

## Unavailable Producers

The current repository does not provide connected production producers for:

- retailer identity;
- checkout-group context;
- inconvenience penalty;
- retailer preference;
- feasibility state/evidence;
- supplied plan IDs;
- checkout capture and `CheckoutObservation`;
- plan-level ECE reference/result for discovered candidates.

Therefore this contract is a design boundary only. It does not authorize a
production caller to populate those fields, and it does not make the current
cart candidate flow eligible for CandidatePlan construction.

## Checkout Capture Application Boundary

The application-owned checkout capture boundary is implemented separately from
retailer acquisition:

```text
CheckoutCaptureRequest
  -> CheckoutCaptureAdapter
  -> CheckoutCaptureArtifact (CaptureType.CHECKOUT)
  -> CheckoutCaptureParser
  -> CheckoutObservation
  -> CheckoutCaptureRegistrationService
  -> (request_id, plan_id)
```

`CheckoutCaptureRequest` carries explicit request and plan ownership plus
canonical cart-item identities and quantities. The artifact preserves raw
payload, capture metadata, platform, parser version, evidence references, and
the same ownership pair. It is not a listing observation and cannot be created
from one.

When an artifact store is configured, `CheckoutCaptureService` publishes the
immutable raw payload through the existing `ArtifactStore` contract before
parsing or registration. The resulting observation points to the durable
storage reference and retains the original capture source as an evidence
reference. Publication does not imply that acquisition occurred.

`JsonCheckoutCaptureParser` is a generic structured-artifact parser for the
application boundary. It validates typed money and maps only fields present in
the captured payload; it does not fill missing values or calculate checkout
economics. Artifact `content_type` remains descriptive metadata at the global
artifact boundary, while this JSON parser explicitly accepts only JSON media
types. A future retailer adapter owns browser/session acquisition and must
return a complete, provenance-backed checkout artifact.

The default `CheckoutCaptureAdapter` is unavailable and fails closed. Registry
provider mode does not enable capture; it only enables lookup of observations
registered through the existing correlation store. Synthetic checkout artifacts
are test-only fixtures and are not production seed data. Blinkit-specific
capture remains unavailable until real runtime evidence establishes its cart,
checkout, and artifact contracts.

## Existing Versus Proposed

Existing repository behavior includes the discovery models and statuses,
`CandidateAllocationEnrichmentService`,
`CandidatePlanConstructionService`, the Cart Optimization request/models, and
the Cost Intelligence pipeline. The named handoff sequence and responsibility
separation above are the proposed application interface shape for a future
caller; they are not an existing production integration and do not introduce
any new source of truth.
