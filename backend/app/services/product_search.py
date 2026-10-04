from __future__ import annotations

from datetime import datetime
from re import fullmatch
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from app.data_ingestion.observation_registry.interface import ObservationRegistry
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
)
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.models import (
    IdentityStatus,
    ProductLifecycleStatus,
    VariantLifecycleStatus,
)


class ProductSearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    limit: int = 20


class ProductSearchMoney(BaseModel):
    model_config = ConfigDict(frozen=True)

    currency: str
    minor_units: int


class ProductSearchAttribute(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: str
    role: str
    assertion_status: str


class ProductSearchEvidenceReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_type: str
    source_id: str


class ProductSearchItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    canonical_product_id: str
    canonical_variant_id: str
    canonical_display_name: str
    brand: str
    pack: str
    identity_attributes: tuple[ProductSearchAttribute, ...] = Field(default_factory=tuple)
    variant_attributes: tuple[ProductSearchAttribute, ...] = Field(default_factory=tuple)
    evidence_state: str
    observed_at: datetime
    parser_version: str
    normalization_version: str
    platform: str
    retailer_product_id: str | None = None
    retailer_product_url: str | None = None
    platform_listing_id: str
    observation_id: str
    source_reference: str
    raw_artifact_id: str
    raw_content_digest: str
    evidence_references: tuple[ProductSearchEvidenceReference, ...] = Field(default_factory=tuple)
    price: ProductSearchMoney | None = None
    availability_signal: str | None = None


class ProductSearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    items: tuple[ProductSearchItem, ...] = Field(default_factory=tuple)


def has_supported_retailer_evidence(platform: str, observation) -> bool:
    """Return whether an observation has a supported, non-fixture retailer source."""
    allowed_hosts = {"BLINKIT": frozenset({"blinkit.com", "www.blinkit.com"})}.get(
        platform.upper(), frozenset()
    )
    artifact = getattr(observation, "raw_artifact_reference", None)
    if artifact is None:
        return False
    identifiers = dict(observation.platform_identifiers)
    retailer_product_id = identifiers.get("retailer_product_id")
    if not retailer_product_id or retailer_product_id.strip() != retailer_product_id:
        return False
    try:
        parsed = urlsplit(artifact.source_reference)
        port = parsed.port
    except ValueError:
        return False
    provenance_values = (
        observation.parser_version,
        observation.normalization_version,
        artifact.artifact_id,
        artifact.content_digest,
        artifact.storage_reference,
        observation.completeness.basis,
    )
    no_fixture_markers = all(
        not value.casefold().strip().startswith(
            (
                "demo-", "demo_", "demo:", "fixture-", "fixture_", "fixture:",
                "synthetic-", "synthetic_", "synthetic:", "development-seed",
            )
        )
        for value in provenance_values
    )
    provider_source_is_supported = (
        getattr(artifact, "provider_id", None) == "quickcommerce"
        and parsed.hostname is not None
        and parsed.hostname.casefold() == "api.quickcommerceapi.com"
    )
    source_is_supported = no_fixture_markers and (
        observation.platform.value == platform
        and artifact.platform.value == platform
        and parsed.scheme == "https"
        and parsed.hostname is not None
        and (parsed.hostname.casefold() in allowed_hosts or provider_source_is_supported)
        and port in (None, 443)
        and parsed.username is None
        and parsed.password is None
        and parsed.fragment == ""
    )
    if not source_is_supported:
        return False

    product_url = identifiers.get("retailer_product_url")
    if product_url:
        try:
            product_reference = urlsplit(product_url)
            product_path = product_reference.path
            product_port = product_reference.port
        except ValueError:
            return False
        match = fullmatch(r"/prn/[^/]+/prid/([^/?#]+)", product_path)
        if (
            product_reference.scheme != "https"
            or product_reference.hostname not in {"blinkit.com", "www.blinkit.com"}
            or product_port not in (None, 443)
            or product_reference.username is not None
            or product_reference.password is not None
            or product_reference.query
            or product_reference.fragment
            or match is None
            or match.group(1) != retailer_product_id
        ):
            return False
    return True


def latest_governed_observation_ids(associations, observation_registry) -> frozenset[str]:
    """Return only unambiguous latest observations for native retailer listings."""
    grouped: dict[tuple[str, str], list[tuple[object, object]]] = {}
    for association in associations:
        observation = observation_registry.get(association.observation_id)
        if observation is None or not has_supported_retailer_evidence(association.platform, observation):
            continue
        retailer_product_id = dict(observation.platform_identifiers)["retailer_product_id"]
        grouped.setdefault((association.platform, retailer_product_id), []).append(
            (association, observation)
        )

    current: set[str] = set()
    for records in grouped.values():
        identity_mappings = {
            (association.canonical_product_id, association.canonical_variant_id)
            for association, _ in records
        }
        if len(identity_mappings) != 1:
            continue
        newest_timestamp = max(
            observation.raw_artifact_reference.capture_timestamp
            for _, observation in records
        )
        newest = {
            observation.observation_id
            for _, observation in records
            if observation.raw_artifact_reference.capture_timestamp == newest_timestamp
        }
        if len(newest) == 1:
            current.update(newest)
    return frozenset(current)


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
    ) -> None:
        self._catalog = catalog
        self._association_registry = association_registry
        self._observation_registry = observation_registry

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
        current_observations = latest_governed_observation_ids(
            self._association_registry.all(), self._observation_registry
        )
        query_folded = query.casefold()
        items: list[ProductSearchItem] = []
        for association in self._association_registry.all():
            product = products.get(association.canonical_product_id)
            variant = variants.get(association.canonical_variant_id)
            if product is None or variant is None:
                continue
            if variant.canonical_product_id != product.canonical_product_id:
                continue
            if (
                product.product_identity_status is not IdentityStatus.established
                or product.lifecycle_status is not ProductLifecycleStatus.active
                or variant.variant_identity_status is not IdentityStatus.established
                or variant.lifecycle_status is not VariantLifecycleStatus.active
                or variant.pack_configuration.pack_configuration_status != "complete"
            ):
                continue
            searchable = " ".join(
                (
                    product.canonical_display_name,
                    product.brand_reference.display_label,
                    product.product_type,
                    self._pack_label(variant),
                    *(attribute.value for attribute in product.identity_attributes),
                    *(attribute.value for attribute in variant.variant_identity_attributes),
                )
            ).casefold()
            if query_folded not in searchable:
                continue
            observation = self._observation_registry.get(association.observation_id)
            if (
                observation is None
                or association.observation_id not in current_observations
                or not has_supported_retailer_evidence(association.platform, observation)
            ):
                continue
            price = observation.observed_selling_price
            platform_identifiers = dict(observation.platform_identifiers)
            artifact = observation.raw_artifact_reference
            items.append(
                ProductSearchItem(
                    canonical_product_id=product.canonical_product_id,
                    canonical_variant_id=variant.canonical_variant_id,
                    canonical_display_name=product.canonical_display_name,
                    brand=product.brand_reference.display_label,
                    pack=self._pack_label(variant),
                    identity_attributes=tuple(
                        ProductSearchAttribute(
                            name=attribute.name,
                            value=attribute.value,
                            role=attribute.role,
                            assertion_status=attribute.assertion_status,
                        )
                        for attribute in product.identity_attributes
                    ),
                    variant_attributes=tuple(
                        ProductSearchAttribute(
                            name=attribute.name,
                            value=attribute.value,
                            role=attribute.role,
                            assertion_status=attribute.assertion_status,
                        )
                        for attribute in variant.variant_identity_attributes
                    ),
                    evidence_state="registered_governed_observation",
                    observed_at=artifact.capture_timestamp,
                    parser_version=observation.parser_version,
                    normalization_version=observation.normalization_version,
                    platform=association.platform,
                    retailer_product_id=platform_identifiers.get("retailer_product_id"),
                    retailer_product_url=platform_identifiers.get("retailer_product_url"),
                    platform_listing_id=association.platform_listing_id,
                    observation_id=association.observation_id,
                    source_reference=self._safe_source_reference(artifact.source_reference),
                    raw_artifact_id=artifact.artifact_id,
                    raw_content_digest=artifact.content_digest,
                    evidence_references=tuple(
                        ProductSearchEvidenceReference(
                            source_type=reference.source_type,
                            source_id=reference.source_id,
                        )
                        for reference in observation.evidence_references
                    ),
                    price=(
                        ProductSearchMoney(
                            currency=price.currency,
                            minor_units=price.minor_units,
                        )
                        if price is not None
                        else None
                    ),
                    availability_signal=observation.availability_signal,
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

    @staticmethod
    def _safe_source_reference(source_reference: str) -> str:
        parsed = urlsplit(source_reference)
        return parsed._replace(query="", fragment="").geturl()
