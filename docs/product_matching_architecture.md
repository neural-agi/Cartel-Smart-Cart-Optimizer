# Cartel Product Matching Architecture

## Purpose And Scope

This document defines how Cartel should reason about whether platform-native grocery listings refer to the same canonical `Product` and `ProductVariant`.

It builds on the approved research, evidence corpus, canonical schema, product-intelligence domain model, pipeline, and component architecture. It defines decision boundaries, evidence use, uncertainty, review, and future extension points. It does not define normalization rules, algorithms, scores, thresholds, persistence, APIs, or machine-learning models.

The central constraint is that matching is an evidence-backed assertion, not a title-similarity result. A listing may remain unresolved indefinitely when available evidence cannot justify a canonical link.

## 1. Decision Model

Cartel must keep four facts distinct:

1. A `PlatformListing` is the platform's catalog identity, represented by its native identifier, raw title, raw quantity text, raw category text, and URL when available.
2. A `ListingObservation` is the time- and context-bound commercial state of that listing.
3. A `Product` is the canonical, platform-independent product family or formulation.
4. A `ProductVariant` is a consumer-distinct purchasable configuration of a Product, including material variant attributes and pack composition.

Matching produces assertions between the two hierarchies. It must never merge their ownership:

- Listing and observation evidence remains platform-native and immutable.
- Canonical records remain revisioned and evidence-backed.
- Prices, offers, availability, and session state do not establish product identity by themselves.
- An accepted mapping is revisable; raw evidence is not rewritten to fit it.

The normal target for exact cross-platform comparison is a mapped `ProductVariant`. A product-only mapping is useful but incomplete: it says the family/formulation is likely known while the purchasable pack is not yet established.

## 2. Product Identity Philosophy

### What It Means To Be The Same Product

Two listings represent the same `Product` when the available evidence supports the same stable consumer product family or formulation, independent of the currently displayed price, availability, and sellable pack size.

For the initial catalog, the strongest product identity statement combines:

- brand or an explicit unknown/unbranded state
- product type or family
- identity-critical formulation or subtype attributes
- a compatible category context when present

Identity-critical attributes are category-dependent. They include, where material, milk type such as `toned`, `full cream`, `A2`, or `lactose-free`; bread type such as `whole wheat`; rice grain type; chips flavour; and shampoo treatment/range. These are not cosmetic adjectives when they change what a consumer is buying or whether two items are substitutable.

### Example: Amul Taaza Toned Milk

`Amul Taaza Toned Milk 500 ml` and `Amul Taaza Toned Milk 1 L` should generally map to the same `Product` when the brand, product family, and identity-critical formulation agree. They should not map to the same `ProductVariant`, because the purchasable pack differs.

This distinction prevents two opposite errors:

- treating different sizes as unrelated products and losing product-family continuity
- treating different sizes as exact equivalents and comparing their prices as though the packages were identical

### Product Identity Is Not Substitution

Product identity must not be inferred from commercial or nutritional proximity. `Full Cream Milk` is not the same Product as `Toned Milk`; `Magic Masala` chips are not the same Product as salted chips; and a generic `whole wheat bread` should not be silently merged with another formulation merely because the brand and category align.

Potential future substitution relationships are separate, policy-governed assertions. They are not matching evidence and must not be used to manufacture identity.

### Descriptive Claims

Marketing claims can support review and retrieval but are not automatically identity-defining. `High Fibre`, `No Maida`, `Purifying`, and similar language may be material in a category, but the current corpus does not justify a universal rule. The matcher must preserve such text and defer its identity role to category-specific governance rather than discard it or assume it always creates a new product.

## 3. Variant Identity Philosophy

### What It Means To Be The Same ProductVariant

Two listings represent the same `ProductVariant` only when they represent the same consumer-distinct purchasable configuration of the same canonical Product.

Variant identity includes:

- the parent Product
- variant-level identity attributes when they differ from the product family
- pack kind: single unit, multipack, combo, or assortment
- consumer-unit count
- content per consumer unit when known
- total declared content when known
- packaging form when material
- component composition for combos and assortments

Variant matching is therefore stricter than Product matching. A listing can be product-mapped and variant-unresolved without being erroneous.

### Quantity And Pack Semantics

The matching architecture treats quantity evidence as structured, not as an interchangeable scalar.

