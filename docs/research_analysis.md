# Cartel Research Analysis

## Scope And Evidence

This review assimilates the consolidated research report and the repository state observed on 2026-06-20. It is an architecture and sequencing review, not an implementation design.

### Current-State Observations

- The repository has one operational acquisition path: Blinkit search via Playwright after direct HTTP is blocked by `403`.
- A browser session is location-aware, persists state locally, and captures rendered HTML plus request metadata.
- A Blinkit-specific parser extracts 24 product cards from the saved `milk` page into raw structured JSON. The current fields are name, visual price strings, a second visual price called MRP, quantity text, stock inferred from `ADD`, offer text, and raw card text.
- There is no product catalog, normalizer, matcher, offer evaluator, fee model, price-history store, checkout observation model, database, or optimizer.
- The current output is useful evidence, not yet a durable domain contract. In particular, `source_path` is machine-local, the parser assumes a second price is MRP without a visible semantic label, and `ADD` is only a UI availability signal rather than inventory truth.

## 1. Architectural Implications

### Validated Conclusions

- **Raw acquisition and extraction must remain separate.** The existing Blinkit scraper/session/parser split already follows the correct boundary. Raw HTML and raw extracted fields must remain reproducible inputs for later interpretation.
- **Location and session are first-class acquisition context.** The rendered search result changes only after delivery location is established. A listing cannot be treated as a global price; it is an observation for a location, time, session, and platform context.
- **Cartel needs a cart-level cost model.** Research consistently shows that item price is insufficient once delivery, handling, platform, small-cart, surge, packaging, payment, subscription, and deferred-benefit effects are included.
- **Deterministic rules and fuzzy intelligence need different boundaries.** Fee computation and offer applicability require auditable rule evaluation. Product identity resolution is inherently uncertain and needs confidence-aware matching rather than deterministic string equality.

### Invalid Or Unsafe Assumptions

- A displayed selling price is not a comparable or final price.
- A second crossed-out or adjacent price cannot automatically be treated as MRP. It may be an original selling price, a member price comparison, or a platform-specific reference price unless the UI supplies a label.
- `ADD` does not prove inventory quantity, checkout availability, or eligibility for a specific delivery slot.
- A single successful `milk` extraction is not evidence that the parser contract generalizes across categories, stores, locations, sessions, UI experiments, or platforms.
- A persistent browser-state file is not a reusable consumer identity. It is a volatile, potentially sensitive acquisition artifact and must eventually be isolated by intended session scope.

### Architectural Risks And Hidden Complexity

- **Observation drift:** prices, fees, availability, and offers can change within hours or between page load and checkout.
- **Personalization drift:** guest/logged-in state, device, location, time, payment method, membership, and first-order status can affect outcomes.
- **UI/parser drift:** the current Blinkit parser depends on rendered card order and `ADD`/price markers. Platform DOM changes and experiments will cause silent semantic errors unless extraction quality is measured.
- **Checkout-only facts:** many fees and offer constraints appear only after cart assembly, address selection, payment selection, or slot selection. Search-page data cannot support a true-cost claim by itself.
- **Acquisition fragility and compliance:** direct HTTP is already blocked. Browser automation, session state, rate limits, and location automation require platform-specific resilience, retention limits, and an explicit legal/compliance review before scaling.
- **Provenance portability:** the generated output includes an absolute source path from another machine context. Future observations need portable source identifiers plus capture context, rather than relying on local paths as durable references.

### System-Boundary Implications

Keep these boundaries explicit:

1. Acquisition/session: fetch rendered or API evidence and record capture context.
2. Extraction: turn platform evidence into platform-native fields without assigning cross-platform meaning.
3. Product intelligence: normalize, identify candidates, match, score confidence, and preserve decisions/reasons.
4. Cost intelligence: evaluate line items, fees, offers, memberships, and deferred value deterministically against an explicit context.
5. Optimization: compare feasible carts using cost intelligence outputs plus user inconvenience preferences.

