from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from app.product_intelligence.models import Product, ProductVariant


class CatalogValidationError(ValueError):
    """Raised when a canonical entity does not satisfy MVP catalog rules."""


class CatalogConflictError(ValueError):
    """Raised when canonical catalog state conflicts with an existing record."""


class AuthoritativeCatalogRecord(BaseModel):
    """Serializable authoritative catalog payload."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    products: list[Product] = Field(default_factory=list)
    variants: list[ProductVariant] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CatalogState:
    """Normalized canonical catalog state loaded from persistence."""

    products: tuple[Product, ...] = ()
    variants: tuple[ProductVariant, ...] = ()
