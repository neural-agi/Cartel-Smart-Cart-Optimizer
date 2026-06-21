from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from app.product_intelligence.matching.interfaces import (
    VariantCandidateEvaluator,
    VariantGovernanceHooks,
)
from app.product_intelligence.matching.types import (
    CandidateEvaluationResult,
    CoverageState,
    CoverageValidationSnapshot,
    CoverageValidationState,
    FreshnessSnapshot,
    FreshnessState,
    MatchOutcome,
    NormalizedPackEvidenceSnapshot,
    VariantGovernanceContext,
    VariantMatchRequest,
)
from app.product_intelligence.matching.variant_candidate_evaluation import (
    DeterministicVariantCandidateEvaluator,
)
from app.product_intelligence.matching.variant_service import DeterministicVariantMatcher
from app.product_intelligence.models import (
    BrandReference,
    CategoryReference,
    IdentityStatus,
    Measurement,
    PackConfiguration,
    PackKind,
    PlatformListing,
    Product,
    ProductLifecycleStatus,
    ProductVariant,
    QuantityDimension,
    ListingObservation,
)


def _run(coro):
    return asyncio.run(coro)


def _measurement(value: str, unit: str, dimension: QuantityDimension) -> Measurement:
    return Measurement(
        value=Decimal(value),
        unit=unit,
        dimension=dimension,
        content_basis="net_content",
        assertion_status="asserted",
    )


def _product(product_id: str = "product-1") -> Product:
    return Product(
        canonical_product_id=product_id,
        product_identity_status=IdentityStatus.established,
        brand_reference=BrandReference(
            canonical_brand_name="Amul",
            display_label="Amul",
            is_unknown=False,
        ),
        product_type="milk",
        canonical_display_name="Amul Taaza Milk",
        canonical_category_reference=CategoryReference(
            category_id="dairy-milk",
            category_path="dairy/milk",
            taxonomy_version="v1",
        ),
        lifecycle_status=ProductLifecycleStatus.active,
        catalog_revision="rev-1",
    )


def _variant(
    variant_id: str,
    *,
    product_id: str = "product-1",
    pack_kind: PackKind = PackKind.single_unit,
    consumer_unit_count: int | None = 1,
    content_per_consumer_unit: Measurement | None = None,
    total_declared_content: Measurement | None = None,
    packaging_form: str | None = "bottle",
    component_set: list | None = None,
) -> ProductVariant:
    return ProductVariant(
        canonical_variant_id=variant_id,
        canonical_product_id=product_id,
        variant_identity_status=IdentityStatus.established,
        pack_configuration=PackConfiguration(
            pack_kind=pack_kind,
            consumer_unit_count=consumer_unit_count,
            content_per_consumer_unit=content_per_consumer_unit,
            total_declared_content=total_declared_content,
            packaging_form=packaging_form,
            component_set=component_set or [],
            pack_configuration_status="complete",
        ),
        lifecycle_status=ProductLifecycleStatus.active,
        catalog_revision="rev-1",
    )


def _listing(quantity_text: str | None = "500 ml") -> PlatformListing:
    return PlatformListing(
        platform="blinkit",
        platform_listing_id="listing-1",
        raw_title="Amul Taaza Milk",
        raw_quantity_text=quantity_text,
        raw_category_text="milk",
        listing_url="https://example.invalid/listing-1",
    )


def _observation() -> ListingObservation:
    return ListingObservation(
        platform_listing_id="listing-1",
        displayed_price="31",
        reference_price="35",
        offer_text=None,
        availability_signal="available",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        parser_version="parser-v1",
        source_artifact_reference="artifact-1",
        capture_context_reference="context-1",
    )


