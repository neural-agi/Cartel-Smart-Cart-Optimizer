from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.data_ingestion import (
    CaptureType,
    CompletenessState,
    NormalizedObservation,
    ObservationCompleteness,
    ObservationFieldReference,
    Platform,
    RawArtifactReference,
)
from app.product_intelligence.catalog.identity_contract import (
    CanonicalIdentityResolution,
    IdentityFact,
    IdentityResolutionState,
    PackIdentityEvidence,
    ProductIdentityProfile,
    RetailerProductIdentityEvidence,
)
from app.product_intelligence.catalog.resolution import DeterministicCanonicalListingResolver
from app.product_intelligence.catalog.retailer_identity import BlinkitIdentityAdapter
from app.product_intelligence.catalog.types import CatalogState
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
    EvidenceReference,
    IdentityStatus,
    Measurement,
    PackConfiguration,
    PackKind,
    Product,
    ProductLifecycleStatus,
    ProductVariant,
    QuantityDimension,
    VariantLifecycleStatus,
)


def _ref(name: str) -> EvidenceReference:
    return EvidenceReference(source_type="catalog-review", source_id=name)


def _fact(name: str, value: str) -> IdentityFact:
    return IdentityFact(
        name=name,
        value=value,
        assertion_status="asserted",
        evidence_references=(("retailer-capture", "capture-1"),),
    )


def _pack(*, amount="500", unit="ml", kind=PackKind.single_unit, count=1):
    measurement = Measurement(
        value=Decimal(amount),
        unit=unit,
        dimension=QuantityDimension.volume if unit.casefold() in {"ml", "l"} else QuantityDimension.mass,
        content_basis="net_content",
        assertion_status="asserted",
    )
    config = PackConfiguration(
        pack_kind=kind,
        consumer_unit_count=count,
        content_per_consumer_unit=measurement,
        total_declared_content=measurement,
        pack_configuration_status="complete",
    )
    return PackIdentityEvidence(
        configuration=config,
        assertion_status="asserted",
        evidence_references=(("retailer-capture", "capture-1"),),
    )


def _canonical(*, product_id="canonical-product", variant_id="canonical-variant", flavor="plain", amount="500", unit="ml"):
    product = Product(
        canonical_product_id=product_id,
        product_identity_status=IdentityStatus.established,
        brand_reference=BrandReference(
            canonical_brand_name="Acme",
            display_label="Acme",
            evidence_references=[_ref("brand-proof")],
        ),
        product_type="milk",
        canonical_display_name="Acme Dairy Milk",
        identity_attributes=[
            AttributeAssertion(
                name="formulation",
                value="toned",
                role="identity_critical",
                assertion_status="asserted",
                evidence_references=[_ref("formulation-proof")],
            )
        ],
        canonical_category_reference=CategoryReference(
            category_id="dairy",
            review_state="approved",
        ),
        lifecycle_status=ProductLifecycleStatus.active,
        catalog_revision="catalog-r1",
        evidence_references=[_ref("product-proof")],
    )
    variant = ProductVariant(
        canonical_variant_id=variant_id,
        canonical_product_id=product_id,
        variant_identity_status=IdentityStatus.established,
        variant_identity_attributes=[
            AttributeAssertion(
                name="flavor",
                value=flavor,
                role="identity_critical",
                assertion_status="asserted",
                evidence_references=[_ref("flavor-proof")],
            )
        ],
        pack_configuration=_pack(amount=amount, unit=unit).configuration,
        lifecycle_status=VariantLifecycleStatus.active,
        catalog_revision="catalog-r1",
        evidence_references=[_ref("variant-proof")],
    )
    return product, variant


def _observation(*, platform=Platform.BLINKIT, listing_id="cartel-listing-1", retailer_id="retailer-101", title="Acme Dairy Milk Toned Plain 500 ml", captured_at=None):
    timestamp = captured_at or datetime(2026, 1, 1, tzinfo=timezone.utc)
    artifact = RawArtifactReference(
        artifact_id="artifact-1",
        job_id="job-1",
        attempt_id="job-1:1",
        platform=platform,
        capture_type=CaptureType.SEARCH_RESULTS,
        content_digest="a" * 64,
        storage_reference="artifact-store-ref",
        content_type="text/html",
        capture_timestamp=timestamp,
        source_reference=f"https://{platform.value.casefold()}.example/s/?q=milk",
    )
    evidence = EvidenceReference(source_type="retailer-capture", source_id="capture-1")
    return NormalizedObservation(
        platform=platform,
        source_record_id=listing_id,
        raw_artifact_reference=artifact,
        normalized_name=title,
        normalized_quantity="500 ml",
        normalized_category="milk",
        platform_identifiers=(("retailer_product_id", retailer_id),),
        observed_price_text="Rs. 40",
        availability_signal="in_stock",
        evidence_references=(evidence,),
        field_references=(ObservationFieldReference(evidence_reference=evidence, locator="product.raw_title"),),
        completeness=ObservationCompleteness(
            state=CompletenessState.COMPLETE,
            scope_reference="scope-1",
            basis="complete capture",
        ),
        parser_version="retailer-parser-v1",
        normalization_version="normalizer-v1",
    )


