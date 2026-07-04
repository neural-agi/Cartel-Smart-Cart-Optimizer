from __future__ import annotations

import asyncio
import json
import sys
import warnings
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

if sys.platform.startswith("win"):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.logging import configure_logging
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
from app.product_intelligence.orchestrator import DeterministicProductIntelligenceOrchestrator
from app.product_intelligence.orchestrator.service import (
    ProductIntelligencePipelineRequest,
)
from app.product_intelligence.review import DeterministicReviewQueueManager
from app.product_intelligence.review.types import ReviewStatus
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


def _measurement(amount: str, unit: str, dimension: QuantityDimension) -> Measurement:
    return Measurement(
        value=Decimal(amount),
        unit=unit,
        dimension=dimension,
        content_basis="net_content",
        assertion_status="asserted",
    )


def _product() -> Product:
    return Product(
        canonical_product_id="product-1",
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


def _variant(variant_id: str) -> ProductVariant:
    return ProductVariant(
        canonical_variant_id=variant_id,
        canonical_product_id="product-1",
        variant_identity_status=IdentityStatus.established,
        variant_identity_attributes=[],
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.single_unit,
            consumer_unit_count=1,
            content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
            total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
            packaging_form="pouch",
            component_set=[],
            pack_configuration_status="complete",
        ),
        lifecycle_status=VariantLifecycleStatus.active,
        catalog_revision="rev-1",
        evidence_references=[],
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
        source_artifact_reference="demo/raw/blinkit/milk/rendered.html",
        parser_version="demo-parser-1",
        capture_context_reference="demo/location/new-delhi/session-001",
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


async def main() -> None:
    configure_logging(log_level="INFO", json_logs=False)

    product = _product()
    variants = (_variant("variant-a"), _variant("variant-b"))

    evidence_registry = FilesystemEvidenceRegistry(
        EvidenceFilesystemStore(root_dir=PROJECT_ROOT / "data" / "product_intelligence" / "demo_evidence")
    )
    registration = await evidence_registry.register(
        EvidenceRegistrationRequest(
            platform="blinkit",
            source_artifact_reference="demo/raw/blinkit/milk/rendered.html",
            parser_version="demo-parser-1",
            capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            capture_context_reference="demo/location/new-delhi/session-001",
        )
    )

    orchestrator = DeterministicProductIntelligenceOrchestrator(
        evidence_registry=evidence_registry,
        candidate_generator=DeterministicCandidateGenerationService(
            CandidateCatalogSnapshot(products=(product,), variants=variants)
        ),
        product_matcher=DeterministicProductMatcher(),
        variant_matcher=DeterministicVariantMatcher(
            governance_hooks=_StaticVariantGovernanceHooks(_governance_context())
        ),
        review_queue_manager=DeterministicReviewQueueManager(),
        assertion_manager=DeterministicAssertionManager(),
    )

    request = ProductIntelligencePipelineRequest(
        platform_listing=PlatformListing(
            platform="blinkit",
            platform_listing_id="blinkit_demo_001",
            raw_title="Amul Taaza Milk",
            raw_quantity_text="500 ml",
            raw_category_text="milk",
            listing_url="https://example.invalid/blinkit_demo_001",
        ),
        listing_observation=ListingObservation(
            platform_listing_id="blinkit_demo_001",
            displayed_price="31",
            reference_price="35",
            offer_text=None,
            availability_signal="ADD",
            capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            parser_version="demo-parser-1",
            source_artifact_reference="demo/raw/blinkit/milk/rendered.html",
            capture_context_reference="demo/location/new-delhi/session-001",
        ),
        evidence_bundles=[registration.evidence_bundle],
        review_resolution_status=ReviewStatus.approved,
        review_resolution_rationale=["demo-approved"],
    )

    first = await orchestrator.execute(request)
    second = await orchestrator.execute(request.model_copy(deep=True))

    for label, result in (("first_run", first), ("second_run", second)):
        print(label)
        print("evidence_result=")
        print(json.dumps(result.evidence_result[0].model_dump(mode="json"), indent=2, ensure_ascii=True))
        print("candidate_generation_result=")
        print(
            json.dumps(
                result.candidate_generation_result.model_dump(mode="json"),
                indent=2,
                ensure_ascii=True,
            )
        )
        print("product_match_result=")
        print(
            json.dumps(
                result.product_match_result.model_dump(mode="json"),
                indent=2,
                ensure_ascii=True,
            )
        )
        print("variant_match_result=")
        print(
            json.dumps(
                result.variant_match_result.model_dump(mode="json")
                if result.variant_match_result is not None
                else None,
                indent=2,
                ensure_ascii=True,
            )
        )
        print("review_result=")
        print(
            json.dumps(
                result.review_result.model_dump(mode="json")
                if result.review_result is not None
                else None,
                indent=2,
                ensure_ascii=True,
            )
        )
        print("assertion_result=")
        print(
            json.dumps(
                result.assertion_result.model_dump(mode="json")
                if result.assertion_result is not None
                else None,
                indent=2,
                ensure_ascii=True,
            )
        )
        print(f"final_pipeline_outcome={result.final_pipeline_outcome.value}")


if __name__ == "__main__":
    asyncio.run(main())
