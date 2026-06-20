# Cartel Blinkit Evidence Corpus Analysis

## Scope

This report analyzes the Blinkit evidence corpus collected for these categories:

- Milk
- Bread
- Rice
- Atta
- Biscuits
- Chips
- Soft Drinks
- Shampoo

Each category was acquired through the existing Blinkit browser fallback pipeline with location-aware session handling, then persisted as:

- raw rendered HTML under `data/raw/blinkit/`
- structured extraction JSON under `data/cleaned/blinkit/`
- acquisition metadata alongside each raw HTML artifact

The corpus is useful because it spans multiple grocery classes with different packaging, naming, and price-display behavior. It is not yet broad enough to define final normalization policy, but it is sufficient to identify recurring patterns and early parsing risks.

## Corpus Snapshot

Observed latest corpus files for the requested categories:

- `milk` -> 24 extracted products
- `bread` -> 24 extracted products
- `rice` -> 24 extracted products
- `atta` -> 24 extracted products
- `biscuits` -> 24 extracted products
- `chips` -> 24 extracted products
- `soft drinks` -> 24 extracted products
- `shampoo` -> 24 extracted products

Across this sample:

- all extracted items were marked `in_stock`
- every category produced a populated rendered results page
- the parser consistently found 24 candidate product cards per category
- the current extraction output is still a raw evidence layer, not a normalized catalog layer

## Quantity Patterns

The corpus shows that quantities are embedded in several different forms:

- single unit values: `500 ml`, `1 ltr`, `1 kg`, `350 g`
- larger packs: `5 kg`, `10 kg`
- bundled packs: `2 x 750 ml`
- non-round pack sizes: `89 g`, `959.1 g`
- category-specific unit variation: liquids appear as `ml`/`ltr`, solids as `g`/`kg`

This is already enough to show that quantity cannot be treated as a single canonical string later. The same logical amount may appear as:

- `1 ltr`
- `1 L`
- `1000 ml`

The current corpus also shows that multi-pack expressions are not rare; they occur in soft drinks and will likely matter in other categories as the corpus grows.

## Product Naming Patterns

Product names are not clean catalog names. They frequently combine multiple semantic layers:

- brand prefix: `Amul`, `Daawat`, `Lay's`, `L'Oréal`
- product family: `Milk`, `Bread`, `Basmati Rice`, `Potato Chips`
- variant or subtype: `Toned`, `Full Cream`, `Medium Grain`, `Keratin Smooth`
- marketing claim: `100% Atta, 0% Maida`, `No Maida`, `High Fibre`, `Purifying`
- flavor descriptor: `Cream & Onion`, `Pudina Treat`, `Magic Masala`
- pack information sometimes inside the title itself: `Coca-Cola Soft Drink (750 ml) - Pack of 2`

Two important observations follow from this:

1. Titles are not just names; they are composite evidence strings.
2. The same semantic attribute may appear in the title, quantity field, or both.

That means future matching and normalization must treat product names as noisy evidence, not as canonical truth.

## Pricing Patterns

The parsed corpus shows several pricing shapes:

- single display price only
- display price plus a second price interpreted as MRP-like reference
- explicit discount text in the listing
- products with no visible discount even when a second price exists

Examples from the sample:

- milk often shows only a single price, such as `₹30`
- bread may show `₹59` and `₹65`
- rice often shows both a current price and a higher reference price
- shampoo follows the same pattern on premium products

Important implications:

- the second price is not guaranteed to be a true MRP in every case
- the current extraction logic treats the first price as `displayed_price` and the second as `mrp`
- that heuristic is useful for evidence capture, but it is not a final pricing rule

The corpus also shows that displayed price alone is insufficient for later true-cost evaluation, because promotions and reference pricing are mixed into the same listing surface.

## Offer Patterns

Offer text in the current corpus is mostly percentage-based:

- `5% OFF`
- `7% OFF`
- `8% OFF`
- `12% OFF`
- `32% OFF`
- `49% OFF`

Observed offer behavior:

- percentage discount text is common
- some products with a second price do not show explicit offer text
- the parser does not yet observe bundle or stackable checkout offers

From this corpus alone, the following offer types are not yet directly evidenced in the extracted product cards:

- flat coupon discounts
- buy X get Y
- free item promotions
- membership-only price deltas
- cart-level threshold offers

Those may exist on the platform, but they are not yet visible in this acquisition slice and should not be assumed into the model prematurely.

## Availability Patterns

Availability is currently simple in the extracted corpus:

- `ADD` is present for all observed product cards
- all extracted records were tagged `in_stock`
- no `out_of_stock` or `unavailable` cases were observed in this run

This means the current sample is biased toward purchasable catalog items. It does not yet validate how Blinkit presents:

- out-of-stock cards
- waitlist or notify-me states
- limited-quantity warnings
- location-specific non-availability

Those edge cases remain important for later parsing and cart logic, but they are not represented in the present corpus.

## Category-Level Observations

### Milk

- quantities are mostly `500 ml` and `1 ltr`
- names include brand plus milk type, such as `Toned`, `Cow`, `Buffalo A2`, `Full Cream`
- prices are often single-value only

### Bread

- quantity usually appears as `350 g`, `450 g`, or `700 g`
- some cards show both current and reference pricing
- claims such as `100% Atta`, `No Maida`, and `Whole Wheat` appear in titles

### Rice

- packaging is mostly `1 kg` and `5 kg`
- titles frequently include grain type and quality descriptors
- many cards show explicit percentage discounts plus reference pricing

### Atta

- quantity is dominated by `5 kg` and `10 kg`
- the same base product may appear in multiple pack sizes
- marketing claims are embedded directly in the title and must not be collapsed too early

### Biscuits

- quantities vary widely, including small retail packs and odd weights
- flavor and biscuit style are tightly coupled in titles
- offer density is high relative to milk and bread

### Chips

- flavor descriptors are central to identity
- pack weights are small and often similar across SKUs
- brand and flavor separation will matter for matching

### Soft Drinks

- multi-pack notation is visible in product titles and quantity fields
- this category is a useful early signal that pack math will matter
- brand, flavor, and package count all influence identity

### Shampoo

- premium brands show both display price and reference price frequently
- claims and treatment terms are prominent
- quantity is typically `180 ml`, `200 ml`, `250 ml`, or `300 ml`

## Parsing Risks

The corpus reveals several weaknesses in the current extraction approach.

### 1. Quantity ambiguity

Quantity may appear:

- in the title
- as a standalone token
- in a bundled form
- in both title and separate field

This makes a simple positional parse fragile.

### 2. Price-role ambiguity

The current parser assumes:

- first price token = displayed price
- second price token = MRP

That is a reasonable evidence heuristic, but it is not guaranteed to be semantically correct for every card.

### 3. Title boundary ambiguity

The parser currently relies on token ordering around price and `ADD` text. That works for the observed corpus, but it could fail when:

- the card layout changes
- the title contains extra marketing copy
- the card has more than two prices
- quantity is embedded inside the title string

### 4. Offer ambiguity

Offer text is currently captured only when the parser sees obvious discount language in the card text. That means:

- coupon offers may be missed
- stackable offers may be missed
- threshold offers will almost certainly need dedicated checkout or promotion-page evidence

### 5. Availability overfitting

Every observed item is `in_stock`, so availability logic is not yet stress-tested.

### 6. Provenance drift

The raw extraction records preserve source paths and timestamps, but the sample shows that provenance is only as trustworthy as the surrounding file-management discipline. Future phases should ensure source metadata remains stable across machines and environments.

## What This Corpus Supports

This corpus is already good enough to justify the following future design decisions:

- canonical product identity must be separate from raw listing text
- quantity should be modeled as structured evidence, not a single string
- pricing should retain both displayed and reference values
- offer modeling will need more than simple discount text
- availability should remain a first-class observation
- product matching must tolerate title noise, pack size variation, and flavor/variant overload

## What It Does Not Yet Support

This corpus does not yet justify final decisions about:

- normalized unit conversion rules
- canonical product hierarchy
- cross-platform matching thresholds
- offer stacking semantics
- fee or surcharge modeling
- cart optimization constraints

Those should wait for more evidence from additional platforms and, ideally, checkout-level or cart-level observation.

## Recommended Next Documentation Additions

The analysis suggests the following future documents should exist once the project moves into product intelligence:

- a canonical product schema note
- a quantity normalization policy note
- an offer taxonomy note
- a true-cost component glossary
- a cross-platform evidence sampling plan

## Bottom Line

The Blinkit corpus confirms that Cartel is dealing with noisy retail evidence, not clean catalog data. Quantity, title, price, and offer information are all entangled at the listing level, and the same product family appears in multiple pack and variant forms. The current acquisition and extraction pipeline is strong enough to build a representative evidence corpus, but the evidence clearly argues for conservative normalization, explicit provenance, and later-stage decision logic rather than early canonical assumptions.
