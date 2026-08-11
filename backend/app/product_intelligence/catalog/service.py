from __future__ import annotations

from app.core.logging import get_logger
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.product_intelligence.catalog.types import (
    AuthoritativeCatalogRecord,
    CatalogConflictError,
    CatalogState,
    CatalogValidationError,
)
from app.product_intelligence.models import (
    CategoryReference,
    IdentityStatus,
    Product,
    ProductLifecycleStatus,
    ProductVariant,
    VariantLifecycleStatus,
)


logger = get_logger(__name__)


class FilesystemAuthoritativeCatalog:
    """Minimal authoritative catalog for manually curated canonical entities."""

    def __init__(self, store: CatalogFilesystemStore | None = None) -> None:
        self.store = store or CatalogFilesystemStore()

    def register_product(self, product: Product) -> Product:
        self._validate_product(product)
        record = self.store.load()
        updated = list(record.products)
        existing = self._product_by_id(updated, product.canonical_product_id)
        if existing is not None:
            if existing.model_dump(mode="json") != product.model_dump(mode="json"):
                raise CatalogConflictError(
                    f"conflicting Product state for canonical_product_id={product.canonical_product_id}"
                )
            return existing
        updated.append(product.model_copy(deep=True))
        self.store.save(
            AuthoritativeCatalogRecord(
                schema_version=record.schema_version,
                products=updated,
                variants=record.variants,
            )
        )
        logger.info(
            "canonical_product_registered canonical_product_id=%s",
            product.canonical_product_id,
        )
        return product

    def register_variant(self, variant: ProductVariant) -> ProductVariant:
        self._validate_variant(variant)
        record = self.store.load()
        if self._product_by_id(record.products, variant.canonical_product_id) is None:
            raise CatalogValidationError(
                f"parent Product not found for canonical_product_id={variant.canonical_product_id}"
            )
        updated = list(record.variants)
        existing = self._variant_by_id(updated, variant.canonical_variant_id)
        if existing is not None:
            if existing.model_dump(mode="json") != variant.model_dump(mode="json"):
                raise CatalogConflictError(
                    f"conflicting ProductVariant state for canonical_variant_id={variant.canonical_variant_id}"
                )
            return existing
        updated.append(variant.model_copy(deep=True))
        self.store.save(
            AuthoritativeCatalogRecord(
                schema_version=record.schema_version,
                products=record.products,
                variants=updated,
            )
        )
        logger.info(
            "canonical_variant_registered canonical_variant_id=%s canonical_product_id=%s",
            variant.canonical_variant_id,
            variant.canonical_product_id,
        )
        return variant

    def get_product(self, canonical_product_id: str) -> Product | None:
        return self._product_by_id(self.store.load().products, canonical_product_id)

    def get_variant(self, canonical_variant_id: str) -> ProductVariant | None:
        return self._variant_by_id(self.store.load().variants, canonical_variant_id)

    def load_state(self) -> CatalogState:
        record = self.store.load()
        return CatalogState(
            products=tuple(record.products),
            variants=tuple(record.variants),
        )

    def _validate_product(self, product: Product) -> None:
        if not product.canonical_product_id.strip():
            raise CatalogValidationError("canonical_product_id is required")
        if product.product_identity_status is not IdentityStatus.established:
            raise CatalogValidationError("product must be canonically identified")
        if product.lifecycle_status is not ProductLifecycleStatus.active:
            raise CatalogValidationError("product must be active")
        if product.brand_reference.is_unknown:
            raise CatalogValidationError("product brand must be known")
        if not product.brand_reference.display_label.strip():
            raise CatalogValidationError("product brand display_label is required")
        if not product.product_type.strip():
            raise CatalogValidationError("product_type is required")
        if not product.canonical_display_name.strip():
            raise CatalogValidationError("canonical_display_name is required")
        self._validate_category(product.canonical_category_reference)
        if not product.catalog_revision.strip():
            raise CatalogValidationError("catalog_revision is required")
        if not product.identity_attributes and not product.descriptive_attributes:
            raise CatalogValidationError("product must carry canonical attributes")

    def _validate_variant(self, variant: ProductVariant) -> None:
        if not variant.canonical_variant_id.strip():
            raise CatalogValidationError("canonical_variant_id is required")
        if not variant.canonical_product_id.strip():
            raise CatalogValidationError("canonical_product_id is required")
        if variant.variant_identity_status is not IdentityStatus.established:
            raise CatalogValidationError("variant must be canonically identified")
        if variant.lifecycle_status is not VariantLifecycleStatus.active:
            raise CatalogValidationError("variant must be active")
        if not variant.catalog_revision.strip():
            raise CatalogValidationError("catalog_revision is required")
        if variant.pack_configuration.pack_configuration_status != "complete":
            raise CatalogValidationError("variant pack configuration must be complete")
        if variant.pack_configuration.pack_kind.value == "unknown":
            raise CatalogValidationError("variant pack kind is required")
        if variant.pack_configuration.consumer_unit_count is None:
            raise CatalogValidationError("variant consumer_unit_count is required")
        if variant.pack_configuration.content_per_consumer_unit is None:
            raise CatalogValidationError("variant content_per_consumer_unit is required")
        if variant.pack_configuration.total_declared_content is None:
            raise CatalogValidationError("variant total_declared_content is required")

    @staticmethod
    def _validate_category(category: CategoryReference) -> None:
        if not category.category_id.strip():
            raise CatalogValidationError("category_id is required")
        if category.review_state != "approved":
            raise CatalogValidationError("category must be approved")

    @staticmethod
    def _product_by_id(products: list[Product], canonical_product_id: str) -> Product | None:
        for product in products:
            if product.canonical_product_id == canonical_product_id:
                return product
        return None

    @staticmethod
    def _variant_by_id(
        variants: list[ProductVariant],
        canonical_variant_id: str,
    ) -> ProductVariant | None:
        for variant in variants:
            if variant.canonical_variant_id == canonical_variant_id:
                return variant
        return None
