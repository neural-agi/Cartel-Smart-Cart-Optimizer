from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.product_intelligence.assertions import DeterministicAssertionManager
from app.product_intelligence.candidate_generation import (
    CandidateCatalogSnapshot,
    DeterministicCandidateGenerationService,
)
from app.product_intelligence.evidence import EvidenceFilesystemStore, FilesystemEvidenceRegistry
from app.product_intelligence.evidence.types import EvidenceRegistrationRequest
from app.product_intelligence.matching import (
    DeterministicProductMatcher,
    DeterministicVariantMatcher,
)
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
    EvidenceReference,
    IdentityStatus,
    ListingObservation,
    Measurement,
    PackConfiguration,
    PackKind,
    PlatformListing,
    Product,
    ProductLifecycleStatus,
    ProductVariant,
    QuantityDimension,
    VariantLifecycleStatus,
)
from app.product_intelligence.orchestrator.service import (
    DeterministicProductIntelligenceOrchestrator,
    PipelineOutcome,
    ProductIntelligencePipelineRequest,
)
from app.product_intelligence.review import DeterministicReviewQueueManager
from app.product_intelligence.review.interfaces import ReviewQueueManager
from app.product_intelligence.review.types import ReviewStatus
from app.product_intelligence.assertions.interfaces import AssertionManager
from app.product_intelligence.candidate_generation.interfaces import CandidateGenerator
from app.product_intelligence.evidence.interfaces import EvidenceRegistry
from app.product_intelligence.matching.interfaces import ProductMatcher, VariantMatcher
from app.product_intelligence.matching.types import (
    CoverageState,
    CoverageValidationSnapshot,
    CoverageValidationState,
    FreshnessSnapshot,
    FreshnessState,
    NormalizedPackEvidenceSnapshot,
    VariantGovernanceContext,
)
from app.product_intelligence.matching.interfaces import VariantGovernanceHooks


def _run(coro):
    return asyncio.run(coro)


def _measurement(amount: str, unit: str, dimension: QuantityDimension) -> Measurement:
    return Measurement(
        value=Decimal(amount),
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
        identity_attributes=[
            AttributeAssertion(
                name="milk_type",
                value="toned",
                role="identity_critical",
            )
        ],
        canonical_category_reference=CategoryReference(
            category_id="dairy-milk",
            category_path="dairy/milk",
            taxonomy_version="v1",
            review_state="approved",
        ),
        lifecycle_status=ProductLifecycleStatus.active,
        catalog_revision="rev-1",
        evidence_references=[],
    )


def _variant(
    variant_id: str,
    *,
    product_id: str = "product-1",
    quantity: str = "500",
    unit: str = "ml",
    packaging_form: str = "pouch",
) -> ProductVariant:
    return ProductVariant(
        canonical_variant_id=variant_id,
        canonical_product_id=product_id,
        variant_identity_status=IdentityStatus.established,
        variant_identity_attributes=[],
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.single_unit,
            consumer_unit_count=1,
            content_per_consumer_unit=_measurement(quantity, unit, QuantityDimension.volume),
            total_declared_content=_measurement(quantity, unit, QuantityDimension.volume),
            packaging_form=packaging_form,
            component_set=[],
            pack_configuration_status="complete",
        ),
        lifecycle_status=VariantLifecycleStatus.active,
        catalog_revision="rev-1",
        evidence_references=[],
    )


def _listing(platform_listing_id: str = "listing-1") -> PlatformListing:
    return PlatformListing(
        platform="blinkit",
        platform_listing_id=platform_listing_id,
        raw_title="Amul Taaza Milk",
        raw_quantity_text="500 ml",
        raw_category_text="milk",
        listing_url="https://example.invalid/listing",
    )


def _observation(platform_listing_id: str = "listing-1") -> ListingObservation:
    return ListingObservation(
        platform_listing_id=platform_listing_id,
        displayed_price="31",
        reference_price="35",
        offer_text=None,
        availability_signal="ADD",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="parser-v1",
        source_artifact_reference="artifact-1",
        capture_context_reference="context-1",
    )


def _registration_request(platform_listing_id: str = "listing-1") -> EvidenceRegistrationRequest:
    return EvidenceRegistrationRequest(
        platform="blinkit",
        source_artifact_reference=f"artifact-{platform_listing_id}",
        parser_version="parser-v1",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        capture_context_reference="context-1",
    )


