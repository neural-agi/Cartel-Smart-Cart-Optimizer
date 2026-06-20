# Product Intelligence Design

## Domain Boundaries

Cartel's product-intelligence layer is split into two separate hierarchies:

1. `Product` -> `ProductVariant`
2. `PlatformListing` -> `ListingObservation`

The first hierarchy is canonical and platform-independent. The second hierarchy is platform-native and time-bound.

`Product` represents the stable grocery product family: brand, product type, identity-defining attributes, category reference, lifecycle state, and evidence. `ProductVariant` represents the consumer-distinct purchasable configuration of that product, including pack structure and quantity semantics.

`PlatformListing` represents a listing as it exists on a source platform. `ListingObservation` captures what was observed on that listing at a specific time, including price, reference price, offer text, availability signal, parser version, and source artifact reference.

## Responsibility Separation

### Product

Belongs here:

- canonical identity
- brand reference
- product family or type
- identity-critical attributes
- descriptive attributes that support review and search
- category reference
- lifecycle status
- evidence references

Does not belong here:

- raw platform titles
- listing URLs
- prices
- offers
- stock state
- session or capture context
- platform IDs

### ProductVariant

Belongs here:

- variant-specific identity
- pack configuration
- quantity structure
- component composition for combos and assortments
- lifecycle status
- evidence references

Does not belong here:

- prices
- offers
- availability
- platform metadata
- capture-time state

### PlatformListing

Belongs here:

- platform name
- platform listing identifier
- raw title
- raw quantity text
- raw category text
- listing URL
- mapping status

Does not belong here:

- displayed price
- reference price
- offer text
- availability signal
- canonical identity assertions

### ListingObservation

Belongs here:

- displayed price
- reference price
- offer text
- availability signal
- capture timestamp
- parser version
- source artifact reference
- capture context reference

Does not belong here:

- canonical product identity
- variant identity
- platform-native listing fields that do not change across captures

## Future Evolution

These entities create the stable nouns required for future product-intelligence work without implementing that work now.

- Normalization can later map noisy platform text into `Product` and `ProductVariant` assertions while preserving raw evidence.
- Matching can later link `PlatformListing` records to the correct `ProductVariant` with confidence and review states.
- Cross-platform comparison can later compare like-for-like variants instead of raw titles or arbitrary listing cards.
- Cost intelligence can later combine `PlatformListing`, `ListingObservation`, and cart context to evaluate true spend.
- Cart optimization can later allocate user demand across platform listings while respecting pack structure, availability, and price observations.

The main design constraint is that canonical identity must remain separate from volatile listing observations. That keeps the catalog stable while the commercial surface continues to change.
