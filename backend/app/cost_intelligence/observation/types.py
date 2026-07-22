from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from pydantic import computed_field

from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


class CheckoutLineItemObservation(BaseModel):
    """Observed checkout line item."""

    model_config = ConfigDict(frozen=True)

    label: str
    quantity_text: str | None = None
    displayed_price: Money | None = None
    reference_price: Money | None = None
    raw_text: str | None = None


class CheckoutFeeObservation(BaseModel):
    """Observed checkout fee line."""

    model_config = ConfigDict(frozen=True)

    label: str
    amount: Money | None = None
    raw_text: str | None = None

    @computed_field
    @property
    def fee_id(self) -> str:
        """Deterministic identity of this canonical observed fee."""
        payload = json.dumps(
            self.model_dump(mode="json", exclude={"fee_id"}),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CheckoutOfferObservation(BaseModel):
    """Observed promotion or offer text."""

    model_config = ConfigDict(frozen=True)

    label: str
    amount: Money | None = None
    raw_text: str | None = None

    @computed_field
    @property
    def offer_id(self) -> str:
        """Deterministic identity of this canonical observed offer."""
        payload = json.dumps(
            self.model_dump(mode="json", exclude={"offer_id"}),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CheckoutMembershipObservation(BaseModel):
    """Observed membership-state fact."""

    model_config = ConfigDict(frozen=True)

    label: str
    raw_text: str | None = None


class CheckoutPaymentObservation(BaseModel):
    """Observed payment-method fact."""

    model_config = ConfigDict(frozen=True)

    label: str
    raw_text: str | None = None


class CheckoutThresholdObservation(BaseModel):
    """Observed threshold condition."""

    model_config = ConfigDict(frozen=True)

    label: str
    threshold_amount: Money | None = None
    raw_text: str | None = None


class CheckoutTotalObservation(BaseModel):
    """Observed checkout total or subtotal surface."""

    model_config = ConfigDict(frozen=True)

    label: str
    amount: Money | None = None
    raw_text: str | None = None


class CheckoutObservation(BaseModel):
    """Immutable checkout capture composed from smaller observation surfaces."""

    model_config = ConfigDict(frozen=True)

    platform: str
    source_artifact_reference: str
    capture_timestamp: datetime
    parser_version: str
    capture_context_reference: str | None = None
    evidence_references: tuple[EvidenceReference, ...] = Field(default_factory=tuple)
    line_items: tuple[CheckoutLineItemObservation, ...] = Field(default_factory=tuple)
    fees: tuple[CheckoutFeeObservation, ...] = Field(default_factory=tuple)
    offers: tuple[CheckoutOfferObservation, ...] = Field(default_factory=tuple)
    memberships: tuple[CheckoutMembershipObservation, ...] = Field(default_factory=tuple)
    payment_methods: tuple[CheckoutPaymentObservation, ...] = Field(default_factory=tuple)
    thresholds: tuple[CheckoutThresholdObservation, ...] = Field(default_factory=tuple)
    totals: tuple[CheckoutTotalObservation, ...] = Field(default_factory=tuple)


class CheckoutObservationRegistrationRequest(BaseModel):
    """Input for registering a canonical checkout observation."""

    observation: CheckoutObservation


class CheckoutObservationRegistrationResponse(BaseModel):
    """Deterministic result of registering a checkout observation."""

    observation_id: str
    observation: CheckoutObservation