def _pipeline_request(
    bundle,
    *,
    review_resolution_status: ReviewStatus | None = None,
) -> ProductIntelligencePipelineRequest:
    return ProductIntelligencePipelineRequest(
        platform_listing=_listing(),
        listing_observation=_observation(),
        evidence_bundles=[bundle],
        review_resolution_status=review_resolution_status,
        review_resolution_rationale=["human-approved"] if review_resolution_status else [],
    )


def _governance_context() -> VariantGovernanceContext:
    pack = NormalizedPackEvidenceSnapshot(
        raw_quantity_text="500 ml",
        pack_kind=PackKind.single_unit,
        consumer_unit_count=1,
        content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
        total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
        packaging_form="pouch",
        component_set=[],
        pack_configuration_status="complete",
        source_artifact_reference="artifact-1",
        parser_version="parser-v1",
        capture_context_reference="context-1",
    )
    return VariantGovernanceContext(
        coverage_validation=CoverageValidationSnapshot(
            declaration_id="coverage-1",
            coverage_scope_id="scope-1",
            declared_state=CoverageState.representative,
            validation_state=CoverageValidationState.valid,
            rationale=["coverage=valid"],
        ),
        freshness=FreshnessSnapshot(
            freshness_state=FreshnessState.fresh,
            lineage_root_id="lineage-root-1",
            revision_ids=["revision-1"],
            supersession_ids=[],
            rationale=["freshness=fresh"],
        ),
        upstream_failures=[],
        normalized_pack_evidence=pack,
    )


class _StaticVariantGovernanceHooks(VariantGovernanceHooks):
    def __init__(self, governance: VariantGovernanceContext) -> None:
        self._governance = governance

    async def collect(self, request):
        return self._governance


class _RecordingEvidenceRegistry(EvidenceRegistry):
    def __init__(self, delegate: EvidenceRegistry, calls: list[str]) -> None:
        self._delegate = delegate
        self._calls = calls

    async def register(self, request):
        self._calls.append("evidence.register")
        return await self._delegate.register(request)

    async def assemble(self, request):
        self._calls.append("evidence.assemble")
        return await self._delegate.assemble(request)


class _RecordingCandidateGenerator(CandidateGenerator):
    def __init__(self, delegate: CandidateGenerator, calls: list[str]) -> None:
        self._delegate = delegate
        self._calls = calls

    async def generate(self, request):
        self._calls.append("candidate.generate")
        return await self._delegate.generate(request)


class _RecordingProductMatcher(ProductMatcher):
    def __init__(self, delegate: ProductMatcher, calls: list[str]) -> None:
        self._delegate = delegate
        self._calls = calls

    async def match(self, request):
        self._calls.append("product.match")
        return await self._delegate.match(request)


class _RecordingVariantMatcher(VariantMatcher):
    def __init__(self, delegate: VariantMatcher, calls: list[str]) -> None:
        self._delegate = delegate
        self._calls = calls

    async def match(self, request):
        self._calls.append("variant.match")
        return await self._delegate.match(request)


class _RecordingReviewQueueManager(ReviewQueueManager):
    def __init__(self, delegate: DeterministicReviewQueueManager, calls: list[str]) -> None:
        self._delegate = delegate
        self._calls = calls

    async def enqueue(self, review_case):
        self._calls.append("review.enqueue")
        return await self._delegate.enqueue(review_case)

    async def resolve(self, decision):
        self._calls.append("review.resolve")
        return await self._delegate.resolve(decision)

    def get_review_case(self, review_case_id: str):
        return self._delegate.get_review_case(review_case_id)

    def get_review_record(self, review_case_id: str):
        return self._delegate.get_review_record(review_case_id)


class _RecordingAssertionManager(AssertionManager):
    def __init__(self, delegate: DeterministicAssertionManager, calls: list[str]) -> None:
        self._delegate = delegate
        self._calls = calls

    async def apply(self, request):
        self._calls.append("assertion.apply")
        return await self._delegate.apply(request)