def _governance(
    *,
    coverage_state: CoverageState = CoverageState.representative,
    coverage_validation_state: CoverageValidationState = CoverageValidationState.valid,
    freshness_state: FreshnessState = FreshnessState.fresh,
    normalized_pack_evidence: NormalizedPackEvidenceSnapshot | None = None,
) -> VariantGovernanceContext:
    return VariantGovernanceContext(
        coverage_validation=CoverageValidationSnapshot(
            declaration_id="coverage-1",
            coverage_scope_id="scope-1",
            declared_state=coverage_state,
            validation_state=coverage_validation_state,
            rationale=["coverage=governed"],
        ),
        freshness=FreshnessSnapshot(
            freshness_state=freshness_state,
            lineage_root_id="lineage-root-1",
            revision_ids=["revision-1"],
            supersession_ids=[],
            rationale=["freshness=governed"],
        ),
        normalized_pack_evidence=normalized_pack_evidence,
    )


def _normalized_pack(
    *,
    raw_quantity_text: str = "500 ml",
    pack_kind: PackKind = PackKind.single_unit,
    consumer_unit_count: int | None = 1,
    content_value: str = "500",
    unit: str = "ml",
    dimension: QuantityDimension = QuantityDimension.volume,
    packaging_form: str | None = "bottle",
) -> NormalizedPackEvidenceSnapshot:
    measurement = _measurement(content_value, unit, dimension)
    return NormalizedPackEvidenceSnapshot(
        raw_quantity_text=raw_quantity_text,
        pack_kind=pack_kind,
        consumer_unit_count=consumer_unit_count,
        content_per_consumer_unit=measurement,
        total_declared_content=measurement,
        packaging_form=packaging_form,
        component_set=[],
        pack_configuration_status="complete",
        source_artifact_reference="artifact-1",
        parser_version="parser-v1",
        capture_context_reference="context-1",
    )


class _StaticGovernanceHooks(VariantGovernanceHooks):
    def __init__(self, governance: VariantGovernanceContext) -> None:
        self._governance = governance

    async def collect(self, request: VariantMatchRequest) -> VariantGovernanceContext:
        return self._governance


class _StaticCandidateEvaluator(VariantCandidateEvaluator):
    def __init__(self, result: CandidateEvaluationResult) -> None:
        self._result = result

    async def evaluate(
        self,
        request: VariantMatchRequest,
        governance: VariantGovernanceContext,
    ) -> CandidateEvaluationResult:
        return self._result


def _request(
    *,
    product: Product | None,
    variants: list[ProductVariant],
    quantity_text: str | None = "500 ml",
) -> VariantMatchRequest:
    return VariantMatchRequest(
        platform_listing=_listing(quantity_text),
        listing_observation=_observation(),
        evidence_references=[],
        product=product,
        variant_candidates=variants,
    )


def test_unique_exact_support_survivor_is_selected() -> None:
    evaluator = DeterministicVariantCandidateEvaluator()
    product = _product()
    exact_variant = _variant(
        "variant-exact",
        content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
        total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
    )
    partial_variant = _variant(
        "variant-partial",
        consumer_unit_count=1,
        content_per_consumer_unit=None,
        total_declared_content=None,
    )
    request = _request(product=product, variants=[exact_variant, partial_variant])
    governance = _governance(normalized_pack_evidence=_normalized_pack())

    result = _run(evaluator.evaluate(request=request, governance=governance))

    assert result.candidate_ids_considered == ["variant-exact", "variant-partial"]
    assert result.selected_variant_id == "variant-exact"
    assert result.viable_candidate_ids == ["variant-exact", "variant-partial"]
    assert result.ambiguous_candidate_ids == []
    assert result.eliminated_candidate_ids == []
    assert result.all_candidates_disproved is False
    assert "exact_support_candidate_ids=variant-exact" in result.rationale


def test_multiple_exact_support_survivors_become_ambiguous() -> None:
    evaluator = DeterministicVariantCandidateEvaluator()
    product = _product()
    variant_a = _variant(
        "variant-a",
        content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
        total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
    )
    variant_b = _variant(
        "variant-b",
        content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
        total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
    )
    request = _request(product=product, variants=[variant_a, variant_b])
    governance = _governance(normalized_pack_evidence=_normalized_pack())

    result = _run(evaluator.evaluate(request=request, governance=governance))

    assert result.selected_variant_id is None
    assert result.viable_candidate_ids == ["variant-a", "variant-b"]
    assert result.ambiguous_candidate_ids == ["variant-a", "variant-b"]
    assert "exact_support_candidate_ids=variant-a,variant-b" in result.rationale


