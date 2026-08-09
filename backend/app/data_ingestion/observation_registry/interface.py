from __future__ import annotations

from abc import ABC, abstractmethod

from app.data_ingestion.types import NormalizedObservation


class ObservationRegistry(ABC):
    """Process-local registry for immutable normalized observations."""

    @abstractmethod
    def register(self, observation: NormalizedObservation) -> NormalizedObservation:
        """Register or replay an observation idempotently."""

    @abstractmethod
    def get(self, observation_id: str) -> NormalizedObservation | None:
        """Return an immutable copy of a registered observation."""

    @abstractmethod
    def exists(self, observation_id: str) -> bool:
        """Return whether an observation is registered."""
