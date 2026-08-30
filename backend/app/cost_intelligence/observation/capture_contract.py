"""Application-owned checkout capture request, artifact, and parser contracts."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.cart_optimization.types import CartItemRequest, CandidateItemAllocation
from app.data_ingestion.enums import CaptureType
from app.product_intelligence.models import EvidenceReference
from app.cost_intelligence.observation.types import CheckoutObservation


def _text(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value must be non-empty")
    return value.strip()


class CheckoutCaptureRequest(BaseModel):
    """Explicit ownership and cart identity supplied to a capture adapter."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    plan_id: str
    platform: str
    cart_items: tuple[CartItemRequest, ...]
    # Optional for legacy callers; checkout-capable adapters require this
    # authoritative allocation data to construct the retailer cart.
    candidate_allocations: tuple[CandidateItemAllocation, ...] = Field(default_factory=tuple)

    _required = field_validator("request_id", "plan_id", "platform")(_text)

    @field_validator("cart_items")
    @classmethod
    def _items(cls, value: tuple[CartItemRequest, ...]) -> tuple[CartItemRequest, ...]:
        if not value:
            raise ValueError("cart_items must not be empty")
        identities = [(item.item_id, item.canonical_variant_id) for item in value]
        if len(identities) != len(set(identities)):
            raise ValueError("cart_items must have unique logical identities")
        return value

    @model_validator(mode="after")
    def _allocation_correspondence(self) -> "CheckoutCaptureRequest":
        if not self.candidate_allocations:
            return self
        requested = {(item.item_id, item.canonical_variant_id, item.quantity) for item in self.cart_items}
        allocated: dict[tuple[str, str], int] = {}
        for allocation in self.candidate_allocations:
            key = (allocation.item_id, allocation.canonical_variant_id)
            if key not in {(item.item_id, item.canonical_variant_id) for item in self.cart_items}:
                raise ValueError("checkout allocation does not belong to cart")
            allocated[key] = allocated.get(key, 0) + allocation.quantity
        for item in self.cart_items:
            if allocated.get((item.item_id, item.canonical_variant_id)) != item.quantity:
                raise ValueError("checkout allocations must fulfill cart quantities exactly")
        return self

class CheckoutCaptureArtifact(BaseModel):
    """Immutable raw checkout capture, distinct from listing observations."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    capture_type: CaptureType
    platform: str
    capture_timestamp: datetime
    source_reference: str
    capture_version: str
    parser_version: str
    content_type: str
    request_id: str
    plan_id: str
    payload: bytes
    evidence_references: tuple[EvidenceReference, ...]

    _required = field_validator(
        "artifact_id", "platform", "source_reference", "capture_version",
        "parser_version", "request_id", "plan_id",
        "content_type",
    )(_text)

    @field_validator("capture_type")
    @classmethod
    def _checkout_only(cls, value: CaptureType) -> CaptureType:
        if value is not CaptureType.CHECKOUT:
            raise ValueError("checkout capture artifact must use CaptureType.CHECKOUT")
        return value

    @field_validator("evidence_references")
    @classmethod
    def _evidence(cls, value: tuple[EvidenceReference, ...]) -> tuple[EvidenceReference, ...]:
        if not value:
            raise ValueError("checkout capture requires evidence references")
        return value


class CheckoutCaptureParser(Protocol):
    def parse(self, artifact: CheckoutCaptureArtifact) -> CheckoutObservation: ...


class JsonCheckoutCaptureParser:
    """Parse explicit structured checkout evidence without filling missing fields."""

    def parse(self, artifact: CheckoutCaptureArtifact) -> CheckoutObservation:
        if artifact.capture_type is not CaptureType.CHECKOUT:
            raise ValueError("unsupported checkout artifact type")
        media_type = artifact.content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/json" and not media_type.endswith("+json"):
            raise ValueError(
                "JsonCheckoutCaptureParser requires an application/json content type"
            )
        try:
            payload = json.loads(artifact.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("checkout artifact payload is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("checkout artifact payload must be an object")
        if payload.get("platform") not in (None, artifact.platform):
            raise ValueError("checkout artifact platform conflicts with payload")
        observation_payload = dict(payload)
        observation_payload["platform"] = artifact.platform
        observation_payload["source_artifact_reference"] = artifact.source_reference
        observation_payload["capture_timestamp"] = artifact.capture_timestamp
        observation_payload["parser_version"] = artifact.parser_version
        observation_payload["evidence_references"] = artifact.evidence_references
        try:
            return CheckoutObservation.model_validate(observation_payload)
        except ValueError as exc:
            raise ValueError("checkout artifact evidence is invalid") from exc
