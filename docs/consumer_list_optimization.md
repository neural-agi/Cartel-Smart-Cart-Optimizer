# Consumer List Optimization

## Request and reproducibility

`POST /api/v2/optimizations` accepts an owned `list_id` and `expected_revision`; the authenticated session supplies the owner. The route locks and loads that list, rejects archived lists, and returns `409 stale_list_revision` if the current revision differs. It snapshots requested item identity and quantities, current eligible observation references, raw evidence digest, catalog revisions, and configured policy context. A canonical digest derives an idempotent per-user request ID. `GET /api/v2/optimizations/{request_id}` is owner-scoped and returns the stored snapshot only; it never recomputes a historical run.

The current list tables retain only the latest mutable item state. The optimization request's immutable input/result JSON snapshots preserve the exact revision used without inventing list-history lifecycle semantics. Plans and allocations have owner-constrained foreign keys to their request/plan. Canonical product and listing records remain in their existing catalog/association stores; the relational rows keep governed IDs and evidence references, not a competing identity model.

## Candidate eligibility

The existing candidate-discovery service resolves only associations whose Product and Variant are established, active, and have complete pack configuration. The observation must be supported by the existing retailer evidence policy, be the unique latest observation for that retailer product identity, contain a typed supported-currency selling price, and explicitly report `available` or `in_stock`. Superseded, conflicting, fixture/demo, unresolved, mismatched, inactive, unknown-availability, and price-less records cannot enter allocations. No age threshold is invented; observation capture time is returned for consumers to assess, and latest governed observation semantics determine supersession.

Listing identity (platform + platform listing ID + retailer product ID) remains distinct from canonical Product/Variant identity. Price and availability affect offer eligibility/display, never identity matching. The currently supported evidence policy is whatever the existing governed product-search helper admits; this endpoint does not add retailer acquisition or capability claims.

## Optimizer and outcomes

Consumer optimization uses the existing deterministic `AutomaticCartPlanningService` and `CartOptimizationService`; plan identity, tie-breaking, feasibility, and ranking semantics are unchanged. The consumer instance has `checkout_capture=None`, so this endpoint never mutates retailer carts or initiates checkout. The optimizer's feasible-plan contract requires a request/plan-correlated ECE. If that evidence or configured retailer/group/policy authority is absent, the request is persisted as `unavailable` or `unresolved`; observed listing prices are not substituted for ECE. Partial baskets expose eligible observed offers alongside unresolved items, but do not claim a complete allocation. Empty lists return `no_plan`.

Displayed unit prices and quantity-multiplied product subtotals are explicitly `observed` product-price figures. They exclude delivery, handling/platform fees, offers/discount effects, and checkout changes. They are not payable totals, effective costs, or savings. A selected optimizer plan is returned only if the existing optimizer selected it with valid linked ECE.

## Persistence and future acquisition

`optimization_requests` stores the authenticated owner, list/revision, deterministic request ID, digest, policy version, status, and immutable input/result snapshots. `optimization_plans` stores the optimizer's plan identity, feasibility, rank/selection and JSON contract snapshot. `optimization_allocations` stores item/product/variant/quantity, retailer, listing, observation, checkout-group IDs only from the existing plan, and evidence provenance. Composite owner foreign keys prevent cross-user linkage. Unique constraints make identical submissions idempotent and prevent conflicting identity rows.

Future authorized retailer-offer discovery can feed the current candidate boundary by adding governed listing associations and normalized observations through the established ingestion path. It must not bypass exact canonical identity, source provenance, freshness/supersession checks, or the ECE requirement for a feasible checkout-backed optimizer result. There is no checkout/cart automation in this consumer endpoint.
