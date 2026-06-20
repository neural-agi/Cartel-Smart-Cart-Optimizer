from __future__ import annotations

from abc import ABC, abstractmethod

from app.product_intelligence.evidence.types import (
    EvidenceBundle,
    EvidenceRegistrationRequest,
    EvidenceRegistrationResponse,
)


class EvidenceRegistry(ABC):
    """Abstract contract for durable evidence registration."""

    @abstractmethod
    async def register(
        self,
        request: EvidenceRegistrationRequest,
    ) -> EvidenceRegistrationResponse:
        """Register source evidence and return a durable evidence bundle."""

    @abstractmethod
    async def assemble(self, request: EvidenceBundle) -> EvidenceBundle:
        """Return an evidence bundle for matching and review consumers."""

