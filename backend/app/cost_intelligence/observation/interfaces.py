from __future__ import annotations

from abc import ABC, abstractmethod

from app.cost_intelligence.observation.types import (
    CheckoutObservation,
    CheckoutObservationRegistrationRequest,
    CheckoutObservationRegistrationResponse,
)


class CheckoutObservationRegistry(ABC):
    """Abstract contract for deterministic checkout observation storage."""

    @abstractmethod
    async def register(
        self,
        request: CheckoutObservationRegistrationRequest,
    ) -> CheckoutObservationRegistrationResponse:
        """Register a canonical checkout observation."""

    @abstractmethod
    def get_checkout_observation(self, observation_id: str) -> CheckoutObservation | None:
        """Return a previously registered checkout observation."""

    @abstractmethod
    def list_checkout_observations(self) -> list[CheckoutObservation]:
        """Return registered checkout observations in deterministic order."""
