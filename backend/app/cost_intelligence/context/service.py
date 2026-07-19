"""Pure deterministic construction of Cost Context objects."""

from __future__ import annotations

import hashlib
import json

from app.cost_intelligence.context.types import CostContext
from app.cost_intelligence.observation.types import CheckoutObservation


class DeterministicCostContextBuilder:
    """Build immutable contexts without I/O, clocks, or mutable shared state."""

    def build(self, observation: CheckoutObservation) -> CostContext:
        """Build a context from an evidence-backed checkout observation."""
        if not observation.evidence_references:
            raise ValueError("cost context requires an evidence-backed observation")

        payload = json.dumps(
            observation.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        context_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return CostContext(
            context_id=context_id,
            checkout_observation=observation,
            evidence_references=tuple(observation.evidence_references),
        )
