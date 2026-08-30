from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from app.data_ingestion.types import CaptureCoverage


class RawExtractedProduct(BaseModel):
    source_index: int
    platform: str = "blinkit"
    retailer_product_id: str | None = None
    product_name: str
    displayed_price: str | None = None
    mrp: str | None = None
    quantity: str | None = None
    stock_availability: str | None = None
    offer_text: str | None = None
    raw_text: str


class RawExtractionResult(BaseModel):
    platform: str = "blinkit"
    parser_version: str = "blinkit-parser-v1"
    query: str | None = None
    source_path: Path | None = None
    source_reference: str | None = None
    extracted_at: datetime
    product_count: int = Field(ge=0)
    products: list[RawExtractedProduct]
    warnings: list[str] = Field(default_factory=list)
    evaluation_scope: str | None = None
    capture_coverage: CaptureCoverage | None = None
    pages_evaluated: int | None = None
    pagination_complete: bool | None = None
    termination_reason: str | None = None