def test_partial_support_single_survivor_remains_unresolved_candidate_result() -> None:
    evaluator = DeterministicVariantCandidateEvaluator()
    product = _product()
    partial_variant = _variant(
        "variant-partial",
        pack_kind=PackKind.unknown,
        consumer_unit_count=None,
        content_per_consumer_unit=None,
        total_declared_content=None,
        packaging_form=None,
    )
    request = _request(product=product, variants=[partial_variant])
    governance = _governance(normalized_pack_evidence=None)

    result = _run(evaluator.evaluate(request=request, governance=governance))

    assert result.selected_variant_id is None
    assert result.viable_candidate_ids == ["variant-partial"]
    assert result.ambiguous_candidate_ids == []
    assert result.eliminated_candidate_ids == []
    assert "partial_support_candidate_ids=variant-partial" in result.rationale


def test_partial_support_multiple_survivors_form_ambiguity() -> None:
    evaluator = DeterministicVariantCandidateEvaluator()
    product = _product()
    variant_a = _variant(
        "variant-a",
        pack_kind=PackKind.unknown,
        consumer_unit_count=None,
        content_per_consumer_unit=None,
        total_declared_content=None,
        packaging_form=None,
    )
    variant_b = _variant(
        "variant-b",
        pack_kind=PackKind.unknown,
        consumer_unit_count=None,
        content_per_consumer_unit=None,
        total_declared_content=None,
        packaging_form=None,
    )
    request = _request(product=product, variants=[variant_a, variant_b])
    governance = _governance(normalized_pack_evidence=None)

    result = _run(evaluator.evaluate(request=request, governance=governance))

    assert result.selected_variant_id is None
    assert result.viable_candidate_ids == ["variant-a", "variant-b"]
    assert result.ambiguous_candidate_ids == ["variant-a", "variant-b"]


def test_direct_contradiction_eliminates_candidate() -> None:
    evaluator = DeterministicVariantCandidateEvaluator()
    product = _product("product-1")
    good_variant = _variant("variant-good", product_id="product-1")
    bad_variant = _variant("variant-bad", product_id="product-2")
    request = _request(product=product, variants=[good_variant, bad_variant])
    governance = _governance(normalized_pack_evidence=None)

    result = _run(evaluator.evaluate(request=request, governance=governance))

    assert result.viable_candidate_ids == ["variant-good"]
    assert result.eliminated_candidate_ids == ["variant-bad"]
    assert result.all_candidates_disproved is False
    assert any(
        line.startswith("elimination_record|candidate_id=variant-bad")
        for line in result.rationale
    )


def test_duplicate_candidate_removal_preserves_first_occurrence() -> None:
    evaluator = DeterministicVariantCandidateEvaluator()
    product = _product()
    variant_a = _variant("variant-a")
    variant_b = _variant("variant-b")
    request = _request(product=product, variants=[variant_a, variant_b, variant_a])
    governance = _governance(normalized_pack_evidence=_normalized_pack())

    result = _run(evaluator.evaluate(request=request, governance=governance))

    assert result.candidate_ids_considered == ["variant-a", "variant-b"]


def test_all_candidates_eliminated_sets_disproved_flag() -> None:
    evaluator = DeterministicVariantCandidateEvaluator()
    product = _product("product-1")
    bad_a = _variant("variant-a", product_id="product-2")
    bad_b = _variant("variant-b", product_id="product-3")
    request = _request(product=product, variants=[bad_a, bad_b])
    governance = _governance(normalized_pack_evidence=None)

    result = _run(evaluator.evaluate(request=request, governance=governance))

    assert result.viable_candidate_ids == []
    assert result.eliminated_candidate_ids == ["variant-a", "variant-b"]
    assert result.all_candidates_disproved is True


