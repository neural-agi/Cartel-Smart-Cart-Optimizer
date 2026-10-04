# Canonical Product Identity Matching

This is an identity boundary, not an offer-ranking or optimization feature. It reuses governed `Product`, `ProductVariant`, `CanonicalListingAssociation`, and immutable `NormalizedObservation` records.

## Identity contract

An exact match requires attributable, asserted evidence for:

- canonical brand identity (`canonical_brand_name`; an unknown/display-only brand is insufficient);
- product type and every governed `identity_critical` Product attribute, such as formulation;
- every governed `identity_critical` Variant attribute, such as flavor/type;
- complete pack configuration: pack kind, consumer-unit count, declared content and unit, plus per-unit content/components/packaging form when present on either side.

Identity values are normalized only for whitespace and case. Units are not converted: `500 ml` and `0.5 L` do not silently become equal. Any asserted attributes must retain evidence references. Canonical Product/Variant lifecycle and established-identity gates still apply.

Canonical display title, retailer title, descriptions, images, and category labels are descriptive/search aids, not proof of identity. Title similarity alone never matches. Price, discounts, availability, stock, capture recency, and ranking are excluded from the identity profile entirely. Staleness must be evaluated by offer/search policy separately; an old offer cannot fill a missing identity fact.

## Resolution states

- `EXACT_MATCH`: exactly one active established canonical Product/Variant satisfies all required asserted facts. Only this state may produce an automatic listing association.
- `MISMATCH`: a proposed canonical pair has an authoritative contradiction, such as a different brand, formulation, flavor, pack kind, quantity, or unit.
- `UNRESOLVED`: required facts/provenance are absent, inferred, conflicting, the candidate set is ambiguous, or no unique exact catalog pair exists. It never upgrades to exact through title similarity.

Catalog-wide resolution with zero or multiple exact candidates is `UNRESOLVED`; unrelated canonical entries are not treated as evidence that the listing is `MISMATCH` to a particular product.

## Retailer adapters and provenance

`RetailerIdentityAdapter` maps retailer evidence into the shared `ProductIdentityProfile`; the canonical comparison logic is retailer-independent. `BlinkitIdentityAdapter` currently exposes only fields represented by its normalized observation and marks missing identity as unresolved. Current Blinkit observations generally lack explicit brand/formulation and structured pack identity, so the adapter intentionally cannot promote them to exact matches. Future Zepto/Swiggy adapters can implement the same protocol; no retailer-specific matcher is required.

The adapter retains the original normalized observation, including platform, Cartel `source_record_id`/listing identity, native `retailer_product_id`, product URL, artifact reference/digest, capture time, parser/normalizer versions, and evidence references. `source_index` is not a retailer ID. The resolver does not rewrite or merge listing identities. Distinct retailer listings may independently associate to one canonical Product/Variant only after exact resolution.

Consumer search already returns canonical IDs alongside each associated listing's retailer identity and observation provenance. No response-shape change is needed for this matcher; a listing appears only if its association exists and current consumer evidence checks pass. This work adds no optimizer, cart, checkout, or production data.
