"""Shared, evidence-backed identity facts for canonical and retailer products."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.models import PackConfiguration, Product, ProductVariant


class IdentityResolutionState(StrEnum):
    EXACT_MATCH = "EXACT_MATCH"
    MISMATCH = "MISMATCH"
    UNRESOLVED = "UNRESOLVED"


class IdentityFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: str
    assertion_status: Literal["asserted", "inferred", "unknown"]
    evidence_references: tuple[tuple[str, str], ...]

    @field_validator("name", "value")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("identity fact values must not be blank")
        return value


class PackIdentityEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    configuration: PackConfiguration
    assertion_status: Literal["asserted", "inferred", "unknown"]
    evidence_references: tuple[tuple[str, str], ...]


class ProductIdentityProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    brand: IdentityFact | None = None
    product_type: IdentityFact | None = None
    product_attributes: tuple[IdentityFact, ...] = ()
    variant_attributes: tuple[IdentityFact, ...] = ()
    pack: PackIdentityEvidence | None = None


class RetailerProductIdentityEvidence(BaseModel):
    """Retailer identity facts bound to one immutable normalized observation."""

    model_config = ConfigDict(frozen=True)

    observation: NormalizedObservation
    identity: ProductIdentityProfile
    descriptive_title: str | None = None
    evidence_issues: tuple[str, ...] = ()

    @field_validator("descriptive_title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        return None if value is None else " ".join(value.split()) or None

    @field_validator("evidence_issues")
    @classmethod
    def clean_issues(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(" ".join(item.split()) for item in values if item.strip())

    @field_validator("identity")
    @classmethod
    def identity_facts_retain_observation_evidence(cls, value, info):
        observation = info.data.get("observation")
        if observation is None:
            return value
        available = {(item.source_type, item.source_id) for item in observation.evidence_references}
        facts = [value.brand, value.product_type, *value.product_attributes, *value.variant_attributes]
        fact_refs = [reference for fact in facts if fact is not None for reference in fact.evidence_references]
        if value.pack is not None:
            fact_refs.extend(value.pack.evidence_references)
        if any(reference not in available for reference in fact_refs):
            raise ValueError("identity facts must cite evidence registered on the source observation")
        return value

    @property
    def platform(self) -> str:
        return self.observation.platform.value

    @property
    def platform_listing_id(self) -> str:
        return self.observation.source_record_id

    @property
    def retailer_product_id(self) -> str | None:
        return dict(self.observation.platform_identifiers).get("retailer_product_id")

    @property
    def retailer_product_url(self) -> str | None:
        return dict(self.observation.platform_identifiers).get("retailer_product_url")


class IdentityComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: Literal["EXACT_MATCH", "MISMATCH", "UNRESOLVED"]
    reason: str


class CanonicalIdentityResolution(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: Literal["EXACT_MATCH", "MISMATCH", "UNRESOLVED"]
    reason: str
    canonical_product_id: str | None = None
    canonical_variant_id: str | None = None

    @model_validator(mode="after")
    def identity_matches_resolution_state(self):
        has_identity = bool(self.canonical_product_id and self.canonical_variant_id)
        if self.state == IdentityResolutionState.EXACT_MATCH and not has_identity:
            raise ValueError("exact match requires canonical Product and Variant IDs")
        if self.state != IdentityResolutionState.EXACT_MATCH and has_identity:
            raise ValueError("non-exact resolution must not carry canonical IDs")
        return self


def canonical_identity_profile(product: Product, variant: ProductVariant) -> ProductIdentityProfile:
    """Adapt existing governed Product/Variant assertions into the shared contract."""
    brand_name = product.brand_reference.canonical_brand_name
    brand = None
    if brand_name and not product.brand_reference.is_unknown:
        brand = IdentityFact(
            name="brand",
            value=brand_name,
            assertion_status="asserted" if product.brand_reference.evidence_references else "unknown",
            evidence_references=tuple(
                sorted((item.source_type, item.source_id) for item in product.brand_reference.evidence_references)
            ),
        )
    product_type = IdentityFact(
        name="product_type",
        value=product.product_type,
        assertion_status="asserted" if product.evidence_references else "unknown",
        evidence_references=tuple(sorted((item.source_type, item.source_id) for item in product.evidence_references)),
    )

    def attributes(items) -> tuple[IdentityFact, ...]:
        return tuple(
            IdentityFact(
                name=item.name,
                value=item.value,
                assertion_status=(
                    item.assertion_status
                    if item.role == "identity_critical" and item.evidence_references
                    else "unknown"
                ),
                evidence_references=tuple(
                    sorted((ref.source_type, ref.source_id) for ref in item.evidence_references)
                ),
            )
            for item in items
            if item.role == "identity_critical"
        )

    pack = PackIdentityEvidence(
        configuration=variant.pack_configuration,
        assertion_status=(
            "asserted"
            if variant.evidence_references
            and variant.pack_configuration.pack_configuration_status == "complete"
            else "unknown"
        ),
        evidence_references=tuple(
            sorted((item.source_type, item.source_id) for item in variant.evidence_references)
        ),
    )
    return ProductIdentityProfile(
        brand=brand,
        product_type=product_type,
        product_attributes=attributes(product.identity_attributes),
        variant_attributes=attributes(variant.variant_identity_attributes),
        pack=pack,
    )


def compare_identity_profiles(
    canonical: ProductIdentityProfile,
    retailer: ProductIdentityProfile,
) -> IdentityComparison:
    """Compare only asserted identity facts; descriptive/offer facts are excluded."""
    unresolved: list[str] = []
    mismatch: list[str] = []

    for label, left, right in (
        ("brand", canonical.brand, retailer.brand),
        ("product_type", canonical.product_type, retailer.product_type),
    ):
        state = _compare_fact(left, right)
        if state == IdentityResolutionState.MISMATCH:
            mismatch.append(label)
        elif state == IdentityResolutionState.UNRESOLVED:
            unresolved.append(label)

    for label, left, right in (
        ("product identity attribute", canonical.product_attributes, retailer.product_attributes),
        ("variant identity attribute", canonical.variant_attributes, retailer.variant_attributes),
    ):
        state, reason = _compare_attributes(left, right)
        if state == IdentityResolutionState.MISMATCH:
            mismatch.append(reason or label)
        elif state == IdentityResolutionState.UNRESOLVED:
            unresolved.append(reason or label)

    pack_state, pack_reason = _compare_pack(canonical.pack, retailer.pack)
    if pack_state == IdentityResolutionState.MISMATCH:
        mismatch.append(pack_reason)
    elif pack_state == IdentityResolutionState.UNRESOLVED:
        unresolved.append(pack_reason)

    if mismatch:
        return IdentityComparison(state=IdentityResolutionState.MISMATCH, reason="authoritative contradiction: " + ", ".join(sorted(set(mismatch))))
    if unresolved:
        return IdentityComparison(state=IdentityResolutionState.UNRESOLVED, reason="insufficient or ambiguous identity evidence: " + ", ".join(sorted(set(unresolved))))
    return IdentityComparison(state=IdentityResolutionState.EXACT_MATCH, reason="all required asserted identity constraints match")


def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


def _fact_is_authoritative(fact: IdentityFact | None) -> bool:
    return bool(fact and fact.assertion_status == "asserted" and fact.evidence_references)


def _compare_fact(left: IdentityFact | None, right: IdentityFact | None) -> str:
    if not _fact_is_authoritative(left) or not _fact_is_authoritative(right):
        return IdentityResolutionState.UNRESOLVED
    assert left is not None and right is not None
    if _normalize(left.name) != _normalize(right.name):
        return IdentityResolutionState.UNRESOLVED
    return (
        IdentityResolutionState.EXACT_MATCH
        if _normalize(left.value) == _normalize(right.value)
        else IdentityResolutionState.MISMATCH
    )


def _attribute_map(facts: tuple[IdentityFact, ...]) -> dict[str, IdentityFact] | None:
    result: dict[str, IdentityFact] = {}
    for fact in facts:
        key = _normalize(fact.name)
        existing = result.get(key)
        if existing is not None and _normalize(existing.value) != _normalize(fact.value):
            return None
        result[key] = fact
    return result


def _compare_attributes(left: tuple[IdentityFact, ...], right: tuple[IdentityFact, ...]) -> tuple[str, str | None]:
    canonical = _attribute_map(left)
    retailer = _attribute_map(right)
    if canonical is None or retailer is None:
        return IdentityResolutionState.UNRESOLVED, "conflicting duplicate attribute evidence"
    if not canonical:
        return IdentityResolutionState.UNRESOLVED, "canonical identity attributes are not governed"
    for name, expected in canonical.items():
        observed = retailer.get(name)
        if observed is None or not _fact_is_authoritative(expected) or not _fact_is_authoritative(observed):
            return IdentityResolutionState.UNRESOLVED, f"missing or unasserted identity attribute {name}"
        if _normalize(expected.value) != _normalize(observed.value):
            return IdentityResolutionState.MISMATCH, f"identity attribute {name}"
    if set(retailer) - set(canonical):
        return IdentityResolutionState.UNRESOLVED, "retailer identity attributes exceed canonical assertions"
    return IdentityResolutionState.EXACT_MATCH, None


def _measurement_signature(measurement) -> tuple | None:
    if (
        measurement is None
        or measurement.assertion_status != "asserted"
        or not measurement.value.is_finite()
        or measurement.value <= 0
        or measurement.dimension == "unknown"
        or measurement.content_basis == "unknown"
        or not measurement.unit.strip()
    ):
        return None
    return (
        measurement.value.normalize(),
        _normalize(measurement.unit),
        measurement.dimension.value if hasattr(measurement.dimension, "value") else measurement.dimension,
        measurement.content_basis,
    )


def _pack_signature(pack: PackIdentityEvidence | None) -> tuple | None:
    if (
        pack is None
        or pack.assertion_status != "asserted"
        or not pack.evidence_references
        or pack.configuration.pack_configuration_status != "complete"
    ):
        return None
    config = pack.configuration
    if config.pack_kind.value == "unknown" or config.consumer_unit_count is None or config.consumer_unit_count < 1:
        return None
    total = _measurement_signature(config.total_declared_content)
    if total is None:
        return None
    per_unit = _measurement_signature(config.content_per_consumer_unit)
    if config.content_per_consumer_unit is not None and per_unit is None:
        return None
    if config.pack_kind.value in {"combo", "assortment"} and not config.component_set:
        return None
    components = []
    for component in config.component_set:
        quantity = _measurement_signature(component.quantity)
        if component.quantity is not None and quantity is None:
            return None
        components.append((_normalize(component.label), _normalize(component.quantity_text or ""), quantity))
    return (
        config.pack_kind.value,
        config.consumer_unit_count,
        per_unit,
        total,
        _normalize(config.packaging_form or ""),
        tuple(sorted(components, key=repr)),
    )


def _compare_pack(left: PackIdentityEvidence | None, right: PackIdentityEvidence | None) -> tuple[str, str]:
    if (
        left is None
        or right is None
        or left.assertion_status != "asserted"
        or right.assertion_status != "asserted"
        or not left.evidence_references
        or not right.evidence_references
    ):
        return IdentityResolutionState.UNRESOLVED, "complete asserted pack identity is required"

    left_config = left.configuration
    right_config = right.configuration
    known_contradictions: list[str] = []
    if (
        left_config.pack_kind.value != "unknown"
        and right_config.pack_kind.value != "unknown"
        and left_config.pack_kind != right_config.pack_kind
    ):
        known_contradictions.append("pack kind")
    if (
        left_config.consumer_unit_count is not None
        and right_config.consumer_unit_count is not None
        and left_config.consumer_unit_count != right_config.consumer_unit_count
    ):
        known_contradictions.append("consumer-unit count")
    if (
        left_config.packaging_form
        and right_config.packaging_form
        and _normalize(left_config.packaging_form) != _normalize(right_config.packaging_form)
    ):
        known_contradictions.append("packaging form")

    for label, first, second in (
        ("total declared content", left_config.total_declared_content, right_config.total_declared_content),
        ("content per unit", left_config.content_per_consumer_unit, right_config.content_per_consumer_unit),
    ):
        first_signature = _measurement_signature(first)
        second_signature = _measurement_signature(second)
        if first_signature is not None and second_signature is not None and first_signature != second_signature:
            known_contradictions.append(label)

    if (
        left_config.component_set
        and right_config.component_set
        and _component_signature(left_config) != _component_signature(right_config)
    ):
        known_contradictions.append("pack component set")
    if known_contradictions:
        return IdentityResolutionState.MISMATCH, "pack contradiction: " + ", ".join(known_contradictions)

    left_signature = _pack_signature(left)
    right_signature = _pack_signature(right)
    if left_signature is None or right_signature is None:
        return IdentityResolutionState.UNRESOLVED, "complete asserted pack identity is required"
    if left_signature != right_signature:
        return IdentityResolutionState.MISMATCH, "pack kind/count/content/unit/components"
    return IdentityResolutionState.EXACT_MATCH, "pack identity matches"


def _component_signature(config: PackConfiguration) -> tuple:
    components = []
    for component in config.component_set:
        quantity = _measurement_signature(component.quantity)
        if component.quantity is not None and quantity is None:
            return ()
        components.append((_normalize(component.label), _normalize(component.quantity_text or ""), quantity))
    return tuple(sorted(components, key=repr))