def _retailer_evidence(*, platform=Platform.BLINKIT, listing_id="cartel-listing-1", retailer_id="retailer-101", identity=None, **observation_kwargs):
    observation = _observation(
        platform=platform,
        listing_id=listing_id,
        retailer_id=retailer_id,
        **observation_kwargs,
    )
    identity = identity or ProductIdentityProfile(
        brand=_fact("brand", "Acme"),
        product_type=_fact("product_type", "milk"),
        product_attributes=(_fact("formulation", "toned"),),
        variant_attributes=(_fact("flavor", "plain"),),
        pack=_pack(),
    )
    return RetailerProductIdentityEvidence(
        observation=observation,
        identity=identity,
        descriptive_title=observation.normalized_name,
    )


def _resolver():
    return DeterministicCanonicalListingResolver(
        product_observation_key=lambda _: None,
        product_catalog_key=lambda _: None,
        variant_observation_key=lambda *_: None,
        variant_catalog_key=lambda _: None,
    )


def test_exact_identity_requires_brand_product_attributes_variant_and_full_pack():
    product, variant = _canonical()
    result = _resolver().compare_identity(_retailer_evidence(), product, variant)
    assert result.state == IdentityResolutionState.EXACT_MATCH


@pytest.mark.parametrize(
    "identity",
    [
        ProductIdentityProfile(
            brand=_fact("brand", "Other"), product_type=_fact("product_type", "milk"),
            product_attributes=(_fact("formulation", "toned"),),
            variant_attributes=(_fact("flavor", "plain"),), pack=_pack(),
        ),
        ProductIdentityProfile(
            brand=_fact("brand", "Acme"), product_type=_fact("product_type", "yogurt"),
            product_attributes=(_fact("formulation", "toned"),),
            variant_attributes=(_fact("flavor", "plain"),), pack=_pack(),
        ),
        ProductIdentityProfile(
            brand=_fact("brand", "Acme"), product_type=_fact("product_type", "milk"),
            product_attributes=(_fact("formulation", "skimmed"),),
            variant_attributes=(_fact("flavor", "plain"),), pack=_pack(),
        ),
        ProductIdentityProfile(
            brand=_fact("brand", "Acme"), product_type=_fact("product_type", "milk"),
            product_attributes=(_fact("formulation", "toned"),),
            variant_attributes=(_fact("flavor", "chocolate"),), pack=_pack(),
        ),
        ProductIdentityProfile(
            brand=_fact("brand", "Acme"), product_type=_fact("product_type", "milk"),
            product_attributes=(_fact("formulation", "toned"),),
            variant_attributes=(_fact("flavor", "plain"),), pack=_pack(amount="1000"),
        ),
        ProductIdentityProfile(
            brand=_fact("brand", "Acme"), product_type=_fact("product_type", "milk"),
            product_attributes=(_fact("formulation", "toned"),),
            variant_attributes=(_fact("flavor", "plain"),), pack=_pack(amount="0.5", unit="l"),
        ),
    ],
)
def test_authoritative_brand_product_variant_pack_contradictions_are_mismatches(identity):
    product, variant = _canonical()
    result = _resolver().compare_identity(_retailer_evidence(identity=identity), product, variant)
    assert result.state == IdentityResolutionState.MISMATCH


def test_missing_pack_and_conflicting_identity_facts_remain_unresolved():
    product, variant = _canonical()
    missing_pack = ProductIdentityProfile(
        brand=_fact("brand", "Acme"),
        product_type=_fact("product_type", "milk"),
        product_attributes=(_fact("formulation", "toned"),),
        variant_attributes=(_fact("flavor", "plain"),),
    )
    assert _resolver().compare_identity(_retailer_evidence(identity=missing_pack), product, variant).state == IdentityResolutionState.UNRESOLVED

    conflicting = ProductIdentityProfile(
        brand=_fact("brand", "Acme"),
        product_type=_fact("product_type", "milk"),
        product_attributes=(_fact("formulation", "toned"), _fact("formulation", "skimmed")),
        variant_attributes=(_fact("flavor", "plain"),),
        pack=_pack(),
    )
    assert _resolver().compare_identity(_retailer_evidence(identity=conflicting), product, variant).state == IdentityResolutionState.UNRESOLVED