def test_variant_matcher_rejects_all_disproved_with_representative_coverage() -> None:
    product = _product("product-1")
    bad_a = _variant("variant-a", product_id="product-2")
    bad_b = _variant("variant-b", product_id="product-3")
    request = _request(product=product, variants=[bad_a, bad_b])
    governance = _governance(
        coverage_state=CoverageState.representative,
        coverage_validation_state=CoverageValidationState.valid,
        freshness_state=FreshnessState.fresh,
        normalized_pack_evidence=None,
    )
    matcher = DeterministicVariantMatcher(
        governance_hooks=_StaticGovernanceHooks(governance)
    )

    response = _run(matcher.match(request))

    assert response.outcome == MatchOutcome.rejected
    assert response.selected_variant is None


def test_variant_matcher_keeps_all_disproved_non_representative_as_unresolved() -> None:
    product = _product("product-1")
    bad_a = _variant("variant-a", product_id="product-2")
    bad_b = _variant("variant-b", product_id="product-3")
    request = _request(product=product, variants=[bad_a, bad_b])
    governance = _governance(
        coverage_state=CoverageState.partial,
        coverage_validation_state=CoverageValidationState.valid,
        freshness_state=FreshnessState.fresh,
        normalized_pack_evidence=None,
    )
    matcher = DeterministicVariantMatcher(
        governance_hooks=_StaticGovernanceHooks(governance)
    )

    response = _run(matcher.match(request))

    assert response.outcome == MatchOutcome.unresolved
    assert response.selected_variant is None


def test_variant_matcher_maps_unique_exact_survivor_with_partial_support_candidates() -> None:
    product = _product()
    exact_variant = _variant(
        "variant-exact",
        content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
        total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
    )
    partial_variant = _variant(
        "variant-partial",
        pack_kind=PackKind.unknown,
        consumer_unit_count=None,
        content_per_consumer_unit=None,
        total_declared_content=None,
        packaging_form=None,
    )
    request = _request(product=product, variants=[exact_variant, partial_variant])
    governance = _governance(normalized_pack_evidence=_normalized_pack())
    matcher = DeterministicVariantMatcher(
        governance_hooks=_StaticGovernanceHooks(governance)
    )

    response = _run(matcher.match(request))

    assert response.outcome == MatchOutcome.mapped
    assert response.selected_variant is not None
    assert response.selected_variant.canonical_variant_id == "variant-exact"


def test_variant_matcher_marks_multiple_exact_survivors_ambiguous() -> None:
    product = _product()
    variant_a = _variant(
        "variant-a",
        content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
        total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
    )
    variant_b = _variant(
        "variant-b",
        content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
        total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
    )
    request = _request(product=product, variants=[variant_a, variant_b])
    governance = _governance(normalized_pack_evidence=_normalized_pack())
    matcher = DeterministicVariantMatcher(
        governance_hooks=_StaticGovernanceHooks(governance)
    )

    response = _run(matcher.match(request))

    assert response.outcome == MatchOutcome.ambiguous
    assert response.selected_variant is None


def test_variant_matcher_ignores_rationale_formatting_when_classifying() -> None:
    product = _product()
    variant_a = _variant(
        "variant-a",
        content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
        total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
    )
    request = _request(product=product, variants=[variant_a])
    governance = _governance(normalized_pack_evidence=_normalized_pack())
    candidate_result = CandidateEvaluationResult(
        candidate_ids_considered=["variant-a"],
        viable_candidate_ids=["variant-a"],
        eliminated_candidate_ids=[],
        ambiguous_candidate_ids=[],
        selected_variant_id="variant-a",
        all_candidates_disproved=False,
        rejection_rationale=[],
        rationale=[
            "garbled-rationale",
            "exact_support_candidate_ids:variant-a",
            "ambiguous_candidate_ids variant-a",
            "selected_variant_id=not-for-classification",
        ],
    )
    matcher = DeterministicVariantMatcher(
        governance_hooks=_StaticGovernanceHooks(governance),
        candidate_evaluator=_StaticCandidateEvaluator(candidate_result),
    )

    response = _run(matcher.match(request))

    assert response.outcome == MatchOutcome.mapped
    assert response.selected_variant is not None
    assert response.selected_variant.canonical_variant_id == "variant-a"
