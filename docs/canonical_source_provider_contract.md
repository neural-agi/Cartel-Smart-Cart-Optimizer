# Canonical Source Provider Contract

This boundary describes future independent sources of canonical Product and
ProductVariant evidence. It does not authorize retailer observations to become
canonical evidence and it does not imply that GS1 DataKart or any other source
is configured today.

## Provider result

A configured provider may return an immutable, content-addressed evidence
record containing:

- `provider_id` and source name;
- source record identifier and source revision;
- capture timestamp and effective timestamp, when supplied;
- canonical brand/manufacturer;
- canonical product name and product type;
- approved taxonomy/category reference;
- identity-critical product and variant attributes;
- GTIN/EAN when explicitly supplied by the source;
- structured packaging: pack kind, consumer-unit count, content per unit,
  total declared content, unit, dimension, content basis, and packaging form;
- source URL or durable artifact reference;
- field-level provenance and evidence quality.

Missing or conflicting fields remain unresolved. A provider result must never
be converted directly into a catalog row.

## Governance boundary

The result enters the existing operator manifest workflow. The workflow must
validate complete established Product/Variant records, evidence references,
approved category, active lifecycle, catalog revision, and complete structured
pack identity before persistence. A retailer observation is only compared by
the existing exact resolver after the canonical records exist.

GTIN is corroborating identity evidence, not a universal requirement and not a
substitute for product, variant, or pack identity. One GTIN cannot be reused
for incompatible variants; missing GTIN remains valid when the other governed
identity evidence is complete.

## Current status

No canonical-source provider is configured in this repository. The real
QuickCommerce/Blinkit observation for retailer product `19512` remains
retailer evidence and is not sufficient by itself to establish the canonical
Amul Taaza 500 ml Product/Variant.