Scalability concerns follow from these boundaries: multi-platform collection multiplies session/location combinations; price history grows by listing-location-time observations; candidate matching grows faster than listings without blocking and retrieval; and cart optimization becomes combinatorial as platforms, offer choices, and split orders increase.

## 2. Canonical Product Catalog Implications

The canonical catalog must represent an abstract purchasable product or variant, not a platform listing. A listing is an observation of that product under one platform/context.

### Mandatory Canonical Information

- Stable canonical product and variant identity.
- Brand and brand aliases.
- Product family/category and a category path with provenance.
- Product form/type, such as toned milk, full-cream milk, lactose-free milk, or UHT milk.
- Pack composition: net quantity, unit dimension, count/multipack structure, and per-item quantity when present.
- Variant-defining attributes: flavor, fat/strength, dietary claims, packaging/form factor, shelf-life classification when material, and bundle composition.
- Identity evidence, confidence, version/effective period, and human-review status. Repackaging, reformulation, and bundle changes must not overwrite history.

### Platform-Specific Information That Must Stay Outside The Catalog

- Platform product/listing ID and URL.
- Raw title, raw quantity text, raw category, image, and descriptions.
- Selling price, visual reference/MRP text, availability UI state, ETA, display order, and platform-specific badges.
- Location, capture time, session/membership/payment context, and extraction confidence.
- Platform offer wording and UI claims.

### Matching Challenges Already Visible

- "Amul Taaza Toned Milk" appears at several sizes; title similarity alone would collapse distinct variants.
- A name can contain quantity-like text, for example "25 g High Protein," which is not the pack size.
- Multipacks such as "Pack of 2" and `2 x 200 ml` require composition-aware identity rather than a single scalar quantity.
- Terms such as full cream, toned, skimmed, lactose-free, A2, UHT, and high-protein are commercially material; treating them as optional adjectives will create false matches.
- Brand spelling, abbreviations, category paths, and bundle labels will vary between platforms.

Essential comparison attributes are brand, product family, variant-defining attributes, normalized pack composition, and a traceable link back to each raw listing. Barcode/GTIN should be used when legitimately available, but it cannot be assumed to cover all quick-commerce listings.

## 3. Product Normalization Implications

### Normalize Later, Preserve Now

Future normalization should cover text whitespace/case, brand aliases, category mapping, quantity/unit expressions, pack composition, numeric price values, and explicit availability states. It should produce derived fields alongside untouched raw evidence.

Raw values that should remain immutable include the original title, quantity string, all price labels/text, visual badges, raw card text, source artifact reference, capture timestamp, location/session context, and parser version.

### Likely Ambiguities

- `1 ltr`, `1 litre`, `1000 ml`, and `2 x 500 ml` can be equivalent only after pack composition is understood.
- A reference price may be MRP, prior selling price, membership comparison, or promotional anchor.
- "Combo", "pack", "free", and "off" can describe distinct commercial structures.
- Category hierarchy can be inconsistent between platforms.
- UI availability can mean in stock, addable now, deliverable later, or limited to a selected store.

### High-Risk Mistakes

- Collapsing multipacks into single-pack equivalents without retaining count.
- Treating all size expressions as net quantity when they occur in the name.
- Removing meaningful variant descriptors during text cleanup.
- Normalizing a visually adjacent price into MRP without label evidence.
- Converting a UI `ADD` control into a durable stock quantity.

### Decisions To Defer

Do not finalize category taxonomy, brand alias policy, unit conversion edge cases, reference-price semantics, or equivalence thresholds from a single platform/category. Gather multi-category, multi-location, and multi-platform samples first; publish a normalization policy and fixtures before producing canonical data.

## 4. Offer Engine Implications

### Offer Types

Research supports item-level flat and percentage discounts, BOGO/BXGY, bundles/combo offers, cart-threshold discounts, free delivery, coupons, bank/payment offers, wallet cashback, subscription benefits, first-order offers, loyalty points, and near-expiry/clearance promotions.

### Required Future Rule Inputs

