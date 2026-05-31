from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class RawExtractedProduct(BaseModel):
    source_index: int
    platform: str = "blinkit"
    product_name: str
    displayed_price: str | None = None
    mrp: str | None = None
    quantity: str | None = None
    stock_availability: str | None = None
    offer_text: str | None = None
    raw_text: str


class RawExtractionResult(BaseModel):
    platform: str = "blinkit"
    query: str | None = None
    source_path: Path
    extracted_at: datetime
    product_count: int = Field(ge=0)
    products: list[RawExtractedProduct]