def test_title_price_availability_and_old_capture_cannot_supply_missing_identity():
    product, variant = _canonical()
    observation = _observation(captured_at=datetime(2018, 1, 1, tzinfo=timezone.utc))
    title_only = RetailerProductIdentityEvidence(
        observation=observation,
        identity=ProductIdentityProfile(),
        descriptive_title="Acme Dairy Milk Toned Plain 500 ml",
    )
    result = _resolver().compare_identity(title_only, product, variant)
    assert result.state == IdentityResolutionState.UNRESOLVED
    assert "brand" in result.reason


def test_price_and_availability_changes_do_not_change_an_exact_identity_result():
    product, variant = _canonical()
    evidence = _retailer_evidence()
    updated_observation = evidence.observation.model_copy(
        update={"observed_price_text": "Rs. 999", "availability_signal": "out_of_stock"}
    )
    changed_offer = evidence.model_copy(update={"observation": updated_observation})
    assert _resolver().compare_identity(changed_offer, product, variant).state == IdentityResolutionState.EXACT_MATCH


def test_cross_retailer_listings_resolve_to_same_canonical_ids_without_merging_listing_ids():
    product, variant = _canonical()
    resolver = _resolver()
    state = CatalogState(products=(product,), variants=(variant,))
    blinkit = _retailer_evidence(listing_id="blinkit-listing-key", retailer_id="blinkit-1")
    zepto = _retailer_evidence(
        platform=Platform.ZEPTO,
        listing_id="zepto-listing-key",
        retailer_id="zepto-9",
    )

    left = resolver.resolve_identity(blinkit, state)
    right = resolver.resolve_identity(zepto, state)
    assert left.state == right.state == IdentityResolutionState.EXACT_MATCH
    assert (left.canonical_product_id, left.canonical_variant_id) == (
        right.canonical_product_id,
        right.canonical_variant_id,
    )
    assert blinkit.observation.source_record_id != zepto.observation.source_record_id
    assert blinkit.retailer_product_id != zepto.retailer_product_id


def test_multiple_exact_canonical_pairs_are_unresolved_as_ambiguous():
    product, variant = _canonical()
    duplicate_product, duplicate_variant = _canonical(product_id="other-product", variant_id="other-variant")
    result = _resolver().resolve_identity(
        _retailer_evidence(),
        CatalogState(products=(product, duplicate_product), variants=(variant, duplicate_variant)),
    )
    assert result.state == IdentityResolutionState.UNRESOLVED
    assert result.canonical_product_id is None


def test_exact_candidate_is_unresolved_when_another_eligible_candidate_is_ambiguous():
    product, variant = _canonical()
    incomplete_product, incomplete_variant = _canonical(
        product_id="incomplete-product",
        variant_id="incomplete-variant",
    )
    incomplete_product = incomplete_product.model_copy(update={"identity_attributes": []})
    result = _resolver().resolve_identity(
        _retailer_evidence(),
        CatalogState(
            products=(product, incomplete_product),
            variants=(variant, incomplete_variant),
        ),
    )
    assert result.state == IdentityResolutionState.UNRESOLVED
    assert result.canonical_product_id is None
    assert "insufficient identity evidence" in result.reason


def test_blinkit_adapter_does_not_infer_brand_or_pack_from_title_or_quantity():
    evidence = BlinkitIdentityAdapter().adapt(_observation())
    product, variant = _canonical()
    result = _resolver().compare_identity(evidence, product, variant)
    assert evidence.identity.brand is None
    assert evidence.identity.pack is None
    assert evidence.descriptive_title
    assert result.state == IdentityResolutionState.UNRESOLVED


def test_existing_resolver_routes_blinkit_through_strict_adapter_when_configured():
    product, variant = _canonical()
    observation = _observation(title="Acme Dairy Milk Toned Plain 500 ml")
    resolver = DeterministicCanonicalListingResolver(
        product_observation_key=lambda _: ("acme dairy milk toned plain 500 ml", "dairy"),
        product_catalog_key=lambda _: ("acme dairy milk toned plain 500 ml", "dairy"),
        variant_observation_key=lambda *_: ("canonical-product", ("500", "ml")),
        variant_catalog_key=lambda _: ("canonical-product", ("500", "ml")),
        retailer_identity_adapters={"BLINKIT": BlinkitIdentityAdapter()},
    )
    result = resolver.resolve(observation, CatalogState(products=(product,), variants=(variant,)))
    assert result.status.value == "unresolved"
    assert result.association is None


def test_identity_resolution_has_only_three_states_and_exact_only_carries_ids():
    assert {state.value for state in IdentityResolutionState} == {"EXACT_MATCH", "MISMATCH", "UNRESOLVED"}
    with pytest.raises(ValueError):
        CanonicalIdentityResolution(state="EXACT_MATCH", reason="missing ids")
