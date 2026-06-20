# Cartel Canonical Product Schema Design

## Purpose And Scope

This document proposes Cartel's platform-independent representation of grocery products. It is a domain-model design proposal, not a database schema, implementation plan, normalization policy, or matching algorithm.

The proposal is grounded in:

- `docs/research_analysis.md`, which establishes the separation between acquisition, extraction, product intelligence, cost intelligence, and optimization.
- `docs/evidence_corpus_analysis.md`, which records observed Blinkit patterns across milk, bread, rice, atta, biscuits, chips, soft drinks, and shampoo.

The objective is to establish a stable target for future normalization and matching while preserving the distinction between a product's identity and a platform's changing commercial presentation of it.

## Design Position

Cartel should model the following concepts separately:

1. **Product**: the stable consumer product family or formulation.
2. **Product Variant**: a consumer-distinct purchasable configuration of that product, including material variant attributes and pack composition.
3. **Platform Listing**: a platform's native catalog entry that may represent a product variant.
4. **Listing Observation**: an append-only capture of how that listing appeared in a particular location, session, and time.

The canonical catalog comprises Products and Product Variants. It must not absorb raw listing text, current price, stock state, offers, fees, or browser/session data.

This separation is the central decision in the proposal. A price comparison becomes meaningful only when a platform listing is linked, with evidence and confidence, to a consumer-distinct canonical variant. A canonical record must therefore remain stable while listing observations change.

## Evidence, Decisions, And Assumptions

### Evidence-Based Facts

- Blinkit titles combine brand, product type, formulation, flavor, marketing claims, and sometimes pack information. Examples include milk type, `No Maida` bread claims, grain descriptions, chip flavors, shampoo treatments, and a soft-drink `Pack of 2` title.
- Quantity is represented as single net content (`500 ml`, `5 kg`), multipack composition (`2 x 750 ml`), and non-round pack sizes. A single scalar quantity cannot faithfully represent every sellable pack.
- The same product family appears in materially different sizes and variants. Similar titles alone would incorrectly merge separate purchasable items.
- Platform price, availability, discount labels, location, capture time, and browser session context are observations, not product identity.
- The current extractor's raw `mrp` and `in_stock` fields are useful evidence but are not semantically certain enough to become canonical product fields.

### Design Assumptions

- Most initial catalog creation will start from platform-native evidence, often without a barcode or manufacturer identifier.
- Exact product equivalence may be unknown at first. The catalog needs an explicit unresolved or reviewable state rather than forced matches.
- Categories and controlled attribute vocabularies will evolve. The schema should accommodate versioned classification without requiring a final taxonomy now.
- A consumer-distinct pack may be represented as a Product Variant even when its underlying formulation is shared with other pack sizes.

These are operational assumptions, not established facts. They should be reviewed after evidence is collected from more locations and platforms.

## 1. Canonical Product Structure

### What Fundamentally Defines A Grocery Product

At the broadest level, a grocery product is defined by a stable identity statement:

- brand or explicit no-brand/unknown-brand status
- product type or family, such as toned milk, sandwich bread, basmati rice, potato chips, or shampoo
- material formulation or variant attributes, such as full cream, A2, whole wheat, flavor, grain type, hair-treatment range, or sugar/caffeine state where relevant
- consumer-relevant packaging and sellable pack composition

These elements are not equally applicable to every category. The schema should therefore use a common core plus typed, category-dependent attributes rather than one large set of mostly empty product-specific columns.

### Identity, Variant Attributes, Packaging, Quantity, Category, And Provenance