An offer needs a trigger, benefit, validity window, target scope, caps, redemption limits, code requirement, eligibility cohort, payment/membership requirements, stacking/exclusivity behavior, and source/verification evidence. Benefits must distinguish immediate out-of-pocket reduction from deferred/restricted value.

### Cart Dependencies

Offer applicability can depend on cart subtotal, eligible items/quantities, store/location, delivery slot, new-user state, membership, payment method, coupon choice, prior usage, and competing offers. Application order matters: item effects, cart effects, payment effects, and deferred rewards are not interchangeable.

### Platform-Specific Versus Reusable

Platform-specific adapters should capture raw offer language, UI placement, eligibility signals, and checkout behavior. A platform-agnostic evaluator can later model trigger, benefit, validity, scope, cap, and stacking semantics. The evaluator must preserve unknown or unsupported semantics rather than silently approximate them.

## 5. Cost Intelligence Implications

### True-Cost Components

True immediate cost includes product lines plus delivery, handling/convenience, platform, small-cart, packaging, surge/rain, bulk-order, quick-delivery, and tax-on-fee components, less immediate item/cart/coupon/payment/subscription/points reductions. Deferred cashback and loyalty value should be modeled separately from immediate payable cost.

### Hidden Variables

Fees and benefits may vary by delivery location/store, time/slot, cart value, basket composition, membership, payment rail, new-versus-existing user status, coupon use, and offer eligibility. Loss leaders and threshold nudges mean a cheap SKU can raise total cost when it changes cart behavior.

### Modeling Implication

Cost intelligence needs an explicit evaluation context and a checkout-observation evidence layer. It cannot infer all fee rules from rendered search cards. It must return a breakdown, assumptions, unknown inputs, and freshness/capture time, not only a total.

## 6. Cart Optimization Implications

Product-level comparison fails because fees, thresholds, offers, availability, and benefits couple items together. The correct decision is the feasible allocation of requested items across one or more platforms.

Future optimization dimensions include:

- Item equivalence and allowed substitutions.
- Location-specific availability and fulfillment constraints.
- Per-platform checkout cost under fee and offer rules.
- Offer/coupon/payment/membership eligibility and mutually exclusive choices.
- Delivery count, timing, and user-defined inconvenience penalty.
- Freshness of observations, minimum confidence, and user budget/preferences.

The difficult cases are threshold discontinuities, bundle/BXGY constraints, split-order combinations, limited stock, mutually exclusive offers, deferred-value tradeoffs, and uncertain product matches. A split should be recommended only when explainable savings exceed a stated hassle threshold; the optimizer must return the math and assumptions.

## 7. Data Model Implications

These are domain entities, not a database design.

| Entity | Why it exists |
| --- | --- |
| Product | Canonical, versioned representation of an equivalent consumer product/variant. |
| Product Variant / Pack Composition | Separates material size, count, bundle, and variant attributes from generic product identity. |
| Brand | Supports aliases and brand-level matching constraints. |
| Category | Captures canonical classification while retaining platform category observations. |
| Platform Listing | Represents a platform-native product identifier/title/URL and its mapping status. |
| Listing Observation | Captures price, availability, raw fields, time, location, session context, parser version, and provenance without overwriting history. |
| Capture Context | Represents location/store, session cohort, device/guest state, and other conditions that affect a listing observation. |
| Product Match Decision | Stores candidate links, confidence, reasons, reviewer action, and mapping version for auditability. |
| Offer | Represents an observed promotion and its trigger, benefit, scope, validity, caps, and evidence. |
| Fee Rule / Fee Observation | Separates reusable fee semantics from observed checkout charges and their contexts. |
| Membership Benefit | Models subscription or loyalty entitlements separately from general offers. |
| Cart | Represents requested quantities, substitutions, and user intent. |
| Checkout Scenario | Represents a platform/cart/context evaluation used to calculate true cost. |
| Cost Breakdown | Records all payable and deferred components with assumptions and freshness. |
| Optimization Result | Preserves a recommended allocation, alternatives, rationale, and inputs for explainability/debugging. |
| User Preference | Holds explicit inconvenience, budget, membership, payment, and substitution preferences needed for personalized optimization. |

