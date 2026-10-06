from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Protocol

from app.cost_intelligence.shared.money import Money
from app.normalization.pricing.parser import GovernedRetailPriceParser
from app.schemas.extraction import RawExtractionResult, RawExtractedProduct
from app.scrapers.blinkit.parser import BlinkitProductParser
from app.retailer_data.types import RetailerObservation


class RetailerAcquisition(Protocol):
    async def acquire_search(self, query: str):
        """Acquire using the provider's existing acquisition implementation."""


class BlinkitRetailerDataProvider:
    """Provider adapter over existing Blinkit acquisition/parser output."""

    provider = "blinkit"
    schema_version = "retailer-observation-v1"

    def __init__(self, *, acquisition: RetailerAcquisition | None = None, parser: BlinkitProductParser | None = None, price_parser: GovernedRetailPriceParser | None = None) -> None:
        self.acquisition = acquisition
        self.parser = parser or BlinkitProductParser()
        self.price_parser = price_parser or GovernedRetailPriceParser()

    async def acquire(self, query: str) -> tuple[RetailerObservation, ...]:
        if self.acquisition is None:
            raise RuntimeError("Blinkit acquisition dependency is not configured")
        response = await self.acquisition.acquire_search(query)
        result = self.parser.parse_content(response.body, query=query, source_reference=response.url)
        return self.normalize(result)

    def normalize(
        self,
        result: RawExtractionResult,
        *,
        currency_code: str = "INR",
        acquired_at: datetime | None = None,
        source_artifact_reference: str | None = None,
    ) -> tuple[RetailerObservation, ...]:
        if result.platform != self.provider:
            raise ValueError("Blinkit provider requires Blinkit extraction output")
        if not result.source_reference or not result.source_reference.strip():
            raise ValueError("Blinkit extraction must carry a source artifact reference")
        durable_reference = source_artifact_reference or result.source_reference
        if not durable_reference.strip():
            raise ValueError("Blinkit extraction must carry a durable artifact reference")
        acquired = acquired_at or datetime.now(timezone.utc)
        output = []
        for product in result.products:
            if not product.retailer_product_id or not product.retailer_product_id.strip():
                raise ValueError("retailer listing ID is required")
            raw = json.dumps(product.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            digest = hashlib.sha256(raw.encode()).hexdigest()
            observed_at = result.extracted_at
            listed = self.price_parser.parse(product.displayed_price, currency_code=currency_code)
            effective = listed
            observation_id = RetailerObservation.deterministic_id(provider=self.provider, retailer_listing_id=product.retailer_product_id, observed_at=observed_at, payload_digest=digest)
            output.append(RetailerObservation(
                observation_id=observation_id, provider=self.provider, retailer=self.provider,
                retailer_listing_id=product.retailer_product_id, source_url=product.product_url,
                observed_at=observed_at, acquired_at=acquired, title=product.product_name,
                quantity_text=product.quantity, normalized_quantity=product.quantity,
                listed_price=listed, effective_price=effective,
                currency=currency_code if listed is not None else None,
                availability=product.availability_status.value if product.availability_status else None,
                stock_state=product.stock_availability, discount_text=product.offer_text,
                source_artifact_reference=durable_reference,
                source_reference=result.source_reference, payload_digest=digest,
                parser_version=result.parser_version, schema_version=self.schema_version,
                evidence_references=(
                    ("retailer_artifact", durable_reference),
                    ("retailer_source", result.source_reference),
                ),
            ))
        return tuple(output)