| Observed configuration | Product relationship | Variant relationship | Required interpretation |
| --- | --- | --- | --- |
| `500 ml` and `1 L` of the same formulation | Usually same Product | Different variants | Different sellable pack sizes. |
| `1 L` and `1000 ml`, both confirmed as single units | Same Product | Potentially same variant | Unit expression may differ; equivalence still requires trustworthy pack interpretation. |
| `Pack of 2` and a single unit | Usually same Product | Different variants | Count is commercially material. |
| `2 x 500 ml` and one `1 L` container | Usually same Product | Different variants by default | Equal total content does not erase multipack semantics. |
| Combo containing different items | May involve one or more Products | Separate combo/assortment variant or unresolved | Component composition must be retained, not reduced to total content. |

`2 x 500 ml` should never become the same variant as a single `1 L` pack solely because arithmetic totals agree. The count, component structure, packaging, and offer eligibility may differ. Likewise, a combo must not be collapsed into an equivalent total weight or volume if that loses its included-item structure.

### Variant Boundaries

The system should regard the following as variant boundaries unless evidence and policy establish otherwise:

- changed net quantity or per-unit quantity
- changed count or multipack structure
- changed combo/assortment composition
- changed packaging form when it is consumer-material
- a pack-specific formulation or identity attribute

The architecture does not decide conversion rules, tolerated label variation, or category-specific packaging equivalence. Those remain future normalization and catalog-governance decisions.

## 4. Matching Workflow

The matching workflow should be staged, conservative, and auditable.

```text
Raw extracted listing
        |
        v
Evidence registration and intake validation
        |
        v
PlatformListing identity + ListingObservation assembly
        |
        v
Evidence preparation and candidate generation
        |
        v
Product match evaluation
        |
        +--> unresolved / ambiguous / conflicting --> review queue
        |
        v
Variant match evaluation
        |
        +--> unresolved / ambiguous / conflicting --> review queue
        |
        v
Audited canonical assertion update
```

### Stage 1: Evidence Preparation

Purpose:

- assemble an immutable matching evidence bundle without converting raw evidence into canonical truth
- establish the provenance required to interpret later decisions

Inputs:

- `PlatformListing` fields
- `ListingObservation` fields
- source artifact reference
- parser version
- capture timestamp and capture context
- any raw extraction warnings

Outputs:

- evidence bundle with durable references
- explicit indicators for absent, partial, or contradictory fields

Failure modes:

- missing source artifact or parser version
- incomplete title/quantity/category extraction
- conflicting raw fields from one extraction

Handling:

- preserve the observation where possible
- label evidence incompleteness
- prevent unsafe automatic assertion rather than synthesizing missing facts

### Stage 2: Candidate Generation

Purpose:

- produce a bounded, explainable set of plausible canonical Products and ProductVariants
- optimize recall, not final correctness

Inputs:

- prepared evidence bundle
- canonical brand, category, Product, and ProductVariant metadata
- permitted historical mapping evidence

Outputs:

- Product candidate set
- ProductVariant candidate set, scoped to candidate Products where possible
- rationale fragments describing why candidates entered the set

Candidate sources:

- exact or close raw title evidence
- brand evidence
- product-family evidence
- identity-critical attribute evidence
- category context
- pack and quantity signals
- trusted historical mapping patterns

Failure modes:

- no candidate because a brand/title is new or malformed
- excessive candidate set because evidence is generic
- historical mappings biasing the set toward an earlier mistake

Handling:

- allow an empty candidate set
- expose broad candidate sets as uncertainty, not a reason to force ranking
- retain the candidate-generation rationale and catalog version used

### Stage 3: Product Match Evaluation

Purpose:

- decide whether the listing belongs to a canonical Product family/formulation before considering an exact pack

Inputs:

- Product candidates
- raw title and category evidence
- brand and product-type evidence
- identity-critical attribute evidence
- supported historical mapping evidence
- provenance and extraction-quality indicators

Outputs:

- accepted Product assertion
- product-only provisional assertion when policy permits
- `unresolved`, `ambiguous`, `conflicting`, or `rejected` outcome
- evidence-specific rationale and review trigger where needed

Failure modes:

- same brand but distinct formulation
- similar titles with different flavour, grain, treatment, or dietary properties
- meaningful identity tokens hidden in noisy title content
- category mismatch or platform taxonomy drift

Decision boundary:

- Product matching must answer only the product-family/formulation question.
- It must not accept or reject an exact variant based solely on a price, offer, display order, or total quantity.
- It may accept a Product while deliberately leaving the variant unresolved.

### Stage 4: Variant Match Evaluation

Purpose:

- decide whether the listing maps to a specific consumer-distinct ProductVariant inside an accepted or provisional Product context

Inputs:

- accepted or provisional Product context
- candidate ProductVariants
- raw quantity text and title-derived quantity evidence
- pack-kind, count, packaging, and component evidence
- variant-level identity attributes
- evidence-completeness indicators

Outputs:

- accepted ProductVariant assertion
- `unresolved`, `ambiguous`, `conflicting`, or `rejected` variant outcome
- rationale and review trigger when needed

Failure modes:

- title quantity and dedicated quantity text disagree
- `1 L` and `1000 ml` may be equivalent wording but pack form is unknown
- multipack wording is incomplete or embedded in a title
- combo and multipack semantics are confused
- source evidence has no reliable quantity

Decision boundary:

- Variant matching must not infer a single-unit variant from a total quantity that could describe a multipack or combo.
- It must not collapse materially distinct packs for unit-price convenience.
- Where pack semantics are incomplete, the correct output is product-mapped and variant-unresolved, or review.

### Stage 5: Outcome Classification And Assertion Handoff

Purpose:

- classify the decision state and route it to either an audited assertion update or review

Inputs:

- Product decision
- Variant decision
- supporting evidence references
- decision rationale

Outputs:

- safe mapping-state transition
- review case request when needed
- assertion update request only for accepted outcomes

Allowed outcomes:

- `mapped`: Product and ProductVariant identity is accepted within the governing policy.
- `product_mapped_variant_unresolved`: Product identity is accepted while pack identity is not. This is a decision detail beyond the current `MappingStatus` enum, not a substitute for it.
- `unresolved`: evidence is insufficient or no defensible candidate exists.
- `ambiguous`: multiple candidates remain materially plausible.
- `conflicting`: evidence sources or trusted prior assertions disagree.
- `rejected`: a proposed candidate has been positively ruled out.

Only accepted outcomes may reach the Assertion Manager. All other outcomes remain evidence-bearing records and, where appropriate, enter review.

## 5. Evidence Hierarchy

Matching must distinguish evidence strength from evidence availability. Multiple weak signals do not automatically become strong proof, and visually convenient signals can be dangerous.

### Strong Evidence

Strong evidence is specific, stable, and directly relevant to identity:

- a trustworthy platform-native listing identifier consistently linked to an established canonical assertion
- manufacturer or barcode evidence with known provenance and appropriate verification, when legitimately available
- exact brand and product-family agreement combined with identity-critical attribute agreement
- explicit, reliable pack composition that agrees with a candidate variant
- repeated, independently captured evidence that is consistent and traceable
- a reviewed prior decision whose evidence remains applicable

Strong evidence still does not excuse a pack mismatch. A listing can strongly match a Product while failing to establish a ProductVariant.

### Supporting Evidence

Supporting evidence can narrow candidates or strengthen an otherwise coherent case, but should not independently prove identity:

- raw title token overlap
- canonical category agreement
- platform category path
- packaging form
- raw quantity text when clearly labeled
- recurring platform presentation patterns
- prior mapping consistency that has not been independently verified

### Weak Evidence

Weak evidence can help retrieval but should carry limited decision authority:

- general category membership
- broad title similarity
- display image resemblance
- display order or search-rank proximity
- common co-occurrence with a query
- a price range that appears typical for a category

### Dangerous Evidence

The following must not establish identity and should be recorded as context only:

- displayed selling price, reference price, discount percentage, offer text, or membership-price presentation
- availability state or an `ADD` control
- search query alone
- one unverified parser field whose semantic role is uncertain
- total quantity used to erase multipack or combo composition
- a generic brand/category match without formulation evidence
- a prior mapping that lacks rationale or portable provenance

The current Blinkit corpus makes these restrictions necessary. The second visual price is not reliably an MRP, `ADD` is only a UI signal, quantities may appear in title and field with different meanings, and multi-packs occur in observed listings.

### Evidence Precedence In Conflicts

When evidence conflicts, the system should not silently choose the most convenient representation. It should:

1. retain each raw source and its provenance;
2. record the conflict in the decision rationale;
3. favor the more direct and reliable evidence only when governance explicitly supports that precedence;
4. otherwise emit a conflicting or unresolved outcome and route the case to review.

## 6. Confidence Philosophy

### What Confidence Represents

Confidence should communicate the quality and agreement of evidence supporting a particular assertion in the current decision context. It is not a claim of objective truth, a probability guarantee, or a substitute for auditability.

At minimum, future confidence reporting should be interpretable in terms of:

- evidence specificity: does the evidence distinguish this candidate from nearby alternatives?
- evidence agreement: do brand, family, attribute, and pack signals point to the same candidate?
- evidence completeness: are required identity and pack facts actually present?
- provenance quality: can the decision be traced to source artifacts, parser version, and capture context?
- contradiction: does any reliable evidence disagree with the proposed mapping?
- decision scope: is the assertion product-level or exact-variant-level?

### Confidence Is Assertion-Scoped

There must not be one opaque confidence for an entire listing. Product and variant assertions have separate confidence contexts because their evidence differs.

For example, `Amul Taaza Toned Milk` may be strongly supported as a Product while its quantity text is incomplete. The Product assertion can be high confidence while the ProductVariant remains unresolved. Combining these into one number would hide the important uncertainty.

### Confidence Limitations

Confidence can be misleading when:

- a candidate set omitted the true product;
- repeated evidence comes from the same parser defect or platform artifact;
- historic mappings have propagated an earlier false positive;
- a sparse title appears highly similar to a familiar catalog record;
- category-specific identity semantics are not yet governed;
- the model treats commonness as correctness.

Future scoring should therefore be advisory to the architecture. It may determine automation eligibility under a reviewed policy, but it cannot bypass evidence preservation, contradiction checks, review triggers, or revisioned assertions.

### Overconfidence Guardrails

- Never infer certainty from title similarity alone.
- Never let a high product-level assessment imply a high variant-level assessment.
- Never auto-accept when material pack composition is absent, partial, or contradictory.
- Never use volume of historical mappings as proof without inspecting their evidence quality.
- Record which evidence was absent as well as which evidence agreed.
- Re-evaluate confidence when parser versions, catalog revisions, or source evidence change.

No numeric formula or automation threshold is specified here. Thresholds should be set only after representative, reviewed matching data exists across categories and platforms.

## 7. Ambiguity And Refusal Policy

Uncertainty is a valid output, not an exceptional error condition.

### Required States

`unresolved`

- No candidate has enough evidence to support a mapping.
- The candidate set may be empty, incomplete, or not yet curated.
- The listing and observation remain usable for future reprocessing.

`ambiguous`

- Two or more candidates remain materially plausible.
- Available evidence cannot distinguish them without guessing.

`conflicting`

- Evidence sources point toward incompatible identities or pack structures.
- A reliable prior mapping conflicts with newer evidence.
- Raw title, quantity, packaging, or platform identifiers disagree in a material way.

`rejected`

- A specific candidate has enough contrary evidence to be ruled out.
- Rejection applies to that candidate assertion, not necessarily to all possible canonical mappings.

### When The System Must Refuse To Match

Automatic matching must refuse to produce an accepted assertion when any of the following applies:

- brand or product family evidence is missing and candidate distinction depends on broad title similarity;
- identity-critical attributes conflict or are absent where they distinguish nearby products;
- the Product context is uncertain and would make a variant result arbitrary;
- pack configuration is incomplete, contradictory, or insufficient to distinguish candidates;
- a multipack, combo, or assortment might be flattened into a scalar quantity;
- the only apparent support is pricing, offer, availability, or category;
- extraction quality is suspect and the source artifact cannot resolve the uncertainty;
- a previous mapping has no auditable evidence or conflicts with current, reliable evidence.

Refusal does not block acquisition or observation storage. It blocks only canonical assertion updates.

### Product-Only Resolution

Product-only resolution is permitted when product-family/formulation evidence is sufficient but variant evidence is not. It must preserve the reason the variant is unresolved, for example missing count, unclear pack format, or incompatible quantity signals. It must not be presented downstream as an exact comparison-ready link.

## 8. Human Review Strategy

Human review is a formal control in the matching architecture, owned by the `Review Queue Manager` described in the component architecture. It is not a hidden manual override.

### Review Triggers

Create a review case when:

- product candidates are materially tied or cannot be distinguished;
- a Product is plausible but multiple variants fit the evidence;
- count, per-unit content, total content, or combo components are missing or contradictory;
- a significant identity attribute conflicts with the best candidate;
- trusted prior mappings conflict with a new observation;
- parser output appears inconsistent with the captured source artifact;
- a new brand, product family, or pack structure has no defensible canonical candidate;
- an automated decision is accepted only under a policy requiring sampled verification.

### Reviewer Evidence Bundle

Every review case must display or link to:

- raw title, raw quantity text, raw category text, and platform-native listing identifiers;
- listing URL when available;
- source artifact and capture context references;
- parser version, extraction timestamp, and extraction warnings;
- raw displayed/reference price, offer text, and availability only as contextual evidence;
- all candidates considered and why each candidate was generated;
- product and variant evaluation rationale, including missing and conflicting evidence;
- relevant historical mappings, revisions, and prior review outcomes;
- the catalog revision used for the decision.

The reviewer must be able to examine the original evidence without relying on a summary generated by the matcher.

### Review Outcomes

Review may:

- accept Product and ProductVariant mappings;
- accept Product only and leave ProductVariant unresolved;
- reject one or more candidate mappings;
- request a new Product or ProductVariant through governed catalog curation;
- mark evidence as insufficient and request recapture or better extraction;
- supersede a previous assertion through a revisioned, auditable decision.

Review must not alter raw listing evidence, change past observations, or convert an uncertain visual price into identity evidence.

### Audit Requirements

The `Decision Audit Recorder` must retain:

- the matching input evidence bundle;
- candidate set and candidate-generation rationale;
- product and variant decision outputs;
- reviewed policy/version context when present;
- review actions, reviewer identity when available, and timestamps;
- resulting assertion state, supersession links, and evidence references.

This audit trail is necessary for reprocessing after parser changes, catalog corrections, or later matching-policy improvements.

## 9. Future Evolution Without Architectural Redesign

The architecture is intentionally independent of matching technique.

### Deterministic Matching

Deterministic rules can later operate inside candidate generation and the Product/Variant Matcher components. They consume the same raw evidence bundle and produce the same decision/rationale contract. This is appropriate for trusted identifiers, governed aliases, and explicitly structured pack facts.

### Heuristic Matching

Heuristics can later expand candidate retrieval or evaluate agreement across title, brand, attributes, category, and pack evidence. They must continue to return candidate-specific rationale and honor refusal conditions. Heuristics may improve recall, but they do not change the assertion, audit, or review boundaries.

### Confidence Scoring

Confidence scoring can enrich decision outputs with evidence-quality and agreement assessments. It should be versioned and retained in the audit trail. It must remain separate for Product and ProductVariant assertions and should not hide missing or conflicting evidence.

### Machine-Learning Assistance

ML may later rank candidates, identify likely attributes, or propose review priorities after Cartel has labeled, provenance-rich data. It should be treated as an input to the same candidate and matcher contracts, not as an authority that directly rewrites canonical records. Human review, durable evidence, and assertion revisioning remain unchanged.

### Cross-Platform Comparison

New platforms enter through their own listing and observation evidence. Their titles, categories, and identifiers may differ, but the matching architecture continues to target the same canonical Product and ProductVariant boundaries. Exact comparison is permitted only for accepted ProductVariant mappings; product-family comparisons and substitution comparisons must remain explicitly labeled as such.

### Reprocessing And Policy Change

As parsers, normalization policy, catalog coverage, or matching methods improve, Cartel must be able to rerun matching from retained raw evidence. Decision records should identify the parser version, catalog revision, and future matcher/policy version used. A new result supersedes an earlier assertion through revision history; it does not erase the prior decision or source evidence.

## 10. Architectural Invariants

1. A platform listing can be unresolved, ambiguous, conflicting, or rejected without being invalid data.
2. Product identity and ProductVariant identity are separate assertions with separate evidence and uncertainty.
3. Pack composition is not reduced to total content when count, multipack, combo, or assortment semantics would be lost.
4. Price, reference-price text, offers, availability, and session state are not canonical identity fields.
5. Candidate generation is recall-oriented; match evaluation is correctness-oriented; assertion updates are evidence- and audit-gated.
6. Raw evidence, parser provenance, capture context, candidate rationale, and review history remain referenceable after every decision.
7. Automated matching may decline to decide. Lack of a match must never be silently converted into a weak canonical assertion.
8. Corrections are revisioned assertions or supersessions, never destructive rewrites of raw listing and observation evidence.

## Bottom Line

Cartel should reason about grocery identity in two steps: first identify the stable Product family/formulation, then identify the exact ProductVariant pack configuration. The system should use evidence hierarchically, keep product and variant confidence separate, and refuse automatic mapping when identity-critical or pack semantics are incomplete, ambiguous, or contradictory.

This design allows deterministic rules, heuristics, confidence scoring, and eventual ML assistance to improve matching without changing the core guarantees: raw evidence is preserved, uncertainty remains visible, review is explainable, and only audited assertions can become canonical product intelligence.