| Concern | Belongs in canonical Product? | Belongs in canonical Product Variant? | Rationale |
| --- | --- | --- | --- |
| Brand identity | Yes | Reference only when needed | Brand is a principal matching constraint, but a variant normally inherits it from its Product. |
| Product type/family | Yes | No, except an explicit override | `Milk`, `bread`, `rice`, and `shampoo` identify the underlying product family. |
| Formulation and identity-critical variant attributes | Usually Yes | Yes when pack-specific or commercially distinct | `Toned`, `A2`, `whole wheat`, `Magic Masala`, and `Keratin Smooth` affect substitutability and must survive cataloging. |
| Descriptive claims | Optional | Optional | Claims such as `No Maida` or `High Fibre` are preserved when observed, but are not automatically treated as a distinct product identity. |
| Packaging form | Optional | Yes when material | Bottle, pouch, carton, jar, sachet, and tub can affect consumer choice and comparison. |
| Pack composition and net content | No | Yes | `500 ml`, `5 kg`, and `2 x 750 ml` define the purchasable configuration. |
| Canonical category classification | Yes | Optional refinement | A product family should have a broad controlled classification; more granular category paths may evolve. |
| Evidence and lifecycle metadata | Yes | Yes | Canonical decisions need traceability, reviewability, and revision history. |
| Raw title, raw quantity text, raw badges | No | No | These are immutable listing evidence and stay with the Platform Listing or Listing Observation. |
| Price, availability, offers, fees | No | No | These vary by platform, location, time, session, cart, and eligibility. |

### Information Outside The Canonical Product

The following must remain outside the canonical catalog even if they are useful inputs to it:

- platform product/listing ID, URL, raw title, image, description, and platform category path
- raw quantity text, raw card text, visible price strings, visible price labels, discount badges, and UI controls
- location/store, capture time, source artifact identifier, parser version, session scope, and extraction confidence
- selling price, reference-price interpretation, stock/UI availability, ETA, display rank, and checkout eligibility
- offer language, coupon eligibility, membership status, payment method, fee rules, and cart outcome

Keeping these fields out of canonical records prevents commercial volatility and platform-specific semantics from rewriting product identity.

## 2. Listing Versus Product Separation

### Product

A Product is the stable canonical family from which sellable variants derive. It represents the brand and underlying consumer product identity, not a particular current platform card or price.

Example: `Amul Taaza Toned Milk` as a branded toned-milk formulation.

A Product can have several Product Variants, such as different net quantities or materially different packaging. It should not contain a listing's price, availability, or offer.

### Product Variant

A Product Variant is the smallest canonical unit Cartel can safely compare as a consumer-distinct purchase. It combines the inherited Product identity with any material variant attributes and an exact pack configuration.

Examples:

- Amul Taaza Toned Milk, `500 ml` pouch
- Amul Taaza Toned Milk, `1 L` carton
- Coca-Cola Soft Drink, `2 x 750 ml` multipack
- a distinct shampoo formulation in `300 ml`

A Product Variant is the likely target of a cross-platform listing match. Similar variants should not be merged merely because they share a brand and title stem.

### Platform Listing

A Platform Listing is the platform-native catalog object. It holds the platform's identifier and presentation of an item, including raw title, raw category, URL, image references, and mapping status to a canonical Product Variant.

One Platform Listing should usually map to zero or one current canonical Product Variant. It may initially be unresolved, ambiguous, or under review. The mapping must retain a confidence and an explanation in the future product-intelligence layer.

### Listing Observation

A Listing Observation is a time- and context-bound capture of a Platform Listing. It records evidence such as displayed price, raw reference price text, visible discount text, UI availability state, location/store context, session scope, capture time, parser version, and source artifact reference.

The observed Blinkit `ADD` state and second visual price belong here. They remain facts about a page render, not assertions about inventory or MRP semantics.

### Why The Separation Must Remain Strict

- **Temporal correctness:** prices, availability, and offers change frequently; Product and Product Variant identity should not.
- **Location correctness:** the same listing can differ by delivery location or store context.
- **Auditability:** raw extraction can be reinterpreted when parser or normalization rules improve without changing historical evidence.
- **Matching safety:** an uncertain listing-to-variant link can be reviewed or replaced without mutating the platform listing itself.
- **Cost correctness:** cart and checkout conditions belong to observations and later cost scenarios, not the catalog.

## 3. Quantity And Packaging Model

### Principle