## 8. Recommended Development Order

1. **Define observation and extraction contracts, then build fixture coverage.**
   - Why next: the current parser is only validated on one Blinkit search/category/page shape.
   - Unlocks: reliable acquisition/extraction quality measurement and safe later normalizer input.
   - Risk reduced: silent parser regressions, absolute-path provenance, misclassified MRP/stock, and UI drift.

2. **Gather a representative raw evidence corpus before defining normalization policy.**
   - Why next: unit, category, offer, and reference-price semantics cannot be safely inferred from milk alone.
   - Unlocks: evidence-based normalization specification and test fixtures across categories, locations, and repeated captures.
   - Risk reduced: premature equivalence rules and irreversible semantic loss.

3. **Specify and implement a conservative product-intelligence layer.**
   - Why next: cross-platform comparison requires stable product identity before price comparison has meaning.
   - Unlocks: canonical catalog, deterministic candidate generation, confidence-scored matching, and a manual-review path.
   - Risk reduced: false matches, especially across pack sizes, bundles, and meaningful variants.

4. **Introduce durable, append-only observation storage and provenance.**
   - Why next: product intelligence, volatility analysis, and checkout reconciliation require historical observations.
   - Unlocks: price history, parser-version audits, reprocessing, freshness logic, and multi-platform comparison.
   - Risk reduced: overwriting raw truth and losing the context required to explain a result.

5. **Build checkout evidence collection and an offer/fee taxonomy before a cost engine.**
   - Why next: search-page prices cannot calculate true cart cost.
   - Unlocks: deterministic fee/offer evaluation from observed, attributable facts.
   - Risk reduced: presenting unsupported or misleading savings claims.

6. **Implement deterministic true-cost scenarios with explicit unknowns.**
   - Why next: optimization requires trustworthy per-platform cart costs first.
   - Unlocks: explainable single-platform comparisons and checkout reconciliation.
   - Risk reduced: hard-coded offer logic and accidental mixing of immediate versus deferred value.

7. **Add a second platform only after the contracts above are stable.**
   - Why next: multi-platform data is valuable only when it is comparable and traceable.
   - Unlocks: real catalog matching validation and initial cross-platform cost comparisons.
   - Risk reduced: multiplying scraper-specific assumptions into the core model.

8. **Create a bounded, explainable cart optimizer.**
   - Why next: it consumes canonical matches and true-cost scenarios rather than raw prices.
   - Unlocks: one-platform versus limited split-order recommendations with a configurable hassle penalty.
   - Risk reduced: combinatorial growth and untrusted recommendations.

9. **Use ML only after labeled matching and historical data exist.**
   - Why later: the research supports ML for fuzzy matching, prediction, and personalization, not deterministic fee/offer logic.
   - Unlocks: semantic reranking, price/offer forecasts, and personalization with measurable quality.
   - Risk reduced: training on noisy, semantically unstable observations.

## Documentation Gaps To Address Later

- Acquisition contract: artifact identity, capture timestamp, location/session scope, freshness, and retention rules.
- Extraction contract: parser version, field confidence, visual-label evidence, and known unsupported card states.
- Normalization policy: raw-versus-derived fields, unit/pack semantics, category policy, and non-destructive transform history.
- Matching decision policy: confidence thresholds, review workflow, versioning, and rollback.
- Checkout observation protocol: how fees/offers are captured and verified without conflating assumptions with facts.
- Cost explanation contract: immediate payable total, deferred value, unknowns, and user-visible rationale.
- Session/privacy policy: storage, isolation, expiry, access control, and deletion of browser state containing potentially sensitive data.

## Bottom Line

Cartel's current raw acquisition and extraction work is a valid foundation, but it is not yet a price-comparison system. The next architectural objective is a traceable product-intelligence foundation that preserves raw evidence, models identity uncertainty, and postpones cost/offer claims until checkout-context evidence exists. This sequencing protects the core promise of Cartel: explainable true-cost decisions rather than visually plausible but unsupported comparisons.