def _build_orchestrator(
    tmp_path,
    *,
    variants: tuple[ProductVariant, ...],
    calls: list[str] | None = None,
):
    calls = calls if calls is not None else []
    store = EvidenceFilesystemStore(root_dir=tmp_path / "evidence")
    base_registry = FilesystemEvidenceRegistry(store=store)
    evidence_registry = _RecordingEvidenceRegistry(base_registry, calls)
    candidate_generator = _RecordingCandidateGenerator(
        DeterministicCandidateGenerationService(
            CandidateCatalogSnapshot(products=(_product(),), variants=variants)
        ),
        calls,
    )
    product_matcher = _RecordingProductMatcher(DeterministicProductMatcher(), calls)
    variant_matcher = _RecordingVariantMatcher(
        DeterministicVariantMatcher(
            governance_hooks=_StaticVariantGovernanceHooks(_governance_context())
        ),
        calls,
    )
    review_queue = _RecordingReviewQueueManager(DeterministicReviewQueueManager(), calls)
    assertion_manager = _RecordingAssertionManager(DeterministicAssertionManager(), calls)
    orchestrator = DeterministicProductIntelligenceOrchestrator(
        evidence_registry=evidence_registry,
        candidate_generator=candidate_generator,
        product_matcher=product_matcher,
        variant_matcher=variant_matcher,
        review_queue_manager=review_queue,
        assertion_manager=assertion_manager,
    )
    return orchestrator, base_registry, review_queue, assertion_manager, calls


def _register_bundle(base_registry: FilesystemEvidenceRegistry) -> EvidenceReference:
    registration = _run(base_registry.register(_registration_request()))
    return registration.evidence_bundle


def test_successful_end_to_end_pipeline_applies_canonical_assertion(tmp_path) -> None:
    calls: list[str] = []
    orchestrator, base_registry, review_queue, assertion_manager, calls = _build_orchestrator(
        tmp_path,
        variants=(_variant("variant-1"),),
        calls=calls,
    )
    bundle = _register_bundle(base_registry)

    result = _run(orchestrator.execute(_pipeline_request(bundle)))

    assert result.final_pipeline_outcome == PipelineOutcome.asserted
    assert result.review_result is None
    assert result.assertion_result is not None
    assert result.product_match_result.outcome.value == "mapped"
    assert result.variant_match_result is not None
    assert result.variant_match_result.outcome.value == "mapped"
    assert calls == [
        "evidence.assemble",
        "candidate.generate",
        "product.match",
        "variant.match",
        "assertion.apply",
    ]
    assert len(review_queue._delegate.list_review_cases()) == 0
    assert len(assertion_manager._delegate._product_states) == 1


def test_ambiguous_variant_match_requires_review(tmp_path) -> None:
    calls: list[str] = []
    orchestrator, base_registry, review_queue, assertion_manager, calls = _build_orchestrator(
        tmp_path,
        variants=(
            _variant("variant-a"),
            _variant("variant-b"),
        ),
        calls=calls,
    )
    bundle = _register_bundle(base_registry)

    result = _run(orchestrator.execute(_pipeline_request(bundle)))

    assert result.final_pipeline_outcome == PipelineOutcome.review_queued
    assert result.review_result is not None
    assert result.review_result.review_case.review_status == ReviewStatus.queued
    assert result.assertion_result is None
    assert result.variant_match_result is not None
    assert result.variant_match_result.outcome.value == "ambiguous"
    assert calls == [
        "evidence.assemble",
        "candidate.generate",
        "product.match",
        "variant.match",
        "review.enqueue",
    ]
    assert len(review_queue._delegate.list_review_cases()) == 1
    assert len(assertion_manager._delegate._product_states) == 0


def test_approved_review_leads_to_assertion_update(tmp_path) -> None:
    calls: list[str] = []
    orchestrator, base_registry, review_queue, assertion_manager, calls = _build_orchestrator(
        tmp_path,
        variants=(
            _variant("variant-a"),
            _variant("variant-b"),
        ),
        calls=calls,
    )
    bundle = _register_bundle(base_registry)

    result = _run(
        orchestrator.execute(
            _pipeline_request(
                bundle,
                review_resolution_status=ReviewStatus.approved,
            )
        )
    )

    assert result.final_pipeline_outcome == PipelineOutcome.asserted
    assert result.review_result is not None
    assert result.review_result.review_case.review_status == ReviewStatus.approved
    assert result.assertion_result is not None
    assert calls == [
        "evidence.assemble",
        "candidate.generate",
        "product.match",
        "variant.match",
        "review.enqueue",
        "review.resolve",
        "assertion.apply",
    ]
    assert len(review_queue._delegate.list_review_cases()) == 1
    assert len(assertion_manager._delegate._product_states) == 1


