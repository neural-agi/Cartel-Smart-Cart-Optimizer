from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class IdentityStatus(StrEnum):
    """Lifecycle of a canonical identity assertion."""

    established = "established"
    provisional = "provisional"
    ambiguous = "ambiguous"
    deprecated = "deprecated"
    merged = "merged"


class ProductLifecycleStatus(StrEnum):
    """Lifecycle state for a canonical product."""

    active = "active"
    discontinued = "discontinued"
    superseded = "superseded"
    unknown = "unknown"


class VariantLifecycleStatus(StrEnum):
    """Lifecycle state for a canonical product variant."""

    active = "active"
    discontinued = "discontinued"
    superseded = "superseded"
    unknown = "unknown"


class MappingStatus(StrEnum):
    """State of a platform listing's canonical mapping."""

    unresolved = "unresolved"
    ambiguous = "ambiguous"
    mapped = "mapped"
    rejected = "rejected"


class PackKind(StrEnum):
    """High-level commercial pack structure."""

    single_unit = "single_unit"
    multipack = "multipack"
    combo = "combo"
    assortment = "assortment"
    unknown = "unknown"


class QuantityDimension(StrEnum):
    """Measurement dimension for a declared quantity."""

    mass = "mass"
    volume = "volume"
    count = "count"
    unknown = "unknown"


class QuantityValue(BaseModel):
    """Structured quantity value used in measurements and pack configurations."""

    amount: Decimal
    unit: str
    dimension: QuantityDimension
    content_basis: Literal["net_content", "count_only", "unknown"] = "unknown"


class EvidenceReference(BaseModel):
    """Pointer to a durable evidence source or decision record."""

    source_type: str
    source_id: str
    capture_timestamp: datetime | None = None
    note: str | None = None


class BrandReference(BaseModel):
    """Canonical brand reference with an explicit unresolved state."""

    canonical_brand_name: str | None = None
    display_label: str
    is_unknown: bool = False
    evidence_references: list[EvidenceReference] = Field(default_factory=list)


class CategoryReference(BaseModel):
    """Versioned category reference used by canonical product records."""

    category_id: str
    category_path: str | None = None
    taxonomy_version: str | None = None
    review_state: Literal["unreviewed", "reviewed", "approved", "deprecated"] = "unreviewed"


class AttributeAssertion(BaseModel):
    """Structured attribute claim with an explicit role and evidence trail."""

    name: str
    value: str
    role: Literal["identity_critical", "descriptive"]
    assertion_status: Literal["asserted", "inferred", "unknown"] = "asserted"
    qualifier: str | None = None
    evidence_references: list[EvidenceReference] = Field(default_factory=list)


class Measurement(BaseModel):
    """Normalized quantity representation without conversion logic."""

    value: Decimal
    unit: str
    dimension: QuantityDimension
    content_basis: Literal["net_content", "count_only", "unknown"] = "unknown"
    assertion_status: Literal["asserted", "inferred", "unknown"] = "asserted"


class PackComponent(BaseModel):
    """One component in a combo or assortment pack."""

    label: str
    quantity_text: str | None = None
    quantity: Measurement | None = None


class PackConfiguration(BaseModel):
    """Structured pack description for a product variant."""

    pack_kind: PackKind = PackKind.unknown
    consumer_unit_count: int | None = None
    content_per_consumer_unit: Measurement | None = None
    total_declared_content: Measurement | None = None
    packaging_form: str | None = None
    component_set: list[PackComponent] = Field(default_factory=list)
    pack_configuration_status: Literal[
        "complete",
        "partial",
        "unknown",
        "requires_review",
    ] = "unknown"


class Product(BaseModel):
    """Canonical platform-independent grocery product family."""

    canonical_product_id: str
    product_identity_status: IdentityStatus = IdentityStatus.provisional
    brand_reference: BrandReference
    product_type: str
    canonical_display_name: str
    identity_attributes: list[AttributeAssertion] = Field(default_factory=list)
    descriptive_attributes: list[AttributeAssertion] = Field(default_factory=list)
    canonical_category_reference: CategoryReference
    lifecycle_status: ProductLifecycleStatus = ProductLifecycleStatus.unknown
    catalog_revision: str
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    effective_period_start: datetime | None = None
    effective_period_end: datetime | None = None


class ProductVariant(BaseModel):
    """Canonical consumer-distinct purchasable configuration."""

    canonical_variant_id: str
    canonical_product_id: str
    variant_identity_status: IdentityStatus = IdentityStatus.provisional
    variant_identity_attributes: list[AttributeAssertion] = Field(default_factory=list)
    pack_configuration: PackConfiguration
    lifecycle_status: VariantLifecycleStatus = VariantLifecycleStatus.unknown
    catalog_revision: str
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    effective_period_start: datetime | None = None
    effective_period_end: datetime | None = None


class PlatformListing(BaseModel):
    """Platform-native catalog listing for a purchasable item."""

    platform: str
    platform_listing_id: str
    raw_title: str
    raw_quantity_text: str | None = None
    raw_category_text: str | None = None
    listing_url: str | None = None
    mapping_status: MappingStatus = MappingStatus.unresolved


class ListingObservation(BaseModel):
    """Append-only observation of a platform listing at a point in time."""

    platform_listing_id: str
    displayed_price: str | None = None
    reference_price: str | None = None
    offer_text: str | None = None
    availability_signal: str | None = None
    capture_timestamp: datetime
    parser_version: str
    source_artifact_reference: str
    capture_context_reference: str | None = None
