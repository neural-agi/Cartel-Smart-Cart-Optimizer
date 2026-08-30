from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.cost_intelligence.shared.money import Money
from app.data_ingestion.enums import TaxStatus
from app.data_ingestion.observation_registry.query import RetailObservationQueryService


class RetailPriceComparisonStatus(StrEnum):
    COMPLETED = "completed"
    NO_COMPARABLE_OBSERVATIONS = "no_comparable_observations"
    CURRENCY_MISMATCH = "currency_mismatch"


class ComparableRetailObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_id: str
    platform: str
    platform_listing_id: str
    retailer_product_id: str | None = None
    canonical_product_id: str
    canonical_variant_id: str
    observed_selling_price: Money
    tax_status: TaxStatus


class RetailPriceComparisonResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    canonical_variant_id: str
    status: RetailPriceComparisonStatus
    observations: tuple[ComparableRetailObservation, ...] = ()
    rationale: tuple[str, ...] = Field(default_factory=tuple)


class RetailPriceComparisonQueryService:
    """Build a deterministic displayed-price projection for one Variant."""

    def __init__(
        self,
        observation_queries: RetailObservationQueryService,
        *,
        supported_currencies: frozenset[str] = frozenset({"INR"}),
    ) -> None:
        self.observation_queries = observation_queries
        self.supported_currencies = frozenset(
            currency.strip().upper() for currency in supported_currencies
        )

    def compare(self, canonical_variant_id: str) -> RetailPriceComparisonResult:
        records = self.observation_queries.list_observations(
            canonical_variant_id=canonical_variant_id
        )
        comparable: list[ComparableRetailObservation] = []
        currencies: set[str] = set()
        for record in records:
            association = record.association
            price = record.observation.observed_selling_price
            if association is None or price is None:
                continue
            if price.currency not in self.supported_currencies:
                continue
            if record.observation.tax_status is TaxStatus.UNKNOWN:
                continue
            currencies.add(price.currency)
            comparable.append(
                ComparableRetailObservation(
                    observation_id=record.observation_id,
                    platform=association.platform,
                    platform_listing_id=association.platform_listing_id,
                    retailer_product_id=dict(record.observation.platform_identifiers).get("retailer_product_id"),
                    canonical_product_id=association.canonical_product_id,
                    canonical_variant_id=association.canonical_variant_id,
                    observed_selling_price=price,
                    tax_status=record.observation.tax_status,
                )
            )

        if len(currencies) > 1:
            return RetailPriceComparisonResult(
                canonical_variant_id=canonical_variant_id,
                status=RetailPriceComparisonStatus.CURRENCY_MISMATCH,
                rationale=("eligible observations use different currencies",),
            )

        comparable.sort(
            key=lambda item: (
                item.observed_selling_price.minor_units,
                item.platform,
                item.platform_listing_id,
                item.observation_id,
            )
        )
        return RetailPriceComparisonResult(
            canonical_variant_id=canonical_variant_id,
            status=(
                RetailPriceComparisonStatus.COMPLETED
                if comparable
                else RetailPriceComparisonStatus.NO_COMPARABLE_OBSERVATIONS
            ),
            observations=tuple(comparable),
            rationale=(
                "displayed-price comparison only"
                if comparable
                else "no eligible observations with resolved association, typed price, supported currency, and known tax status",
            ),
        )
