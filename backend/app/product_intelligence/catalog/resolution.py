from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Mapping
from enum import StrEnum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.catalog.types import CatalogState
from app.product_intelligence.catalog.identity_contract import (
    CanonicalIdentityResolution,
    IdentityComparison,
    IdentityResolutionState,
    RetailerProductIdentityEvidence,
    canonical_identity_profile,
    compare_identity_profiles,
)
from app.product_intelligence.catalog.retailer_identity import RetailerIdentityAdapter
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
        retailer_identity_adapters: Mapping[str, RetailerIdentityAdapter] | None = None,
    ) -> None:
        self._product_observation_key = product_observation_key
        self._product_catalog_key = product_catalog_key
        self._variant_observation_key = variant_observation_key
        self._variant_catalog_key = variant_catalog_key
        self._retailer_identity_adapters = {
            key.upper(): value for key, value in (retailer_identity_adapters or {}).items()
        }

    def resolve(
        self,
        observation: NormalizedObservation,
        state: CatalogState,
    ) -> ListingResolutionResult:
        identity_adapter = self._retailer_identity_adapters.get(observation.platform.value.upper())
        if identity_adapter is not None:
            evidence = identity_adapter.adapt(observation)
            identity_result = self.resolve_identity(evidence, state)
            if identity_result.state == IdentityResolutionState.EXACT_MATCH:
                assert identity_result.canonical_product_id is not None
                assert identity_result.canonical_variant_id is not None
                return ListingResolutionResult(
                    status=ListingResolutionStatus.mapped,
                    association=CanonicalListingAssociation(
                        observation_id=observation.observation_id,
                        platform=observation.platform.value,
                        platform_listing_id=observation.source_record_id,
                        canonical_product_id=identity_result.canonical_product_id,
                        canonical_variant_id=identity_result.canonical_variant_id,
                    ),
                    rationale=(identity_result.reason,),
                )
            status = (
                ListingResolutionStatus.conflicting
                if identity_result.state == IdentityResolutionState.MISMATCH
                else ListingResolutionStatus.unresolved
            )
            return ListingResolutionResult(status=status, rationale=(identity_result.reason,))

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

    def compare_identity(
        self,
        evidence: RetailerProductIdentityEvidence,
        product: Product,
        variant: ProductVariant,
    ) -> IdentityComparison:
        """Compare one retailer listing to one proposed canonical variant."""
        if evidence.evidence_issues:
            return IdentityComparison(
                state=IdentityResolutionState.UNRESOLVED,
                reason="retailer provenance/identity is incomplete: " + ", ".join(evidence.evidence_issues),
            )
        if not self._identity_evidence_is_well_formed(evidence):
            return IdentityComparison(
                state=IdentityResolutionState.UNRESOLVED,
                reason="authoritative retailer identity or observation provenance is missing or inconsistent",
            )
        if variant.canonical_product_id != product.canonical_product_id:
            return IdentityComparison(
                state=IdentityResolutionState.MISMATCH,
                reason="variant belongs to a different canonical Product",
            )
        if not self._product_eligible(product) or not self._variant_eligible(variant):
            return IdentityComparison(
                state=IdentityResolutionState.UNRESOLVED,
                reason="canonical Product or Variant is not established and active",
            )
        canonical_profile = canonical_identity_profile(product, variant)
        return compare_identity_profiles(canonical_profile, evidence.identity)

    def resolve_identity(
        self,
        evidence: RetailerProductIdentityEvidence,
        state: CatalogState,
    ) -> CanonicalIdentityResolution:
        """Resolve to one unique exact canonical Product/Variant or remain unresolved."""
        if evidence.evidence_issues:
            return CanonicalIdentityResolution(
                state=IdentityResolutionState.UNRESOLVED,
                reason="retailer provenance/identity is incomplete: " + ", ".join(evidence.evidence_issues),
            )
        if not self._identity_evidence_is_well_formed(evidence):
            return CanonicalIdentityResolution(
                state=IdentityResolutionState.UNRESOLVED,
                reason="authoritative retailer listing identity or observation provenance is missing",
            )

        try:
            products = self._unique_products(
                product for product in state.products if self._product_eligible(product)
            )
            variants = self._unique_variants(
                variant for variant in state.variants if self._variant_eligible(variant)
            )
        except ValueError as exc:
            return CanonicalIdentityResolution(
                state=IdentityResolutionState.UNRESOLVED,
                reason=f"canonical catalog identity state is conflicting: {exc}",
            )

        exact: list[tuple[Product, ProductVariant]] = []
        unresolved_candidates = 0
        for product in products:
            for variant in variants:
                if variant.canonical_product_id != product.canonical_product_id:
                    continue
                comparison = self.compare_identity(evidence, product, variant)
                if comparison.state == IdentityResolutionState.EXACT_MATCH:
                    exact.append((product, variant))
                elif comparison.state == IdentityResolutionState.UNRESOLVED:
                    unresolved_candidates += 1
        if len(exact) != 1 or unresolved_candidates:
            reason = (
                "multiple canonical Product/Variant pairs satisfy the identity facts"
                if len(exact) > 1
                else "an eligible canonical Product/Variant candidate has insufficient identity evidence"
                if exact and unresolved_candidates
                else "no unique exact canonical Product/Variant match; evidence remains unresolved"
            )
            return CanonicalIdentityResolution(state=IdentityResolutionState.UNRESOLVED, reason=reason)
        product, variant = exact[0]
        return CanonicalIdentityResolution(
            state=IdentityResolutionState.EXACT_MATCH,
            canonical_product_id=product.canonical_product_id,
            canonical_variant_id=variant.canonical_variant_id,
            reason="unique exact canonical Product and Variant identity match",
        )

    @staticmethod
    def _identity_evidence_is_well_formed(evidence: RetailerProductIdentityEvidence) -> bool:
        observation = evidence.observation
        retailer_id = evidence.retailer_product_id
        artifact = observation.raw_artifact_reference
        return bool(
            retailer_id
            and retailer_id.strip() == retailer_id
            and observation.source_record_id.strip()
            and artifact is not None
            and artifact.platform is observation.platform
            and observation.evidence_references
            and observation.parser_version.strip()
            and observation.normalization_version.strip()
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
