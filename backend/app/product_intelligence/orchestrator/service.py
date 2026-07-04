from __future__ import annotations

import json
from enum import StrEnum

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.product_intelligence.assertions.interfaces import AssertionManager
from app.product_intelligence.assertions.types import (
    AssertionUpdateRequest,
    AssertionUpdateResponse,
)
from app.product_intelligence.assertions.service import (
    DeterministicAssertionRequestFactory,
)
from app.product_intelligence.candidate_generation.interfaces import CandidateGenerator
from app.product_intelligence.candidate_generation.types import (
    CandidateGenerationRequest,
    CandidateGenerationResponse,
)
from app.product_intelligence.evidence.interfaces import EvidenceRegistry
from app.product_intelligence.evidence.types import EvidenceBundle
from app.product_intelligence.matching import ProductMatcher, VariantMatcher
from app.product_intelligence.matching.types import (
    MatchOutcome,
    ProductMatchRequest,
    ProductMatchResponse,
    VariantMatchRequest,
    VariantMatchResponse,
)
from app.product_intelligence.review.interfaces import ReviewQueueManager
from app.product_intelligence.review.types import ReviewCase, ReviewDecision, ReviewStatus
from app.product_intelligence.models import EvidenceReference, ListingObservation, PlatformListing, Product, ProductVariant


logger = get_logger(__name__)


class PipelineOutcome(StrEnum):
    """Deterministic orchestration outcomes."""

    asserted = "asserted"
    review_queued = "review_queued"
    completed_without_assertion = "completed_without_assertion"


class ProductIntelligencePipelineRequest(BaseModel):
    """Input for deterministic product-intelligence orchestration."""

    platform_listing: PlatformListing
    listing_observation: ListingObservation
    evidence_bundles: list[EvidenceBundle] = Field(default_factory=list)
    review_resolution_status: ReviewStatus | None = None
    review_resolution_rationale: list[str] = Field(default_factory=list)


class _ReviewPipelineResult(BaseModel):
    """Internal review artifact preserved in the pipeline result."""

    review_case_id: str
    review_case: ReviewCase
    decision_rationale: list[str] = Field(default_factory=list)


class ProductIntelligencePipelineResult(BaseModel):
    """Deterministic result of the end-to-end product-intelligence pipeline."""

    evidence_result: list[EvidenceBundle] = Field(default_factory=list)
    candidate_generation_result: CandidateGenerationResponse
    product_match_result: ProductMatchResponse
    variant_match_result: VariantMatchResponse | None = None
    review_result: _ReviewPipelineResult | None = None
    assertion_result: AssertionUpdateResponse | None = None
    final_pipeline_outcome: PipelineOutcome


