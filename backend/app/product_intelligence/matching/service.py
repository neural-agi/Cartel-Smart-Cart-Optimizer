from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.product_intelligence.candidate_generation.strategies import tokenize, unique_tokens
from app.product_intelligence.matching.interfaces import ProductMatcher
from app.product_intelligence.matching.types import (
    MatchOutcome,
    ProductMatchRequest,
    ProductMatchResponse,
)
from app.product_intelligence.models import Product


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ProductMatchSignal:
    """Deterministic evidence summary for a product candidate."""

    brand_overlap: int
    family_overlap: int
    category_overlap: int
    attribute_overlap: int

    @property
    def total(self) -> int:
        return (
            self.brand_overlap
            + self.family_overlap
            + self.category_overlap
            + self.attribute_overlap
        )


class DeterministicProductMatcher(ProductMatcher):
    """Evidence-driven matcher for canonical product identity."""

    async def match(self, request: ProductMatchRequest) -> ProductMatchResponse:
        if not request.product_candidates:
            rationale = self._build_request_rationale(
                request=request,
                outcome=MatchOutcome.unresolved,
                detail="no product candidates supplied",
            )
            logger.info(
                "product_match_unresolved platform=%s reason=no_candidates",
                request.platform_listing.platform,
            )
            return ProductMatchResponse(
                outcome=MatchOutcome.unresolved,
                selected_product=None,
                rationale=rationale,
            )

        listing_tokens = unique_tokens(
            request.platform_listing.raw_title,
            request.platform_listing.raw_category_text,
        )
        ranked = [
            (
                product,
                self._signal_for_candidate(product, request, listing_tokens),
            )
            for product in request.product_candidates
        ]
        ranked.sort(
            key=lambda item: (
                item[1].total,
                item[1].brand_overlap,
                item[1].family_overlap,
                item[1].category_overlap,
                item[1].attribute_overlap,
                item[0].canonical_display_name.lower(),
            ),
            reverse=True,
        )

        best_product, best_signal = ranked[0]
        tied = [
            item
            for item in ranked
            if item[1].total == best_signal.total
            and item[1].brand_overlap == best_signal.brand_overlap
            and item[1].family_overlap == best_signal.family_overlap
            and item[1].category_overlap == best_signal.category_overlap
            and item[1].attribute_overlap == best_signal.attribute_overlap
        ]

        if best_signal.total == 0:
            if len(tied) > 1:
                rationale = self._build_tie_rationale(
                    request=request,
                    tied_candidates=[candidate for candidate, _ in tied],
                    signal=best_signal,
                    outcome=MatchOutcome.ambiguous,
                    detail="multiple product candidates tied with no positive overlap",
                )
                logger.info(
                    "product_match_ambiguous platform=%s tied_candidates=%s",
                    request.platform_listing.platform,
                    len(tied),
                )
                return ProductMatchResponse(
                    outcome=MatchOutcome.ambiguous,
                    selected_product=None,
                    rationale=rationale,
                )
            rationale = self._build_candidate_rationale(
                request=request,
                product=best_product,
                signal=best_signal,
                outcome=MatchOutcome.rejected,
                detail="single candidate lacks positive overlap",
            )
            logger.info(
                "product_match_rejected platform=%s reason=no_positive_overlap",
                request.platform_listing.platform,
            )
            return ProductMatchResponse(
                outcome=MatchOutcome.rejected,
                selected_product=None,
                rationale=rationale,
            )

        if len(tied) > 1:
            rationale = self._build_tie_rationale(
                request=request,
                tied_candidates=[candidate for candidate, _ in tied],
                signal=best_signal,
                outcome=MatchOutcome.ambiguous,
                detail="multiple product candidates tied on deterministic signals",
            )
            logger.info(
                "product_match_ambiguous platform=%s tied_candidates=%s",
                request.platform_listing.platform,
                len(tied),
            )
            return ProductMatchResponse(
                outcome=MatchOutcome.ambiguous,
                selected_product=None,
                rationale=rationale,
            )

        if self._evidence_conflicts(request=request, product=best_product):
            rationale = self._build_candidate_rationale(
                request=request,
                product=best_product,
                signal=best_signal,
                outcome=MatchOutcome.conflicting,
                detail="candidate evidence conflicts with listing evidence",
            )
            logger.info(
                "product_match_conflicting platform=%s product_id=%s",
                request.platform_listing.platform,
                best_product.canonical_product_id,
            )
            return ProductMatchResponse(
                outcome=MatchOutcome.conflicting,
                selected_product=None,
                rationale=rationale,
            )

        if self._strong_reject(request=request, product=best_product, signal=best_signal):
            rationale = self._build_candidate_rationale(
                request=request,
                product=best_product,
                signal=best_signal,
                outcome=MatchOutcome.rejected,
                detail="candidate lacks sufficient product-family support",
            )
            logger.info(
                "product_match_rejected platform=%s product_id=%s",
                request.platform_listing.platform,
                best_product.canonical_product_id,
            )
            return ProductMatchResponse(
                outcome=MatchOutcome.rejected,
                selected_product=None,
                rationale=rationale,
            )

        rationale = self._build_candidate_rationale(
            request=request,
            product=best_product,
            signal=best_signal,
            outcome=MatchOutcome.mapped,
            detail="deterministic product evidence supports mapping",
        )
        logger.info(
            "product_match_mapped platform=%s product_id=%s",
            request.platform_listing.platform,
            best_product.canonical_product_id,
        )
        return ProductMatchResponse(
            outcome=MatchOutcome.mapped,
            selected_product=best_product,
            rationale=rationale,
        )

    def _signal_for_candidate(
        self,
        product: Product,
        request: ProductMatchRequest,
        listing_tokens: set[str],
    ) -> ProductMatchSignal:
        brand_tokens = set(tokenize(product.brand_reference.display_label))
        family_tokens = unique_tokens(
            product.canonical_display_name,
            product.product_type,
        )
        category_tokens = unique_tokens(
            product.canonical_category_reference.category_path,
            product.canonical_category_reference.category_id,
        )
        attribute_tokens: set[str] = set()
        for attribute in product.identity_attributes:
            attribute_tokens.update(tokenize(attribute.name))
            attribute_tokens.update(tokenize(attribute.value))
            if attribute.qualifier:
                attribute_tokens.update(tokenize(attribute.qualifier))

        return ProductMatchSignal(
            brand_overlap=len(brand_tokens & listing_tokens),
            family_overlap=len(family_tokens & listing_tokens),
            category_overlap=len(category_tokens & listing_tokens),
            attribute_overlap=len(attribute_tokens & listing_tokens),
        )

    def _evidence_conflicts(self, request: ProductMatchRequest, product: Product) -> bool:
        listing_category = set(tokenize(request.platform_listing.raw_category_text))
        product_category = unique_tokens(
            product.canonical_category_reference.category_path,
            product.canonical_category_reference.category_id,
        )
        brand_tokens = set(tokenize(product.brand_reference.display_label))
        title_tokens = set(tokenize(request.platform_listing.raw_title))
        listing_tokens = title_tokens | listing_category
        has_positive_support = bool(
            (brand_tokens & listing_tokens)
            or (title_tokens and unique_tokens(product.canonical_display_name, product.product_type) & listing_tokens)
            or (product.identity_attributes and any(
                tokenize(attribute.name) or tokenize(attribute.value) or (tokenize(attribute.qualifier) if attribute.qualifier else [])
                for attribute in product.identity_attributes
            ))
        )
        if has_positive_support and listing_category and product_category and not listing_category & product_category:
            return True
        return False

    def _strong_reject(
        self,
        request: ProductMatchRequest,
        product: Product,
        signal: ProductMatchSignal,
    ) -> bool:
        if signal.family_overlap == 0 and signal.brand_overlap == 0:
            return True
        product_family_tokens = unique_tokens(
            product.canonical_display_name,
            product.product_type,
        )
        listing_tokens = unique_tokens(
            request.platform_listing.raw_title,
            request.platform_listing.raw_category_text,
        )
        if product.brand_reference.is_unknown:
            return signal.family_overlap == 0 and signal.attribute_overlap == 0
        if product_family_tokens and not product_family_tokens & listing_tokens:
            return signal.brand_overlap == 0 and signal.attribute_overlap == 0
        return False

    def _build_request_rationale(
        self,
        *,
        request: ProductMatchRequest,
        outcome: MatchOutcome,
        detail: str,
    ) -> list[str]:
        rationale = [
            f"outcome={outcome.value}",
            f"platform={request.platform_listing.platform}",
            f"raw_title={request.platform_listing.raw_title}",
            f"detail={detail}",
        ]
        if request.platform_listing.raw_category_text:
            rationale.append(
                f"raw_category={request.platform_listing.raw_category_text}"
            )
        if request.listing_observation.parser_version:
            rationale.append(
                f"parser_version={request.listing_observation.parser_version}"
            )
        if request.listing_observation.capture_timestamp:
            rationale.append(
                f"capture_timestamp={request.listing_observation.capture_timestamp.isoformat()}"
            )
        if request.evidence_references:
            rationale.append(
                f"evidence_reference_count={len(request.evidence_references)}"
            )
        return rationale

    def _build_candidate_rationale(
        self,
        *,
        request: ProductMatchRequest,
        product: Product,
        signal: ProductMatchSignal,
        outcome: MatchOutcome,
        detail: str,
    ) -> list[str]:
        rationale = self._build_request_rationale(
            request=request,
            outcome=outcome,
            detail=detail,
        )
        rationale.extend(
            [
                f"selected_product_id={product.canonical_product_id}",
                f"selected_product_name={product.canonical_display_name}",
                f"brand_overlap={signal.brand_overlap}",
                f"family_overlap={signal.family_overlap}",
                f"category_overlap={signal.category_overlap}",
                f"attribute_overlap={signal.attribute_overlap}",
            ]
        )
        if product.identity_attributes:
            rationale.append(
                "identity_attributes="
                + ",".join(
                    f"{attribute.name}={attribute.value}"
                    for attribute in product.identity_attributes
                )
            )
        return rationale

    def _build_tie_rationale(
        self,
        *,
        request: ProductMatchRequest,
        tied_candidates: list[Product],
        signal: ProductMatchSignal,
        outcome: MatchOutcome,
        detail: str,
    ) -> list[str]:
        rationale = self._build_request_rationale(
            request=request,
            outcome=outcome,
            detail=detail,
        )
        rationale.append(f"tie_count={len(tied_candidates)}")
        for candidate in tied_candidates:
            rationale.append(
                f"tied_product_id={candidate.canonical_product_id}|name={candidate.canonical_display_name}"
            )
        rationale.extend(
            [
                f"brand_overlap={signal.brand_overlap}",
                f"family_overlap={signal.family_overlap}",
                f"category_overlap={signal.category_overlap}",
                f"attribute_overlap={signal.attribute_overlap}",
            ]
        )
        return rationale