Quantity is not a display string and is not always a single amount. A canonical Product Variant needs a structured **pack configuration** that describes what the consumer receives. Raw expressions remain unchanged in the evidence layer.

### Required Conceptual Components

| Component | Purpose | Examples |
| --- | --- | --- |
| `pack_kind` | Distinguishes the commercial structure of the pack. | `single_unit`, `multipack`, `combo`, `assortment`, `unknown` |
| `consumer_unit_count` | Count of like consumer units when explicitly known. | `1`, `2`, `6` |
| `content_per_consumer_unit` | Net content of one homogeneous unit, represented as value plus measurement dimension and unit. | `500 ml`, `750 ml`, `1 kg` |
| `total_declared_content` | Total content where explicitly stated or safely derivable for a homogeneous pack. | `1500 ml` for `2 x 750 ml` |
| `packaging_form` | Consumer-facing package form when material or known. | `pouch`, `carton`, `bottle`, `jar`, `sachet` |
| `component_set` | Describes non-homogeneous contents without forcing them into a false single quantity. | a snack combo with separate components |
| `content_basis` | States what the measurement means, such as net content or count-only. | `net_content`, `count_only`, `unknown` |
| `pack_configuration_status` | Makes incomplete or uncertain composition explicit. | `complete`, `partial`, `unknown`, `requires_review` |

### Conceptual Representation Of Observed Patterns

| Observed expression | Canonical pack interpretation |
| --- | --- |
| `500 ml` | `single_unit`; count `1`; content per unit `500 ml`; total `500 ml`. |
| `1 L` | `single_unit`; count `1`; content per unit `1 L`; total `1 L`. |
| `5 kg` | `single_unit`; count `1`; content per unit `5 kg`; total `5 kg`. |
| `Pack of 2` | `multipack`; count `2`; per-unit content remains unknown unless independently evidenced. |
| `2 x 750 ml` | `multipack`; count `2`; per-unit content `750 ml`; total declared content `1500 ml`. |
| Combo pack | `combo` or `assortment`; preserve component descriptions and quantities when available; do not synthesize an equivalent single product quantity. |

### Important Boundaries

- Unit conversion, equivalence, and price-per-unit calculations are future derived behavior, not part of this design.
- A title may contain a number that is not pack content. Canonical pack configuration should only be asserted when the evidence supports it.
- `2 x 750 ml` and `1.5 L` may have equivalent total content but are not necessarily equivalent Product Variants. Their multipack structure and packaging can be material to price, offers, convenience, and consumer preference.
- A combo is not a multipack simply because it contains several items. Homogeneity must be explicit.

## 4. Variant Modeling

### Identity-Critical Attributes

An identity-critical attribute changes the product that a consumer is purchasing or changes whether it is an acceptable substitute. These attributes should be represented as structured key/value evidence on the Product or Product Variant, with category-specific semantics developed later.

Examples evidenced by the corpus and research include:

| Category | Identity-critical examples |
| --- | --- |
| Milk | milk type/formulation (`toned`, `full cream`, `A2`, lactose-free where observed), source where stated, processing classification when material |
| Bread | grain/composition (`whole wheat`, `atta`), bread style/type, meaningful dietary formulation |
| Rice | grain family, grain length/type, rice variety, processing/quality designation when it changes the SKU |
| Atta | flour composition, grain blend, formulation where materially distinct |
| Biscuits | biscuit type, flavor, filling/coating style when it defines the SKU |
| Chips | base snack type, flavor, variant/range |
| Soft drinks | brand family, flavor, beverage type, sugar/caffeine/zero-sugar state where stated, multipack composition |
| Shampoo | product line/range, treatment or hair concern, formulation or target hair type where stated |

The intended model is an attribute collection with a controlled attribute name, value, evidence status, and role. The role must distinguish `identity_critical` from `descriptive` rather than assuming every token in a title is equally important.

### Descriptive Attributes

Descriptive attributes help search, display, review, and later matching, but should not automatically create a separate canonical Product or Product Variant. They include:

- marketing language and promotional claims
- presentation text not shown to be a formulation difference
- non-material slogans
- retailer-curated descriptors
- title word order and punctuation

Claims such as `100% Atta`, `0% Maida`, `No Maida`, or `High Fibre` should be preserved as evidence and may later be classified as identity-critical for a defined category. The evidence corpus does not justify making that decision automatically today.

### Attribute Modeling Rules

- Do not reduce meaningful attributes to free-text leftovers after normalization.
- Do not force unobserved attributes to `false`; use absent, unknown, or not-applicable states deliberately.
- Do not make category-specific attributes globally mandatory. A shampoo treatment is not meaningful for rice, and a grain type is not meaningful for soft drinks.
- Preserve source evidence and confidence for any attribute derived from noisy listing text.
- Treat packaging and pack composition as variant-defining even when the underlying formulation is shared.

## 5. Recommended Canonical Schema

This is a conceptual schema recommendation. Field names indicate stable domain concepts; they are not instructions to create database columns, Pydantic models, or dataclasses.

### Product Fields

| Field | Status | Purpose And Why It Exists | Evidence Basis |
| --- | --- | --- | --- |
| `canonical_product_id` | Mandatory | Stable opaque identifier for the Product family. It must not encode a platform, title, or pack size. | Research: canonical identity must be independent of platform listings. |
| `product_identity_status` | Mandatory | States whether identity is established, provisional, ambiguous, deprecated, or merged. Prevents unresolved evidence from becoming false certainty. | Research: matching is confidence-aware and reviewable. |
| `brand_reference` | Mandatory, with explicit `unknown` or `unbranded` state | Identifies the canonical brand or records that no reliable brand is known. Brand is a primary matching constraint. | Evidence: every category shows brand-prefixed titles; research identifies brand aliases as necessary. |
| `product_type` | Mandatory | Controlled broad product type, such as milk, bread, rice, chips, soft drink, or shampoo. Gives a stable comparison boundary before taxonomy is mature. | Evidence corpus spans distinct product classes with different attributes. |
| `canonical_display_name` | Mandatory | Human-readable product family label for review and user-facing explanation. It is a label, not the sole identity key. | Evidence: raw titles are composite and cannot serve directly as canonical truth. |
| `identity_attributes` | Mandatory collection; may be empty only after explicit review | Structured material attributes that define the formulation/family within its product type. | Evidence: toned/full-cream/A2, grain descriptors, flavors, shampoo treatments. |
| `descriptive_attributes` | Optional collection | Preserves useful, non-decisive claims or descriptors without treating them as identity. | Evidence: claims and marketing language are mixed into titles. |
| `canonical_category_reference` | Mandatory at broad level; detailed path optional and versioned | Assigns the Product to a controlled category reference while avoiding an irreversible detailed taxonomy decision. | Research: categories are inconsistent across platforms and taxonomy should evolve. |
| `lifecycle_status` | Mandatory | Represents active, discontinued, superseded, or unknown lifecycle state without deleting historical identity. | Research: reformulation and repackaging must not overwrite history. |
| `catalog_revision` | Mandatory | Identifies the version of the canonical assertion for traceability and future correction. | Research: transformations and match decisions must be auditable. |
| `evidence_references` | Mandatory collection | Links the canonical assertion to stable evidence identifiers and decision records, not raw machine-local file paths. | Research: provenance needs portability; evidence corpus identifies provenance drift risk. |
| `effective_period` | Optional initially, expected later | Records when a canonical identity assertion is known to apply, especially for reformulations or rebrands. | Research: product changes must not overwrite history. |

### Product Variant Fields

