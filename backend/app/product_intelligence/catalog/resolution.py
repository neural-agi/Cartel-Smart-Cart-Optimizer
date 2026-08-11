from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable
from enum import StrEnum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.catalog.types import CatalogState
from app.product_intelligence.models import (
    IdentityStatus,
    Product,
    ProductLifecycleStatus,
    ProductVariant,
    VariantLifecycleStatus,
)


IdentityKey: TypeAlias = Hashable
ProductObservationKey: TypeAlias = Callable[[NormalizedObservation], IdentityKey]
ProductCatalogKey: TypeAlias = Callable[[Product], IdentityKey]
VariantObservationKey: TypeAlias = Callable[[NormalizedObservation, Product], IdentityKey]
VariantCatalogKey: TypeAlias = Callable[[ProductVariant], IdentityKey]


class ListingResolutionStatus(StrEnum):
    mapped = "mapped"
    unresolved = "unresolved"
    ambiguous = "ambiguous"
    conflicting = "conflicting"


class CanonicalListingAssociation(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_id: str
    platform: str
    platform_listing_id: str
    canonical_product_id: str
    canonical_variant_id: str


class ListingResolutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: ListingResolutionStatus
    association: CanonicalListingAssociation | None = None
    rationale: tuple[str, ...] = Field(default_factory=tuple)


class DeterministicCanonicalListingResolver:
    """Resolve normalized observations against immutable catalog state.

    Identity policies are injected explicitly. No heuristic or platform-derived
    identity policy is supplied by this boundary.
    """

    def __init__(
        self,
        *,
        product_observation_key: ProductObservationKey,
        product_catalog_key: ProductCatalogKey,
        variant_observation_key: VariantObservationKey,
        variant_catalog_key: VariantCatalogKey,
    ) -> None:
        self._product_observation_key = product_observation_key
        self._product_catalog_key = product_catalog_key
        self._variant_observation_key = variant_observation_key
        self._variant_catalog_key = variant_catalog_key

    def resolve(
        self,
        observation: NormalizedObservation,
        state: CatalogState,
    ) -> ListingResolutionResult:
        try:
            eligible_products = self._unique_products(
                product for product in state.products if self._product_eligible(product)
            )
            eligible_variants = self._unique_variants(
                variant for variant in state.variants if self._variant_eligible(variant)
            )
        except ValueError as exc:
            return self._result(ListingResolutionStatus.conflicting, str(exc))
        try:
            product_key = self._product_observation_key(observation)
        except (KeyError, TypeError, ValueError) as exc:
            return self._result(ListingResolutionStatus.unresolved, f"product identity evidence unavailable: {exc}")

        products = [product for product in eligible_products if self._same_product_key(product, product_key)]
        if not products:
            return self._result(ListingResolutionStatus.unresolved, "no eligible Product matches the governed identity key")
        if len(products) > 1:
            return self._result(ListingResolutionStatus.ambiguous, "multiple eligible Products match the governed identity key")

        product = products[0]
        try:
            variant_key = self._variant_observation_key(observation, product)
        except (KeyError, TypeError, ValueError) as exc:
            return self._result(ListingResolutionStatus.unresolved, f"variant identity evidence unavailable: {exc}")

        variants = [variant for variant in eligible_variants if self._same_variant_key(variant, variant_key)]
        if not variants:
            return self._result(ListingResolutionStatus.unresolved, "no eligible ProductVariant matches the governed identity key")
        if any(variant.canonical_product_id != product.canonical_product_id for variant in variants):
            return self._result(ListingResolutionStatus.conflicting, "matched Variant belongs to another Product")
        if len(variants) > 1:
            return self._result(ListingResolutionStatus.ambiguous, "multiple eligible ProductVariants match the governed identity key")

        variant = variants[0]
        if variant.canonical_product_id != product.canonical_product_id:
            return self._result(ListingResolutionStatus.conflicting, "matched Variant belongs to another Product")
        return ListingResolutionResult(
            status=ListingResolutionStatus.mapped,
            association=CanonicalListingAssociation(
                observation_id=observation.observation_id,
                platform=observation.platform.value,
                platform_listing_id=observation.source_record_id,
                canonical_product_id=product.canonical_product_id,
                canonical_variant_id=variant.canonical_variant_id,
            ),
            rationale=("exact governed Product and Variant keys matched",),
        )

    def _same_product_key(self, product: Product, key: IdentityKey) -> bool:
        try:
            return self._product_catalog_key(product) == key
        except (KeyError, TypeError, ValueError):
            return False

    def _same_variant_key(self, variant: ProductVariant, key: IdentityKey) -> bool:
        try:
            return self._variant_catalog_key(variant) == key
        except (KeyError, TypeError, ValueError):
            return False

    @staticmethod
    def _product_eligible(product: Product) -> bool:
        return (
            bool(product.canonical_product_id.strip())
            and product.product_identity_status is IdentityStatus.established
            and product.lifecycle_status is ProductLifecycleStatus.active
            and product.canonical_category_reference.review_state == "approved"
        )

    @staticmethod
    def _variant_eligible(variant: ProductVariant) -> bool:
        return (
            bool(variant.canonical_variant_id.strip())
            and bool(variant.canonical_product_id.strip())
            and variant.variant_identity_status is IdentityStatus.established
            and variant.lifecycle_status is VariantLifecycleStatus.active
            and variant.pack_configuration.pack_configuration_status == "complete"
        )

    @staticmethod
    def _result(status: ListingResolutionStatus, rationale: str) -> ListingResolutionResult:
        return ListingResolutionResult(status=status, rationale=(rationale,))

    @staticmethod
    def _unique_products(products: Iterable[Product]) -> list[Product]:
        unique: dict[str, Product] = {}
        for product in products:
            existing = unique.get(product.canonical_product_id)
            if existing is not None and existing.model_dump(mode="json") != product.model_dump(mode="json"):
                raise ValueError(
                    f"conflicting Product state for canonical_product_id={product.canonical_product_id}"
                )
            unique[product.canonical_product_id] = product
        return list(unique.values())

    @staticmethod
    def _unique_variants(variants: Iterable[ProductVariant]) -> list[ProductVariant]:
        unique: dict[str, ProductVariant] = {}
        for variant in variants:
            existing = unique.get(variant.canonical_variant_id)
            if existing is not None and existing.model_dump(mode="json") != variant.model_dump(mode="json"):
                raise ValueError(
                    f"conflicting ProductVariant state for canonical_variant_id={variant.canonical_variant_id}"
                )
            unique[variant.canonical_variant_id] = variant
        return list(unique.values())
