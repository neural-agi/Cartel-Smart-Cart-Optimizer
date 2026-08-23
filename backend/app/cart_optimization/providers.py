"""Injectable application-provider contracts for planning authorities."""

from __future__ import annotations

from typing import Protocol

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
