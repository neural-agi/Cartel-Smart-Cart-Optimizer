"""Product matching contracts and deterministic service layer."""

from app.product_intelligence.matching.interfaces import ProductMatcher, VariantMatcher
from app.product_intelligence.matching.service import DeterministicProductMatcher
from app.product_intelligence.matching.variant_service import DeterministicVariantMatcher
from app.product_intelligence.matching.types import (
    MatchOutcome,
    ProductMatchRequest,
    ProductMatchResponse,
    VariantMatchRequest,
    VariantMatchResponse,
)

__all__ = [
    "DeterministicProductMatcher",
    "DeterministicVariantMatcher",
    "MatchOutcome",
    "ProductMatchRequest",
    "ProductMatchResponse",
    "ProductMatcher",
    "VariantMatchRequest",
    "VariantMatchResponse",
    "VariantMatcher",
]
