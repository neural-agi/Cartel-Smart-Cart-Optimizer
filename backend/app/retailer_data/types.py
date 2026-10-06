from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from hashlib import sha256
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.cost_intelligence.shared.money import Money
from app.data_ingestion.enums import Platform


class AssociationStatus(StrEnum):
    unassociated = "unassociated"
    associated = "associated"
    rejected = "rejected"
    needs_review = "needs_review"


class RetailerObservationFreshness(StrEnum):
    current = "current"
    stale = "stale"
    unavailable = "unavailable"
    never_observed = "never_observed"


class RetailerObservation(BaseModel):
    """A retailer fact; it is never a canonical Product or ProductVariant."""

    model_config = ConfigDict(frozen=True)

    observation_id: str
    provider: str
    retailer: str
    retailer_listing_id: str
    source_url: str | None = None
    observed_at: datetime
    acquired_at: datetime
    title: str
    brand_text: str | None = None
    quantity_text: str | None = None
    normalized_quantity: str | None = None
    listed_price: Money | None = None
    effective_price: Money | None = None
    currency: str | None = None
    availability: str | None = None
    stock_state: str | None = None
    discount_text: str | None = None
    market_context: str | None = None
    location_context: str | None = None
    session_context: str | None = None
    source_artifact_reference: str
    source_reference: str | None = None
    payload_digest: str
    parser_version: str
    schema_version: str
    evidence_references: tuple[tuple[str, str], ...] = ()

    @field_validator("observation_id", "provider", "retailer", "retailer_listing_id", "title", "source_artifact_reference", "payload_digest", "parser_version", "schema_version")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("retailer observation required text must not be blank")
        return value.strip()

    @property
    def freshness(self) -> RetailerObservationFreshness:
        return RetailerObservationFreshness.current

    def freshness_at(self, *, now: datetime | None = None, max_age: timedelta) -> RetailerObservationFreshness:
        reference = now or datetime.now(timezone.utc)
        observed = self.observed_at if self.observed_at.tzinfo else self.observed_at.replace(tzinfo=timezone.utc)
        return RetailerObservationFreshness.current if reference - observed <= max_age else RetailerObservationFreshness.stale

    @staticmethod
    def deterministic_id(*, provider: str, retailer_listing_id: str, observed_at: datetime, payload_digest: str) -> str:
        payload = json.dumps([provider, retailer_listing_id, observed_at.isoformat(), payload_digest], separators=(",", ":"))
        return "retailer_observation_" + sha256(payload.encode()).hexdigest()[:24]


class RetailerAssociation(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    retailer: str
    retailer_listing_id: str
    canonical_variant_id: str | None = None
    status: AssociationStatus = AssociationStatus.unassociated
    method: str = "operator_supplied"
    evidence_references: tuple[tuple[str, str], ...] = ()
    created_at: datetime
    updated_at: datetime

