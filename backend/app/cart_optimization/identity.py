from __future__ import annotations

import json

from pydantic import BaseModel

from app.cart_optimization.types import CandidatePlan, CartOptimizationRequest


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

    def build_request_identity(self, request: CartOptimizationRequest) -> dict[str, object]:
        """Build the canonical request identity fields defined by the contract."""
        linked_evaluation_ids = [
            plan.effective_cost_evaluation_reference.effective_cost_evaluation_id
            for plan in request.candidate_plans
        ]
        ordered_linked_evaluation_ids: list[str] = []
        for evaluation_id in sorted(linked_evaluation_ids):
            if evaluation_id not in ordered_linked_evaluation_ids:
                ordered_linked_evaluation_ids.append(evaluation_id)
        return {
            "cart_items": self._canonical_models(
                request.cart_items,
                ("canonical_variant_id", "item_id", "quantity"),
            ),
            "candidate_plans": tuple(
                sorted(
                    (self.build(plan) for plan in request.candidate_plans),
                    key=lambda item: item["plan_id"],
                )
            ),
            "constraints": self._canonical_models_by_json(request.constraints),
            "effective_cost_evaluation_ids": tuple(ordered_linked_evaluation_ids),
            "optimization_policy_version": request.optimization_policy_version,
        }

    def _canonical_models(
        self, models: tuple[BaseModel, ...], sort_fields: tuple[str, ...]
    ) -> tuple[dict[str, object], ...]:
        serialized = [
            {
                field: model.model_dump(mode="json")[field]
                for field in sort_fields
            }
            for model in models
        ]
        return tuple(
            sorted(
                serialized,
                key=lambda item: tuple(str(item[field]) for field in sort_fields),
            )
        )

    def _canonical_models_by_json(self, models: tuple[BaseModel, ...]) -> tuple[dict[str, object], ...]:
        serialized = [model.model_dump(mode="json") for model in models]
        return tuple(
            sorted(
                serialized,
                key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
            )
        )
