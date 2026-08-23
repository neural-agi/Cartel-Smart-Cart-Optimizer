from __future__ import annotations

import json

from pydantic import BaseModel

from app.cart_optimization.types import CandidatePlan


class CandidatePlanIdentityBuilder:
    """Build the canonical identity payload for an immutable candidate plan."""

    def build(self, plan: CandidatePlan) -> dict[str, object]:
        return {
            "plan_id": plan.plan_id,
            "inconvenience_penalty_units": plan.inconvenience_penalty_units,
            "retailer_preference_priority": plan.retailer_preference_priority,
            "retailer_allocations": self._canonical_models(
                plan.retailer_allocations,
                ("retailer_id", "checkout_group_id"),
            ),
            "item_allocations": self._canonical_models(
                plan.item_allocations,
                ("canonical_variant_id", "retailer_id", "checkout_group_id", "item_id", "quantity"),
            ),
            "candidate_item_allocations": self._canonical_serialized(
                plan.candidate_item_allocations,
            ),
            "checkout_groups": self._canonical_models(
                plan.checkout_groups,
                ("retailer_id", "checkout_group_id", "effective_cost_evaluation_id"),
            ),
            "effective_cost_evaluation_id": (
                plan.effective_cost_evaluation_reference.effective_cost_evaluation_id
            ),
            "constraint_ids": tuple(
                sorted(reference.optimization_constraint_id for reference in plan.constraint_references)
            ),
        }

    def _canonical_models(
        self, models: tuple[BaseModel, ...], sort_fields: tuple[str, ...]
    ) -> tuple[dict[str, object], ...]:
        serialized = [model.model_dump(mode="json") for model in models]
        return tuple(
            sorted(
                serialized,
                key=lambda item: tuple(str(item[field]) for field in sort_fields),
            )
        )

    @staticmethod
    def _canonical_serialized(models: tuple[BaseModel, ...]) -> tuple[str, ...]:
        """Serialize models to canonical JSON strings, sorted for deterministic ordering.

        Used for nested models whose full content (including provenance) must
        participate in plan identity.
        """
        return tuple(
            sorted(
                json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
                for model in models
            )
        )