def test_rejected_review_prevents_assertion_update(tmp_path) -> None:
    calls: list[str] = []
    orchestrator, base_registry, review_queue, assertion_manager, calls = _build_orchestrator(
        tmp_path,
        variants=(
            _variant("variant-a"),
            _variant("variant-b"),
        ),
        calls=calls,
    )
    bundle = _register_bundle(base_registry)

    result = _run(
        orchestrator.execute(
            _pipeline_request(
                bundle,
                review_resolution_status=ReviewStatus.rejected,
            )
        )
    )

    assert result.final_pipeline_outcome == PipelineOutcome.completed_without_assertion
    assert result.review_result is not None
    assert result.review_result.review_case.review_status == ReviewStatus.rejected
    assert result.assertion_result is None
    assert calls == [
        "evidence.assemble",
        "candidate.generate",
        "product.match",
        "variant.match",
        "review.enqueue",
        "review.resolve",
    ]
    assert len(review_queue._delegate.list_review_cases()) == 1
    assert len(assertion_manager._delegate._product_states) == 0


def test_fail_closed_component_failure_stops_pipeline(tmp_path) -> None:
    calls: list[str] = []
    orchestrator, base_registry, review_queue, assertion_manager, calls = _build_orchestrator(
        tmp_path,
        variants=(_variant("variant-1"),),
        calls=calls,
    )
    bundle = _register_bundle(base_registry)

    class _FailingCandidateGenerator(CandidateGenerator):
        async def generate(self, request):
            calls.append("candidate.generate")
            raise RuntimeError("candidate generation failed")

    orchestrator.candidate_generator = _FailingCandidateGenerator()

    with pytest.raises(RuntimeError):
        _run(orchestrator.execute(_pipeline_request(bundle)))

    assert calls == ["evidence.assemble", "candidate.generate"]
    assert len(review_queue._delegate.list_review_cases()) == 0
    assert len(assertion_manager._delegate._product_states) == 0


def test_deterministic_replay_preserves_serialized_result(tmp_path) -> None:
    calls: list[str] = []
    orchestrator, base_registry, _, _, _ = _build_orchestrator(
        tmp_path,
        variants=(
            _variant("variant-a"),
            _variant("variant-b"),
        ),
        calls=calls,
    )
    bundle = _register_bundle(base_registry)
    request = _pipeline_request(
        bundle,
        review_resolution_status=ReviewStatus.approved,
    )

    first = _run(orchestrator.execute(request))
    second = _run(orchestrator.execute(request.model_copy(deep=True)))

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.final_pipeline_outcome == PipelineOutcome.asserted
    assert second.final_pipeline_outcome == PipelineOutcome.asserted


def test_invocation_ordering_is_deterministic(tmp_path) -> None:
    calls: list[str] = []
    orchestrator, base_registry, _, _, calls = _build_orchestrator(
        tmp_path,
        variants=(
            _variant("variant-a"),
            _variant("variant-b"),
        ),
        calls=calls,
    )
    bundle = _register_bundle(base_registry)

    _run(
        orchestrator.execute(
            _pipeline_request(
                bundle,
                review_resolution_status=ReviewStatus.approved,
            )
        )
    )

    assert calls == [
        "evidence.assemble",
        "candidate.generate",
        "product.match",
        "variant.match",
        "review.enqueue",
        "review.resolve",
        "assertion.apply",
    ]


def test_immutable_evidence_propagation(tmp_path) -> None:
    orchestrator, base_registry, _, _, _ = _build_orchestrator(
        tmp_path,
        variants=(_variant("variant-1"),),
    )
    bundle = _register_bundle(base_registry)
    bundle_snapshot = bundle.model_dump(mode="json")

    result = _run(orchestrator.execute(_pipeline_request(bundle)))

    assert bundle.model_dump(mode="json") == bundle_snapshot
    assert len(result.evidence_result) == 1
    assert result.evidence_result[0].model_dump(mode="json") == bundle_snapshot


def test_assertion_manager_invoked_only_when_permitted(tmp_path) -> None:
    calls: list[str] = []
    orchestrator, base_registry, review_queue, assertion_manager, calls = _build_orchestrator(
        tmp_path,
        variants=(
            _variant("variant-a"),
            _variant("variant-b"),
        ),
        calls=calls,
    )
    bundle = _register_bundle(base_registry)

    queued_result = _run(orchestrator.execute(_pipeline_request(bundle)))
    approved_result = _run(
        orchestrator.execute(
            _pipeline_request(
                bundle,
                review_resolution_status=ReviewStatus.approved,
            )
        )
    )

    assert queued_result.assertion_result is None
    assert approved_result.assertion_result is not None
    assert calls.count("assertion.apply") == 1
    assert len(review_queue._delegate.list_review_cases()) == 1
    assert len(assertion_manager._delegate._product_states) == 1
