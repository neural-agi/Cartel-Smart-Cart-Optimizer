from __future__ import annotations

from app.product_intelligence.matching.interfaces import VariantGovernanceHooks
from app.product_intelligence.matching.types import VariantGovernanceContext
from app.product_intelligence.matching.types import VariantMatchRequest


def default_variant_governance_context() -> VariantGovernanceContext:
    """Return the conservative governed-input snapshot used by the slice."""

    return VariantGovernanceContext()


class DeterministicVariantGovernanceHooks(VariantGovernanceHooks):
    """Default governed-input collector for the first executable slice."""

    async def collect(self, request: VariantMatchRequest) -> VariantGovernanceContext:
        return default_variant_governance_context()
