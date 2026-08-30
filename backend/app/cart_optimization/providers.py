"""Injectable application-provider contracts for planning authorities."""

from __future__ import annotations

import hashlib
import json
from typing import Mapping, Protocol

from app.cart_optimization.enums import PlanFeasibility
from app.cost_intelligence.observation.types import CheckoutObservation
from app.cost_intelligence.observation.checkout_capture import (
    CheckoutObservationCorrelationStore,
)


class PlanningProviderUnavailable(RuntimeError):
    """Raised when an authoritative planning provider is not configured."""


class CheckoutObservationProvider(Protocol):
    def get_observation(self, *, plan_id: str, request_id: str) -> CheckoutObservation | None:
        """Return checkout evidence for one plan or None when unavailable."""


class RetailerIdentityProvider(Protocol):
    def retailer_id(self, *, item_id: str, platform: str, listing_id: str) -> str: ...


class CheckoutGroupProvider(Protocol):
    def checkout_group_id(self, *, plan_id: str, item_id: str, retailer_id: str) -> str: ...


class PlanPolicyProvider(Protocol):
    def resolve(self, *, plan_id: str) -> tuple[int, int, PlanFeasibility, tuple[str, ...]]: ...


class UnavailableCheckoutObservationProvider:
    def get_observation(self, *, plan_id: str, request_id: str) -> CheckoutObservation | None:
        raise PlanningProviderUnavailable(
            f"checkout observation provider is unavailable for plan {plan_id}"
        )


class RegistryCheckoutObservationProvider:
    """Provider adapter over explicit plan-correlated checkout persistence."""

    def __init__(self, store: CheckoutObservationCorrelationStore) -> None:
        self._store = store

    def get_observation(self, *, plan_id: str, request_id: str) -> CheckoutObservation | None:
        correlation = self._store.get(request_id, plan_id)
        return None if correlation is None else correlation.observation


class UnavailableRetailerIdentityProvider:
    """Fail-closed adapter until an authoritative retailer registry is wired."""

    def retailer_id(self, *, item_id: str, platform: str, listing_id: str) -> str:
        raise PlanningProviderUnavailable(
            "retailer identity provider is unavailable for "
            f"item {item_id}, platform {platform}, listing {listing_id}"
        )


class UnavailableCheckoutGroupProvider:
    """Fail-closed adapter until explicit grouping context is available."""

    def checkout_group_id(self, *, plan_id: str, item_id: str, retailer_id: str) -> str:
        raise PlanningProviderUnavailable(
            "checkout group provider is unavailable for "
            f"plan {plan_id}, item {item_id}, retailer {retailer_id}"
        )


class UnavailablePlanPolicyProvider:
    """Fail-closed adapter for upstream plan policy and feasibility inputs."""

    def resolve(self, *, plan_id: str) -> tuple[int, int, PlanFeasibility, tuple[str, ...]]:
        raise PlanningProviderUnavailable(
            f"plan policy provider is unavailable for plan {plan_id}"
        )


class ConfiguredRetailerIdentityProvider:
    """Resolve opaque retailer IDs from an explicit listing mapping.

    The mapping key is ``platform|platform_listing_id``.  No retailer identity
    is derived from either component.
    """

    def __init__(self, mapping: Mapping[str, str]) -> None:
        self._mapping = self._validate(mapping)

    @staticmethod
    def _validate(mapping: Mapping[str, str]) -> dict[str, str]:
        result = {}
        for key, value in mapping.items():
            if not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip():
                raise ValueError("retailer identity mappings must contain non-empty strings")
            result[key.strip()] = value.strip()
        return result

    def retailer_id(self, *, item_id: str, platform: str, listing_id: str) -> str:
        del item_id
        key = f"{platform}|{listing_id}"
        try:
            return self._mapping[key]
        except KeyError as exc:
            raise PlanningProviderUnavailable(f"retailer identity is not configured for listing {listing_id}") from exc


class ConfiguredCheckoutGroupProvider:
    """Resolve checkout groups from explicit item/retailer assignments."""

    def __init__(self, mapping: Mapping[str, str]) -> None:
        self._mapping = ConfiguredRetailerIdentityProvider._validate(mapping)

    def checkout_group_id(self, *, plan_id: str, item_id: str, retailer_id: str) -> str:
        del plan_id
        key = f"{item_id}|{retailer_id}"
        try:
            return self._mapping[key]
        except KeyError as exc:
            raise PlanningProviderUnavailable(
                f"checkout group is not configured for item {item_id}, retailer {retailer_id}"
            ) from exc


class ConfiguredPlanPolicyProvider:
    """Return explicitly configured policy and feasibility values."""

    def __init__(
        self,
        *,
        inconvenience_penalty_units: int,
        retailer_preference_priority: int,
        feasibility: PlanFeasibility,
        evidence: tuple[str, ...],
    ) -> None:
        if not evidence:
            raise ValueError("configured plan policy requires feasibility evidence")
        self._values = (
            inconvenience_penalty_units,
            retailer_preference_priority,
            feasibility,
            evidence,
        )

    def resolve(self, *, plan_id: str) -> tuple[int, int, PlanFeasibility, tuple[str, ...]]:
        del plan_id
        return self._values


class DeterministicPlanIdProvider:
    """Generate plan IDs from authoritative allocation identity only."""

    def plan_id(self, *, request_id: str, combination_index: int, allocations: tuple) -> str:
        del request_id
        payload = {
            "combination_index": combination_index,
            "allocations": [allocation.model_dump(mode="json") for allocation in allocations],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "plan-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def parse_mapping(value: str) -> dict[str, str]:
    """Parse an operator-supplied JSON string mapping without accepting junk."""
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("planning provider mapping must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("planning provider mapping must be a JSON object")
    return ConfiguredRetailerIdentityProvider._validate(parsed)