class DeterministicProductIntelligenceOrchestrator:
    """Coordinate the deterministic product-intelligence pipeline."""

    def __init__(
        self,
        *,
        evidence_registry: EvidenceRegistry,
        candidate_generator: CandidateGenerator,
        product_matcher: ProductMatcher,
        variant_matcher: VariantMatcher,
        review_queue_manager: ReviewQueueManager,
        assertion_manager: AssertionManager,
        assertion_request_factory: DeterministicAssertionRequestFactory | None = None,
    ) -> None:
        self.evidence_registry = evidence_registry
        self.candidate_generator = candidate_generator
        self.product_matcher = product_matcher
        self.variant_matcher = variant_matcher
        self.review_queue_manager = review_queue_manager
        self.assertion_manager = assertion_manager
        self.assertion_request_factory = (
            assertion_request_factory or DeterministicAssertionRequestFactory()
        )

    async def execute(
        self,
        request: ProductIntelligencePipelineRequest,
    ) -> ProductIntelligencePipelineResult:
        self._validate_request(request)

        evidence_result = await self._assemble_evidence(request.evidence_bundles)
        evidence_references = self._merge_evidence_references(evidence_result)

        candidate_generation_result = await self.candidate_generator.generate(
            CandidateGenerationRequest(
                platform_listing=request.platform_listing.model_copy(deep=True),
                listing_observation=request.listing_observation.model_copy(deep=True),
                evidence_references=evidence_references,
            )
        )

        product_match_result = await self.product_matcher.match(
            ProductMatchRequest(
                platform_listing=request.platform_listing.model_copy(deep=True),
                listing_observation=request.listing_observation.model_copy(deep=True),
                evidence_references=evidence_references,
                product_candidates=[
                    product.model_copy(deep=True)
                    for product in candidate_generation_result.product_candidates
                ],
            )
        )

        variant_match_result = await self.variant_matcher.match(
            VariantMatchRequest(
                platform_listing=request.platform_listing.model_copy(deep=True),
                listing_observation=request.listing_observation.model_copy(deep=True),
                evidence_references=evidence_references,
                product=(
                    product_match_result.selected_product.model_copy(deep=True)
                    if product_match_result.selected_product is not None
                    else None
                ),
                variant_candidates=[
                    variant.model_copy(deep=True)
                    for variant in candidate_generation_result.variant_candidates
                ],
            )
        )

        review_result: _ReviewPipelineResult | None = None
        assertion_result: AssertionUpdateResponse | None = None
        final_pipeline_outcome = PipelineOutcome.completed_without_assertion

        review_outcome = self._review_outcome(product_match_result, variant_match_result)
        review_required = self._requires_review(review_outcome)

        if request.review_resolution_status is not None and not review_required:
            raise ValueError(
                "review resolution may only be supplied when review is required"
            )

        if review_required:
            review_case = ReviewCase(
                platform_listing=request.platform_listing.model_copy(deep=True),
                listing_observation=request.listing_observation.model_copy(deep=True),
                evidence_references=[
                    reference.model_copy(deep=True) for reference in evidence_references
                ],
                product_candidates=[
                    product.model_copy(deep=True)
                    for product in candidate_generation_result.product_candidates
                ],
                variant_candidates=[
                    variant.model_copy(deep=True)
                    for variant in candidate_generation_result.variant_candidates
                ],
                match_outcome=review_outcome,
            )
            review_case_id = await self.review_queue_manager.enqueue(review_case)
            decision_rationale: list[str] = []
            review_case = review_case.model_copy(deep=True)

            if request.review_resolution_status is not None:
                if (
                    self._current_review_status(review_case_id)
                    != request.review_resolution_status
                ):
                    await self.review_queue_manager.resolve(
                        ReviewDecision(
                            review_case_id=review_case_id,
                            review_status=request.review_resolution_status,
                            rationale=list(request.review_resolution_rationale),
                        )
                    )
                decision_rationale = list(request.review_resolution_rationale)
                review_case = review_case.model_copy(
                    update={"review_status": request.review_resolution_status},
                    deep=True,
                )
                if request.review_resolution_status == ReviewStatus.approved:
                    assertion_request = self._assertion_request_for_review(
                        request=request,
                        product_match_result=product_match_result,
                        variant_match_result=variant_match_result,
                        review_case_id=review_case_id,
                    )
                    if assertion_request is not None:
                        assertion_result = await self.assertion_manager.apply(
                            assertion_request
                        )
                        final_pipeline_outcome = PipelineOutcome.asserted
                    else:
                        final_pipeline_outcome = PipelineOutcome.completed_without_assertion
                else:
                    final_pipeline_outcome = PipelineOutcome.completed_without_assertion
            else:
                final_pipeline_outcome = PipelineOutcome.review_queued

            review_result = _ReviewPipelineResult(
                review_case_id=review_case_id,
                review_case=review_case,
                decision_rationale=decision_rationale,
            )
        else:
            assertion_request = self._assertion_request_for_direct_acceptance(
                request=request,
                product_match_result=product_match_result,
                variant_match_result=variant_match_result,
            )
            if assertion_request is not None:
                assertion_result = await self.assertion_manager.apply(assertion_request)
                final_pipeline_outcome = PipelineOutcome.asserted

        result = ProductIntelligencePipelineResult(
            evidence_result=[
                bundle.model_copy(deep=True) for bundle in evidence_result
            ],
            candidate_generation_result=candidate_generation_result.model_copy(deep=True),
            product_match_result=product_match_result.model_copy(deep=True),
            variant_match_result=(
                variant_match_result.model_copy(deep=True)
                if variant_match_result is not None
                else None
            ),
            review_result=review_result.model_copy(deep=True) if review_result else None,
            assertion_result=(
                assertion_result.model_copy(deep=True)
                if assertion_result is not None
                else None
            ),
            final_pipeline_outcome=final_pipeline_outcome,
        )
        logger.info(
            "product_intelligence_pipeline_complete platform=%s outcome=%s",
            request.platform_listing.platform,
            final_pipeline_outcome.value,
        )
        return result

    async def _assemble_evidence(
        self,
        evidence_bundles: list[EvidenceBundle],
    ) -> list[EvidenceBundle]:
        assembled: list[EvidenceBundle] = []
        for bundle in self._canonicalize_evidence_bundles(evidence_bundles):
            assembled.append(await self.evidence_registry.assemble(bundle))
        return assembled

    def _validate_request(self, request: ProductIntelligencePipelineRequest) -> None:
        if not request.evidence_bundles:
            raise ValueError("pipeline request requires at least one evidence bundle")
        if request.review_resolution_status is not None and request.review_resolution_status == ReviewStatus.queued:
            raise ValueError("pipeline review resolution cannot request queued status")

        platforms = {bundle.platform for bundle in request.evidence_bundles}
        if len(platforms) > 1:
            raise ValueError("pipeline request evidence bundles must share one platform")
        if request.platform_listing.platform not in platforms:
            raise ValueError("platform listing platform must match evidence bundle platform")

    def _canonicalize_evidence_bundles(
        self,
        evidence_bundles: list[EvidenceBundle],
    ) -> list[EvidenceBundle]:
        seen: set[str] = set()
        canonical: list[tuple[str, EvidenceBundle]] = []
        for bundle in evidence_bundles:
            canonical_bundle = bundle.model_copy(deep=True)
            payload = json.dumps(
                canonical_bundle.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            if payload in seen:
                continue
            seen.add(payload)
            canonical.append((payload, canonical_bundle))
        canonical.sort(key=lambda item: item[0])
        return [bundle for _, bundle in canonical]

    def _merge_evidence_references(
        self,
        evidence_bundles: list[EvidenceBundle],
    ) -> list[EvidenceReference]:
        canonical: dict[tuple[str, str], EvidenceReference] = {}
        for bundle in evidence_bundles:
            for reference in bundle.evidence_references:
                source_type = reference.source_type.strip()
                source_id = reference.source_id.strip()
                if not source_type or not source_id:
                    raise ValueError(
                        "evidence bundle contains blank evidence reference identity"
                    )
                key = (source_type, source_id)
                if key not in canonical:
                    canonical[key] = reference.model_copy(
                        update={"source_type": source_type, "source_id": source_id},
                        deep=True,
                    )
        return [canonical[key] for key in sorted(canonical)]

    def _review_outcome(
        self,
        product_match_result: ProductMatchResponse,
        variant_match_result: VariantMatchResponse,
    ) -> MatchOutcome:
        if self._requires_review(product_match_result.outcome):
            return product_match_result.outcome
        return variant_match_result.outcome

    def _requires_review(self, outcome: MatchOutcome) -> bool:
        return outcome in {
            MatchOutcome.ambiguous,
            MatchOutcome.unresolved,
            MatchOutcome.conflicting,
            MatchOutcome.rejected,
        }

    def _assertion_request_for_direct_acceptance(
        self,
        *,
        request: ProductIntelligencePipelineRequest,
        product_match_result: ProductMatchResponse,
        variant_match_result: VariantMatchResponse,
    ) -> AssertionUpdateRequest | None:
        if product_match_result.outcome != MatchOutcome.mapped:
            return None
        if variant_match_result.outcome != MatchOutcome.mapped:
            return None
        if product_match_result.selected_product is None:
            return None
        if variant_match_result.selected_variant is None:
            return None
        return self.assertion_request_factory.build(
            product=product_match_result.selected_product,
            variant=variant_match_result.selected_variant,
            evidence_references=self._merge_evidence_references(request.evidence_bundles),
            decision_references=[
                f"product_match:{product_match_result.selected_product.canonical_product_id}",
                f"variant_match:{variant_match_result.selected_variant.canonical_variant_id}",
            ],
        )

    def _assertion_request_for_review(
        self,
        *,
        request: ProductIntelligencePipelineRequest,
        product_match_result: ProductMatchResponse,
        variant_match_result: VariantMatchResponse,
        review_case_id: str,
    ) -> AssertionUpdateRequest | None:
        if product_match_result.selected_product is None:
            return None
        return self.assertion_request_factory.build(
            product=product_match_result.selected_product,
            variant=(
                variant_match_result.selected_variant
                if variant_match_result.outcome == MatchOutcome.mapped
                else None
            ),
            evidence_references=self._merge_evidence_references(request.evidence_bundles),
            decision_references=[
                f"review_case:{review_case_id}",
                f"product_match:{product_match_result.selected_product.canonical_product_id}",
                f"variant_match:{variant_match_result.outcome.value}",
            ],
        )

    def _current_review_status(self, review_case_id: str) -> ReviewStatus | None:
        record = self.review_queue_manager.get_review_record(review_case_id)
        if record is not None:
            return record.review_case.review_status
        review_case = self.review_queue_manager.get_review_case(review_case_id)
        if review_case is not None:
            return review_case.review_status
        return None
