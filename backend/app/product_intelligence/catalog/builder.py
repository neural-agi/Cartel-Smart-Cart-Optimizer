from __future__ import annotations

from app.product_intelligence.candidate_generation.service import CandidateCatalogSnapshot
from app.product_intelligence.catalog.types import CatalogConflictError, CatalogState
from app.product_intelligence.models import Product, ProductVariant
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog


class DeterministicCandidateCatalogSnapshotBuilder:
    """Build a deterministic candidate snapshot from authoritative catalog state."""

    def build(self, state: CatalogState) -> CandidateCatalogSnapshot:
        products = self._eligible_products(state.products)
        product_ids = {product.canonical_product_id for product in products}
        variants = self._eligible_variants(state.variants, product_ids)
        return CandidateCatalogSnapshot(
            products=tuple(sorted(products, key=lambda item: item.canonical_product_id)),
            variants=tuple(sorted(variants, key=lambda item: item.canonical_variant_id)),
        )

    def build_from_catalog(
        self,
        catalog: FilesystemAuthoritativeCatalog,
    ) -> CandidateCatalogSnapshot:
        return self.build(catalog.load_state())

    def _eligible_products(self, products: tuple[Product, ...]) -> list[Product]:
        eligible: list[Product] = []
        seen: dict[str, Product] = {}
        for product in products:
            existing = seen.get(product.canonical_product_id)
            if existing is not None:
                if existing.model_dump(mode="json") != product.model_dump(mode="json"):
                    raise CatalogConflictError(
                        f"conflicting Product state for canonical_product_id={product.canonical_product_id}"
                    )
                continue
            seen[product.canonical_product_id] = product
            if self._is_product_eligible(product):
                eligible.append(product)
        return eligible

    def _eligible_variants(
        self,
        variants: tuple[ProductVariant, ...],
        product_ids: set[str],
    ) -> list[ProductVariant]:
        eligible: list[ProductVariant] = []
        seen: dict[str, ProductVariant] = {}
        for variant in variants:
            existing = seen.get(variant.canonical_variant_id)
            if existing is not None:
                if existing.model_dump(mode="json") != variant.model_dump(mode="json"):
                    raise CatalogConflictError(
                        f"conflicting ProductVariant state for canonical_variant_id={variant.canonical_variant_id}"
                    )
                continue
            seen[variant.canonical_variant_id] = variant
            if variant.canonical_product_id not in product_ids:
                raise CatalogConflictError(
                    f"orphan ProductVariant canonical_variant_id={variant.canonical_variant_id}"
                )
            if self._is_variant_eligible(variant):
                eligible.append(variant)
        return eligible

    @staticmethod
    def _is_product_eligible(product: Product) -> bool:
        return (
            bool(product.canonical_product_id.strip())
            and product.product_identity_status.value == "established"
            and product.lifecycle_status.value == "active"
            and product.canonical_category_reference.review_state == "approved"
        )

    @staticmethod
    def _is_variant_eligible(variant: ProductVariant) -> bool:
        return (
            bool(variant.canonical_variant_id.strip())
            and bool(variant.canonical_product_id.strip())
            and variant.variant_identity_status.value == "established"
            and variant.lifecycle_status.value == "active"
            and variant.pack_configuration.pack_configuration_status == "complete"
        )