| Field | Status | Purpose And Why It Exists | Evidence Basis |
| --- | --- | --- | --- |
| `canonical_variant_id` | Mandatory | Stable opaque identifier for the exact consumer-distinct purchasable configuration. This is the normal target for listing matching. | Research: similar titles with different sizes must not collapse. |
| `canonical_product_id` | Mandatory | Links the variant to its Product family. | Product/Variant separation in this proposal. |
| `variant_identity_status` | Mandatory | States whether the variant is established, provisional, ambiguous, deprecated, or merged. | Research: uncertainty must be preserved. |
| `variant_identity_attributes` | Optional, but mandatory when material attributes differ from the Product | Records variation that belongs to this sellable variant rather than the general product family. | Evidence: category attributes may be formulation- or pack-specific. |
| `pack_configuration` | Mandatory | Structured model for single packs, multipacks, and combos, including known quantity and packaging form. | Evidence: `500 ml`, `5 kg`, `2 x 750 ml`, and packs/combinations. |
| `consumer_substitution_notes` | Optional and future-governed | Holds explicitly approved compatibility constraints only when a future policy supports them. It must not infer substitution equivalence from title similarity. | Research: optimization needs allowed substitutions; false matches are a primary risk. |
| `lifecycle_status` | Mandatory | Distinguishes active, discontinued, superseded, and unknown variants while retaining historical links. | Research: pack/reformulation changes require history. |
| `catalog_revision` | Mandatory | Versions the exact pack/variant assertion independently of the parent Product. | Research: traceability and reversible decisions. |
| `evidence_references` | Mandatory collection | Records the evidence supporting the variant and pack interpretation. | Evidence corpus: quantity/title ambiguity requires traceable claims. |
| `effective_period` | Optional initially, expected later | Supports reformulations, label changes, and packaging changes without identity overwrite. | Research: time-aware catalog history. |

### Required Supporting Value Structures

The following structures are part of the conceptual schema because they remove ambiguity from the fields above:

| Structure | Required contents | Reason |
| --- | --- | --- |
| `brand_reference` | canonical brand identifier or explicit unknown/unbranded state, display label, alias/evidence linkage | Avoids conflating a raw platform spelling with a canonical brand. |
| `attribute` | controlled name, value, optional qualifier, role (`identity_critical` or `descriptive`), assertion status, evidence references | Keeps category-dependent semantics explicit and reviewable. |
| `measurement` | numeric value, unit, measurement dimension, content basis, assertion status | Represents quantity without using a display string as the canonical value. |
| `pack_configuration` | pack kind, count, per-unit measurement, total declared content, packaging form, components, completeness status | Handles single packs, multipacks, and combos without false equivalence. |
| `evidence_reference` | durable source identifier, source type, capture/decision reference, assertion role | Connects catalog claims to evidence without embedding a local file path as identity. |
| `category_reference` | category identifier/path, taxonomy version, confidence or review state | Allows category classification to evolve as additional platforms are sampled. |

### Derived Fields For Later Phases

The following should be derived or evaluated later. They are intentionally not primary canonical identity fields:

- normalized search tokens and alternate display labels
- identity fingerprint or matching signature
- barcode/GTIN confidence and identifier precedence resolution
- total comparable content and unit-price denominator
- product-to-product substitution compatibility
- category confidence and full category path
- match confidence from a Platform Listing to a Product Variant
- price-per-unit, discount amount, and reference-price interpretation
- offer eligibility, true cart cost, membership effects, and optimizer preference scores

The distinction matters: derived data can be recalculated as policies improve; canonical identity assertions and raw evidence require revision and traceability.

## 6. Future Compatibility Review

### Cross-Platform Matching

The schema supports matching because it keeps the attributes needed to decide equivalence separate from platform-specific title noise:

- brand reference constrains candidates
- product type provides an early candidate boundary
- structured identity attributes retain material differences such as milk type, grain type, flavor, or shampoo treatment
- pack configuration distinguishes `500 ml`, `1 L`, `2 x 750 ml`, and combinations
- evidence references and status fields permit uncertain links and manual review

Risk remains where data is incomplete, brands are absent, titles are ambiguous, or platforms omit pack details. Future matching must support `unresolved` and `ambiguous` outcomes rather than require a canonical link for every listing.

### Price Comparison

