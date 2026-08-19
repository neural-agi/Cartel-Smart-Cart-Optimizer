from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.data_ingestion.observation_registry.interface import ObservationRegistry
from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
)
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog


class CartItemResolutionStatus(StrEnum):
    resolved = "resolved"
    unresolved = "unresolved"


class CartItemResolutionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    quantity: int
    canonical_variant_id: str | None = None
    platform: str | None = None
    platform_listing_id: str | None = None

    @model_validator(mode="after")
    def _validate_listing_identity(self) -> "CartItemResolutionRequest":
        if (self.platform is None) != (self.platform_listing_id is None):
            raise ValueError("platform and platform_listing_id must be provided together")
        if self.canonical_variant_id is None and self.platform is None:
            raise ValueError(
                "canonical_variant_id or platform and platform_listing_id are required"
            )
        return self


class CartResolutionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[CartItemResolutionRequest, ...] = Field(default_factory=tuple)


class CartItemResolution(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    quantity: int
    status: CartItemResolutionStatus
    reason: str | None = None
    canonical_product_id: str | None = None
    canonical_variant_id: str | None = None
    platform: str | None = None
    platform_listing_id: str | None = None
    observation_id: str | None = None
    observation: NormalizedObservation | None = None


class CartResolutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[CartItemResolution, ...]


class CartResolutionService:
    """Resolve frontend cart identities against persisted backend-owned data."""

    def __init__(
        self,
        *,
        catalog: FilesystemAuthoritativeCatalog,
        association_registry: FilesystemCanonicalListingAssociationRegistry,
        observation_registry: ObservationRegistry,
    ) -> None:
        self.catalog = catalog
        self.association_registry = association_registry
        self.observation_registry = observation_registry

    def resolve(self, request: CartResolutionRequest) -> CartResolutionResult:
        return CartResolutionResult(
            items=tuple(self._resolve_item(item) for item in request.items)
        )

    def _resolve_item(self, item: CartItemResolutionRequest) -> CartItemResolution:
        if item.canonical_variant_id is not None:
            variant = self.catalog.get_variant(item.canonical_variant_id)
            if variant is None:
                return self._unresolved(item, "canonical Variant was not found")
            product = self.catalog.get_product(variant.canonical_product_id)
            if product is None:
                return self._unresolved(item, "canonical Product was not found")
            association = self._association(item)
            if association is None:
                return CartItemResolution(
                    item_id=item.item_id,
                    quantity=item.quantity,
                    status=CartItemResolutionStatus.resolved,
                    canonical_product_id=product.canonical_product_id,
                    canonical_variant_id=variant.canonical_variant_id,
                )
            if association.canonical_variant_id != variant.canonical_variant_id:
                return self._unresolved(
                    item,
                    "canonical Variant identity conflicts with listing association",
                )
        else:
            association = self._association(item)
            if association is None:
                return self._unresolved(item, "listing association was not found")
            product = self.catalog.get_product(association.canonical_product_id)
            variant = self.catalog.get_variant(association.canonical_variant_id)
            if product is None:
                return self._unresolved(item, "associated canonical Product was not found")
            if variant is None:
                return self._unresolved(item, "associated canonical Variant was not found")

        observation = self.observation_registry.get(association.observation_id) if association else None
        if association is not None and observation is None:
            return self._unresolved(item, "listing association references a missing observation")
        return CartItemResolution(
            item_id=item.item_id,
            quantity=item.quantity,
            status=CartItemResolutionStatus.resolved,
            canonical_product_id=product.canonical_product_id,
            canonical_variant_id=variant.canonical_variant_id,
            platform=association.platform if association else item.platform,
            platform_listing_id=(
                association.platform_listing_id if association else item.platform_listing_id
            ),
            observation_id=association.observation_id if association else None,
            observation=observation,
        )

    def _association(self, item: CartItemResolutionRequest):
        if item.platform is None or item.platform_listing_id is None:
            return None
        return self.association_registry.get(item.platform, item.platform_listing_id)

    @staticmethod
    def _unresolved(item: CartItemResolutionRequest, reason: str) -> CartItemResolution:
        return CartItemResolution(
            item_id=item.item_id,
            quantity=item.quantity,
            status=CartItemResolutionStatus.unresolved,
            reason=reason,
        )
