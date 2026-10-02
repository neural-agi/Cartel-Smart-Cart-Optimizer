from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShoppingListCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def normalize_name(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("list name must not be blank")
        return self


class ShoppingListUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    archived: bool | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if self.name is None and self.archived is None:
            raise ValueError("at least one list field must be provided")
        if self.name is not None:
            self.name = self.name.strip()
            if not self.name:
                raise ValueError("list name must not be blank")
        return self


class ShoppingListItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=300)
    quantity: int = Field(default=1, ge=1, le=999)
    unit: str | None = Field(default=None, max_length=32)
    canonical_product_id: str | None = Field(default=None, min_length=1, max_length=128)
    canonical_variant_id: str | None = Field(default=None, min_length=1, max_length=128)
    source_platform: str | None = Field(default=None, min_length=1, max_length=64)
    source_listing_id: str | None = Field(default=None, min_length=1, max_length=256)
    source_observation_id: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def normalize_and_validate_identity(self):
        self.query = self.query.strip()
        if not self.query:
            raise ValueError("item query must not be blank")
        if self.unit is not None:
            self.unit = self.unit.strip() or None
        canonical = (self.canonical_product_id, self.canonical_variant_id)
        source = (self.source_platform, self.source_listing_id, self.source_observation_id)
        if (canonical[0] is None) != (canonical[1] is None):
            raise ValueError("canonical product and variant IDs must be supplied together")
        if any(value is not None for value in source) and not all(value is not None for value in source):
            raise ValueError("all source provenance fields must be supplied together")
        if canonical[0] is not None and not all(value is not None for value in source):
            raise ValueError("a confirmed product selection requires source provenance")
        if canonical[0] is None and any(value is not None for value in source):
            raise ValueError("source provenance requires a confirmed product selection")
        return self


class ShoppingListItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(ge=1, le=999)


class ShoppingListItemResponse(BaseModel):
    id: UUID
    query: str
    quantity: int
    unit: str | None
    resolution_status: str
    canonical_product_id: str | None
    canonical_variant_id: str | None
    display_name: str | None
    source_platform: str | None
    source_listing_id: str | None
    source_observation_id: str | None
    created_at: datetime
    updated_at: datetime


class ShoppingListResponse(BaseModel):
    id: UUID
    name: str
    revision: int
    archived: bool
    created_at: datetime
    updated_at: datetime
    items: tuple[ShoppingListItemResponse, ...] = ()