Price comparison can use a listing's matched Product Variant and structured pack configuration to determine whether two listings are exact matches or comparable alternatives. Price itself remains on Listing Observations.

The model deliberately prevents two mistakes:

- treating a `2 x 750 ml` pack as automatically interchangeable with a single `1.5 L` product
- comparing prices across unknown or materially different formulations solely because their titles share a brand and product type

Future work will need a clear policy for exact variant comparison, unit-level comparison, and explicitly permitted substitutes. This document does not define that policy.

### Offer Evaluation

Offers should attach to Platform Listings, Listing Observations, cart contexts, or checkout scenarios, not Products. The canonical Product Variant provides the product scope against which an offer can later be evaluated, including multipack and combo boundaries.

The schema does not attempt to encode discounts, MRP, coupons, or membership pricing as product attributes because those facts are time- and context-dependent.

### Cost Intelligence

Cost intelligence requires line items that reference a Product Variant, a Platform Listing, and a specific Listing Observation or checkout scenario. The proposed schema supplies the stable product/pack identity needed to interpret line quantities while leaving fees, taxes, payment effects, memberships, and delivery conditions outside the catalog.

### Cart Optimization

Optimization needs to allocate requested Product Variants across platform listings while honoring user-approved substitutions, pack composition, availability, costs, and delivery constraints. The Product/Variant distinction supports a user request for a product family while allowing the system to select an exact pack variant only when the choice is explicit and explainable.

The major future risk is not missing fields; it is treating compatibility as identity. A `full cream` milk should not become an automatic substitute for `toned` milk, and a combo should not become a simple quantity equivalent without user-facing rules.

## Likely Future Extensions

The following extensions are plausible but are not justified as mandatory fields by the current evidence corpus:

- manufacturer, country/region of origin, and regulatory identifiers
- barcode/GTIN/UPC/EAN identifiers with source and trust level
- ingredients, allergens, nutrition, dietary certifications, and health claims
- shelf-stable/perishable classification, storage requirements, and shelf-life data
- product images and packaging revision identity
- regional formulation or label variants
- richer taxonomy and category-specific attribute vocabularies
- explicit component products for curated bundles and gift/combo packs
- consumer preference and substitution policy artifacts

Each should be added only when evidence and a downstream requirement establish its semantics. Prematurely making these universal mandatory fields would create low-quality null-heavy catalog records and encourage unsupported inference.

## Governance And Data-Integrity Requirements

The future implementation should preserve the following invariants:

1. Raw acquisition and extraction artifacts remain immutable and independently referenceable.
2. A canonical Product or Product Variant assertion has evidence references, revision metadata, and a clear state of certainty.
3. A platform listing may remain unresolved or ambiguous; absence of a match is valid data.
4. Mapping a listing to a canonical variant does not overwrite the raw platform listing or any historical observation.
5. Pack composition is not reduced to a scalar total when that would erase multipack or combo semantics.
6. Prices, availability, offers, fees, locations, sessions, and checkout outcomes remain observation/context data.
7. Catalog corrections are revisions or supersessions, not destructive edits that remove prior evidence.

## Implementation Boundary

This proposal defines the domain target only. It does not authorize or prescribe:

- unit normalization or conversion rules
- canonical category taxonomy values
- brand alias rules
- exact matching thresholds or scoring algorithms
- a database schema or persistence strategy
- Pydantic models, dataclasses, API contracts, or migrations
- offer, fee, cost, or optimization logic

Those decisions should follow an evidence-backed normalization policy, fixture coverage, and a deliberate matching-design phase.

## Recommendation

Adopt the Product and Product Variant split as Cartel's canonical catalog boundary. Treat Product Variant, not raw listing title, as the unit of exact cross-platform comparison. Preserve raw listing and observation evidence outside the catalog, and require revisioned evidence references for every canonical assertion.

This model is deliberately conservative. It captures the information the current research and Blinkit corpus show to be material, while keeping volatile platform behavior and uncertain semantics out of the foundation that future matching, offer evaluation, true-cost calculation, and cart optimization will depend on.
