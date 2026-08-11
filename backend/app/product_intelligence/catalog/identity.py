"""Approved MVP canonical Product and ProductVariant identity keys."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.models import Product, ProductVariant


def _text(value: str | None, *, field: str) -> str:
    if value is None:
        raise ValueError(f"{field} is required for canonical identity")
    normalized = " ".join(value.split()).casefold()
    if not normalized:
        raise ValueError(f"{field} is required for canonical identity")
    return normalized


def _quantity(value: str | None) -> tuple[str, str]:
    normalized = _text(value, field="normalized_quantity")
    parts = normalized.split(" ")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("normalized_quantity must be an exact '<value> <unit>' representation")
    try:
        amount = Decimal(parts[0])
    except InvalidOperation as exc:
        raise ValueError("normalized_quantity amount is malformed") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError("normalized_quantity amount is malformed")
    return format(amount, "f"), parts[1]


def product_observation_key(observation: NormalizedObservation) -> tuple[str, str]:
    return (
        _text(observation.normalized_name, field="normalized_name"),
        _text(observation.normalized_category, field="normalized_category"),
    )


def product_catalog_key(product: Product) -> tuple[str, str]:
    return (
        _text(product.canonical_display_name, field="canonical_display_name"),
        _text(product.canonical_category_reference.category_id, field="category_id"),
    )


def variant_observation_key(
    observation: NormalizedObservation,
    product: Product,
) -> tuple[str, tuple[str, str]]:
    return (product.canonical_product_id, _quantity(observation.normalized_quantity))


def variant_catalog_key(variant: ProductVariant) -> tuple[str, tuple[str, str]]:
    measurement = variant.pack_configuration.content_per_consumer_unit
    if measurement is None:
        raise ValueError("variant content measurement is required for canonical identity")
    if measurement.value <= 0 or not measurement.value.is_finite():
        raise ValueError("variant content measurement is malformed")
    return (
        _text(variant.canonical_product_id, field="canonical_product_id"),
        (format(measurement.value, "f"), _text(measurement.unit, field="unit")),
    )
