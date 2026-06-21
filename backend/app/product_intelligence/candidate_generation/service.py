from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.core.logging import get_logger
from app.product_intelligence.candidate_generation.interfaces import CandidateGenerator
from app.product_intelligence.candidate_generation.ranking import RankedCandidate
from app.product_intelligence.candidate_generation.strategies import (
    CandidateSignal,
    quantity_hints,
    tokenize,
    unique_tokens,
)
from app.product_intelligence.candidate_generation.types import (
    CandidateGenerationRequest,
    CandidateGenerationResponse,
)
from app.product_intelligence.models import (
    PlatformListing,
    Product,
    ProductVariant,
)


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CandidateCatalogSnapshot:
    """In-memory canonical catalog used for deterministic candidate generation."""

    products: tuple[Product, ...] = ()
    variants: tuple[ProductVariant, ...] = ()


class DeterministicCandidateGenerationService(CandidateGenerator):
    """Recall-first candidate generator using token overlap and quantity hints."""

    def __init__(self, catalog: CandidateCatalogSnapshot | None = None) -> None:
        self.catalog = catalog or CandidateCatalogSnapshot()

    async def generate(
        self,
        request: CandidateGenerationRequest,
    ) -> CandidateGenerationResponse:
        ranked = self._rank_candidates(request)
        product_candidates = [
            item for item in ranked if item.candidate_type == "product"
        ]
        variant_candidates = [
            item for item in ranked if item.candidate_type == "variant"
        ]
        rationale = self._build_rationale(request, ranked)

        logger.info(
            "candidate_generation_complete platform=%s product_candidates=%s variant_candidates=%s",
            request.platform_listing.platform,
            len(product_candidates),
            len(variant_candidates),
        )
        return CandidateGenerationResponse(
            product_candidates=[
                self._product_from_candidate(item) for item in product_candidates
            ],
            variant_candidates=[
                self._variant_from_candidate(item) for item in variant_candidates
            ],
            rationale=rationale,
        )

    def _rank_candidates(
        self,
        request: CandidateGenerationRequest,
    ) -> list[RankedCandidate]:
        listing = request.platform_listing
        listing_tokens = unique_tokens(
            listing.raw_title,
            listing.raw_quantity_text,
            listing.raw_category_text,
        )
        quantity_tokens = quantity_hints(
            listing.raw_quantity_text,
        )

        ranked: list[RankedCandidate] = []
        ranked.extend(self._rank_products(listing_tokens, quantity_tokens, listing))
        ranked.extend(self._rank_variants(listing_tokens, quantity_tokens, listing))
        ranked.sort(key=lambda item: item.sort_key, reverse=True)
        return ranked

    def _rank_products(
        self,
        listing_tokens: set[str],
        quantity_tokens: set[str],
        listing: PlatformListing,
    ) -> list[RankedCandidate]:
        ranked: list[RankedCandidate] = []
        for product in self.catalog.products:
            brand_tokens = set(
                tokenize(product.brand_reference.display_label)
)
            family_tokens = unique_tokens(
                product.canonical_display_name,
                product.product_type,
                product.canonical_category_reference.category_path,
            )
            category_tokens = unique_tokens(
                product.canonical_category_reference.category_path,
                product.canonical_category_reference.category_id,
            )
            signal = CandidateSignal(
                brand_overlap=len(brand_tokens & listing_tokens),
                family_overlap=len(family_tokens & listing_tokens),
                category_overlap=len(category_tokens & listing_tokens),
                quantity_overlap=len(quantity_tokens & listing_tokens),
            )
            if signal.total == 0:
                continue
            ranked.append(
                RankedCandidate(
                    candidate_type="product",
                    candidate_id=product.canonical_product_id,
                    display_name=product.canonical_display_name,
                    signal=signal,
                    rationale=self._candidate_rationale(
                        listing=listing,
                        candidate_name=product.canonical_display_name,
                        signal=signal,
                        candidate_kind="product",
                    ),
                )
            )
        return ranked

    def _rank_variants(
        self,
        listing_tokens: set[str],
        quantity_tokens: set[str],
        listing: PlatformListing,
    ) -> list[RankedCandidate]:
        ranked: list[RankedCandidate] = []
        product_lookup = {product.canonical_product_id: product for product in self.catalog.products}
        for variant in self.catalog.variants:
            product = product_lookup.get(variant.canonical_product_id)
            product_tokens = unique_tokens(
                product.canonical_display_name if product else None,
                product.product_type if product else None,
                product.brand_reference.display_label if product else None,
            )
            variant_tokens = unique_tokens(
                variant.pack_configuration.packaging_form,
                variant.pack_configuration.pack_kind.value,
            )
            for attribute in variant.variant_identity_attributes:
                variant_tokens.update(tokenize(attribute.name))
                variant_tokens.update(tokenize(attribute.value))
                if attribute.qualifier:
                    variant_tokens.update(tokenize(attribute.qualifier))
            signal = CandidateSignal(
                brand_overlap=len(
                    set(tokenize(product.brand_reference.display_label)) & listing_tokens
                )
                if product
                else 0,
                family_overlap=len((product_tokens | variant_tokens) & listing_tokens),
                category_overlap=len(
                    unique_tokens(
                        product.canonical_category_reference.category_path
                        if product
                        else None,
                        product.canonical_category_reference.category_id if product else None,
                    )
                    & listing_tokens
                )
                if product
                else 0,
                quantity_overlap=len(quantity_tokens & (listing_tokens | variant_tokens)),
            )
            if signal.total == 0:
                continue
            ranked.append(
                RankedCandidate(
                    candidate_type="variant",
                    candidate_id=variant.canonical_variant_id,
                    display_name=variant.canonical_variant_id,
                    signal=signal,
                    rationale=self._candidate_rationale(
                        listing=listing,
                        candidate_name=variant.canonical_variant_id,
                        signal=signal,
                        candidate_kind="variant",
                    ),
                )
            )
        return ranked

    def _candidate_rationale(
        self,
        *,
        listing: PlatformListing,
        candidate_name: str,
        signal: CandidateSignal,
        candidate_kind: str,
    ) -> tuple[str, ...]:
        rationale = [
            f"{candidate_kind} candidate={candidate_name}",
            f"brand_overlap={signal.brand_overlap}",
            f"family_overlap={signal.family_overlap}",
            f"category_overlap={signal.category_overlap}",
            f"quantity_overlap={signal.quantity_overlap}",
        ]
        if listing.raw_quantity_text:
            rationale.append(f"listing_quantity={listing.raw_quantity_text}")
        return tuple(rationale)

    def _build_rationale(
        self,
        request: CandidateGenerationRequest,
        ranked: Sequence[RankedCandidate],
    ) -> list[str]:
        rationale = [
            f"platform={request.platform_listing.platform}",
            f"raw_title={request.platform_listing.raw_title}",
            f"candidate_pool_size={len(ranked)}",
            "ranking_prioritizes recall over precision",
        ]
        if request.platform_listing.raw_quantity_text:
            rationale.append(
                f"quantity_hints={sorted(quantity_hints(request.platform_listing.raw_quantity_text))}"
            )
        for candidate in ranked[:10]:
            rationale.append(
                "|".join(
                    (
                        f"candidate_type={candidate.candidate_type}",
                        f"candidate_id={candidate.candidate_id}",
                        f"brand_overlap={candidate.signal.brand_overlap}",
                        f"family_overlap={candidate.signal.family_overlap}",
                        f"category_overlap={candidate.signal.category_overlap}",
                        f"quantity_overlap={candidate.signal.quantity_overlap}",
                    )
                )
            )
        return rationale

    def _product_from_candidate(self, candidate: RankedCandidate) -> Product:
        for product in self.catalog.products:
            if product.canonical_product_id == candidate.candidate_id:
                return product
        raise KeyError(candidate.candidate_id)

    def _variant_from_candidate(self, candidate: RankedCandidate) -> ProductVariant:
        for variant in self.catalog.variants:
            if variant.canonical_variant_id == candidate.candidate_id:
                return variant
        raise KeyError(candidate.candidate_id)
