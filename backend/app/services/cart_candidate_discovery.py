from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.data_ingestion.observation_registry.interface import ObservationRegistry
from app.data_ingestion.types import NormalizedObservation
from app.normalization.pricing.parser import GovernedRetailPriceParser
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
)
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog


class CartCandidateDiscoveryStatus(StrEnum):
    candidates_available = "candidates_available"
    candidates_not_ready = "candidates_not_ready"
    no_candidates = "no_candidates"


class PersistedCandidateReadiness(StrEnum):
    ready_for_allocation = "ready_for_allocation"
    not_ready_for_allocation = "not_ready_for_allocation"


class CartCandidateDiscoveryItemRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    quantity: int
    canonical_product_id: str
    canonical_variant_id: str


class CartCandidateDiscoveryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[CartCandidateDiscoveryItemRequest, ...] = Field(default_factory=tuple)


class PersistedListingCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    platform: str
    platform_listing_id: str
    canonical_product_id: str
    canonical_variant_id: str
    observation_id: str
    observation: NormalizedObservation
    readiness: PersistedCandidateReadiness
    readiness_reason: str | None = None


class CartCandidateDiscoveryItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    quantity: int
    canonical_product_id: str
    canonical_variant_id: str
    status: CartCandidateDiscoveryStatus
    reason: str | None = None
    candidates: tuple[PersistedListingCandidate, ...] = Field(default_factory=tuple)


class CartCandidateDiscoveryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[CartCandidateDiscoveryItem, ...]


class CartCandidateDiscoveryService:
    """Discover persisted listing candidates without constructing optimizer plans."""

    def __init__(
        self,
        *,
        catalog: FilesystemAuthoritativeCatalog,
        association_registry: FilesystemCanonicalListingAssociationRegistry,
        observation_registry: ObservationRegistry,
        price_parser: GovernedRetailPriceParser | None = None,
    ) -> None:
        self.catalog = catalog
        self.association_registry = association_registry
        self.observation_registry = observation_registry
        self.price_parser = price_parser or GovernedRetailPriceParser()

    def discover(
        self, request: CartCandidateDiscoveryRequest
    ) -> CartCandidateDiscoveryResult:
        associations = self.association_registry.all()
        return CartCandidateDiscoveryResult(
            items=tuple(
                self._discover_item(item, associations) for item in request.items
            )
        )

    def _discover_item(self, item, associations) -> CartCandidateDiscoveryItem:
        candidates: list[PersistedListingCandidate] = []
        for association in associations:
            if (
                association.canonical_product_id != item.canonical_product_id
                or association.canonical_variant_id != item.canonical_variant_id
            ):
                continue
            if self.catalog.get_product(association.canonical_product_id) is None:
                continue
            if self.catalog.get_variant(association.canonical_variant_id) is None:
                continue
            observation = self.observation_registry.get(association.observation_id)
            if observation is None:
                continue
            readiness, readiness_reason = self._readiness(observation)
            candidates.append(
                PersistedListingCandidate(
                    platform=association.platform,
                    platform_listing_id=association.platform_listing_id,
                    canonical_product_id=association.canonical_product_id,
                    canonical_variant_id=association.canonical_variant_id,
                    observation_id=association.observation_id,
                    observation=observation,
                    readiness=readiness,
                    readiness_reason=readiness_reason,
                )
            )

        candidates.sort(
            key=lambda candidate: (
                candidate.platform,
                candidate.platform_listing_id,
                candidate.observation_id,
            )
        )
        if not candidates:
            status = CartCandidateDiscoveryStatus.no_candidates
            reason = "no persisted listing candidates available"
        elif any(
            candidate.readiness is PersistedCandidateReadiness.ready_for_allocation
            for candidate in candidates
        ):
            status = CartCandidateDiscoveryStatus.candidates_available
            reason = None
        else:
            status = CartCandidateDiscoveryStatus.candidates_not_ready
            reason = "persisted listing candidates are not ready for allocation"
        return CartCandidateDiscoveryItem(
            item_id=item.item_id,
            quantity=item.quantity,
            canonical_product_id=item.canonical_product_id,
            canonical_variant_id=item.canonical_variant_id,
            status=status,
            reason=reason,
            candidates=tuple(candidates),
        )

    def _readiness(
        self, observation: NormalizedObservation
    ) -> tuple[PersistedCandidateReadiness, str | None]:
        price = observation.observed_selling_price
        if price is None:
            return (
                PersistedCandidateReadiness.not_ready_for_allocation,
                "observation has no typed observed selling price",
            )
        if price.currency not in self.price_parser.currency_precision:
            return (
                PersistedCandidateReadiness.not_ready_for_allocation,
                "observed selling price uses an unsupported currency",
            )
        return PersistedCandidateReadiness.ready_for_allocation, None
