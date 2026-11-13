"""Conservative parser for the documented QuickCommerce search response."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.schemas.extraction import ProductAvailability, RawExtractedProduct, RawExtractionResult
from app.data_ingestion import CaptureCoverage


class QuickCommerceSearchParser:
    parser_version = "quickcommerce-search-v1"

    def parse(self, payload: bytes, *, query: str, source_reference: str, evaluation_scope: str) -> RawExtractionResult:
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("QuickCommerce response is not valid UTF-8 JSON") from exc

        envelope = decoded if isinstance(decoded, dict) else {}
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else envelope
        records = data if isinstance(data, list) else self._records(data)
        if records is None or not isinstance(records, list):
            raise ValueError("QuickCommerce response does not contain a product result list")

        products: list[RawExtractedProduct] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise ValueError("QuickCommerce product result must be an object")
            name = self._text(record.get("name"))
            if name is None:
                raise ValueError("QuickCommerce product result is missing name")
            product_id = self._text(record.get("id"))
            available = self._availability(record.get("available"), record.get("inventory"))
            product_metadata = record.get("platform") if isinstance(record.get("platform"), dict) else {}
            product_metadata = {key: value for key, value in product_metadata.items() if isinstance(value, (str, int, float, bool))}
            products.append(RawExtractedProduct(
                source_index=index,
                platform="blinkit",
                retailer_product_id=product_id,
                product_url=self._text(record.get("deeplink")),
                product_name=name,
                brand=self._text(record.get("brand")),
                displayed_price=self._text(record.get("offer_price")),
                mrp=self._text(record.get("mrp")),
                quantity=self._text(record.get("quantity")),
                stock_availability=self._text(record.get("inventory")),
                availability_status=available,
                raw_text=json.dumps(record, sort_keys=True, separators=(",", ":")),
                image_urls=[item for item in (record.get("images") or []) if isinstance(item, str)],
                retailer_store_id=self._text(record.get("store_id")),
                provider_metadata={
                    **product_metadata,
                    "rank": record.get("rank"),
                    "rating": record.get("rating"),
                    "rating_count": record.get("rating_count"),
                    "is_ad": record.get("is_ad"),
                },
            ))
        coverage = CaptureCoverage(
            evaluation_scope=evaluation_scope, pages_evaluated=1,
            pagination_complete=True, termination_reason="provider_response_complete",
        )
        return RawExtractionResult(
            platform="blinkit",
            parser_version=self.parser_version,
            query=query,
            source_reference=source_reference,
            extracted_at=datetime.now(timezone.utc),
            product_count=len(products),
            products=products,
            evaluation_scope=evaluation_scope,
            capture_coverage=coverage,
            pages_evaluated=1,
            pagination_complete=True,
            termination_reason="provider_response_complete",
            provider_request_id=self._text(envelope.get("request_id")),
            provider_metadata={
                "credits_remaining": envelope.get("credits_remaining"),
                "platform": data.get("platform") if isinstance(data, dict) else None,
                "total_results": data.get("total_results") if isinstance(data, dict) else None,
                "latitude": data.get("lat") if isinstance(data, dict) else None,
                "longitude": data.get("lon") if isinstance(data, dict) else None,
            },
        )

    @staticmethod
    def _records(decoded):
        if not isinstance(decoded, dict):
            return None
        for key in ("results", "products", "data"):
            value = decoded.get(key)
            if isinstance(value, list):
                return value
        return None

    @staticmethod
    def _text(value) -> str | None:
        if value is None:
            return None
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip()
        return None

    @classmethod
    def _availability(cls, available, inventory) -> ProductAvailability | None:
        if isinstance(available, bool):
            return ProductAvailability.AVAILABLE if available else ProductAvailability.OUT_OF_STOCK
        inventory_text = cls._text(inventory)
        if inventory_text is None:
            return None
        normalized = inventory_text.casefold()
        if normalized in {"0", "out_of_stock", "out of stock", "unavailable"}:
            return ProductAvailability.OUT_OF_STOCK
        if normalized in {"available", "in_stock", "in stock", "1"}:
            return ProductAvailability.AVAILABLE
        return ProductAvailability.UNKNOWN
