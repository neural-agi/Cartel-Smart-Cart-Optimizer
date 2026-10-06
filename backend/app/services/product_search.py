from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.data_ingestion.observation_registry.interface import ObservationRegistry
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
)
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.retailer_data.persistence import FilesystemRetailerObservationStore


class ProductSearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    limit: int = 20
    max_age_seconds: int | None = None

    @field_validator("max_age_seconds")
    @classmethod
    def _validate_max_age(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("max_age_seconds must not be negative")
        return value


class ProductSearchMoney(BaseModel):
    model_config = ConfigDict(frozen=True)

    currency: str
    minor_units: int


class ProductSearchItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    canonical_product_id: str
    canonical_variant_id: str
    canonical_display_name: str
    brand: str
    pack: str
    platform: str
    platform_listing_id: str
    observation_id: str
    price: ProductSearchMoney | None = None
    availability_signal: str | None = None


class ProductSearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    items: tuple[ProductSearchItem, ...] = Field(default_factory=tuple)


class ProductSearchService:
    """Search only governed catalog/listing/observation state.

    This service performs retrieval, not product identity inference. A result
    exists only when an active canonical variant has a persisted listing
    association and a registered normalized observation.
    """

    def __init__(
        self,
        *,
        catalog: FilesystemAuthoritativeCatalog,
        association_registry: FilesystemCanonicalListingAssociationRegistry,
        observation_registry: ObservationRegistry,
        retailer_observation_store: FilesystemRetailerObservationStore | None = None,
    ) -> None:
        self._catalog = catalog
        self._association_registry = association_registry
        self._observation_registry = observation_registry
        self._retailer_observation_store = retailer_observation_store

    def search(self, request: ProductSearchRequest) -> ProductSearchResult:
        query = request.query.strip()
        if not query:
            raise ValueError("product search query must not be blank")
        if request.limit < 1 or request.limit > 100:
            raise ValueError("product search limit must be between 1 and 100")

        state = self._catalog.load_state()
        products = {product.canonical_product_id: product for product in state.products}
        variants = {
            variant.canonical_variant_id: variant for variant in state.variants
        }
        query_folded = query.casefold()
        items: list[ProductSearchItem] = []
        for association in self._association_registry.all():
            if getattr(association, "association_status", "associated") != "associated":
                continue
            product = products.get(association.canonical_product_id)
            variant = variants.get(association.canonical_variant_id)
            if product is None or variant is None:
                continue
            if variant.canonical_product_id != product.canonical_product_id:
                continue
            searchable = " ".join(
                (
                    product.canonical_display_name,
                    product.brand_reference.display_label,
                    product.product_type,
                )
            ).casefold()
            if query_folded not in searchable:
                continue
            observation = self._observation_registry.get(association.observation_id)
            retailer_observation = None
            if observation is None and self._retailer_observation_store is not None:
                retailer_observation = self._retailer_observation_store.get(association.observation_id)
                if retailer_observation is not None and request.max_age_seconds is not None:
                    from datetime import timedelta

                    if retailer_observation.freshness_at(max_age=timedelta(seconds=request.max_age_seconds)).value != "current":
                        continue
            if observation is None:
                if retailer_observation is None:
                    continue
                price = retailer_observation.effective_price or retailer_observation.listed_price
                availability_signal = retailer_observation.availability
            else:
                price = observation.observed_selling_price
                availability_signal = observation.availability_signal
            items.append(
                ProductSearchItem(
                    canonical_product_id=product.canonical_product_id,
                    canonical_variant_id=variant.canonical_variant_id,
                    canonical_display_name=product.canonical_display_name,
                    brand=product.brand_reference.display_label,
                    pack=self._pack_label(variant),
                    platform=association.platform,
                    platform_listing_id=association.platform_listing_id,
                    observation_id=association.observation_id,
                    price=(
                        ProductSearchMoney(
                            currency=price.currency,
                            minor_units=price.minor_units,
                        )
                        if price is not None
                        else None
                    ),
                    availability_signal=availability_signal,
                )
            )

        items.sort(
            key=lambda item: (
                item.canonical_display_name.casefold(),
                item.canonical_variant_id,
                item.platform,
                item.platform_listing_id,
                item.observation_id,
            )
        )
        return ProductSearchResult(query=query, items=tuple(items[: request.limit]))

    @staticmethod
    def _pack_label(variant) -> str:
        pack = variant.pack_configuration
        if pack.total_declared_content is not None:
            content = pack.total_declared_content
            return f"{content.value} {content.unit}"
        if pack.consumer_unit_count is not None:
            return f"{pack.consumer_unit_count} units"
        return "Pack information unavailable"
