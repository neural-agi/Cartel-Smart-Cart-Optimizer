from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class Money(BaseModel):
    """Deterministic monetary value stored in integer minor units."""

    model_config = ConfigDict(frozen=True)

    currency: str
    minor_units: int

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3:
            raise ValueError("currency must be a 3-letter ISO code")
        return normalized
