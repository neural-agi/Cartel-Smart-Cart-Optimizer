"""Deterministic, fail-closed retailer cart capture contracts."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.cart_optimization.types import CandidateItemAllocation


class CartVerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIABLE = "unverifiable"
    MISMATCH = "mismatch"
    CONTAMINATED = "contaminated"
    UNAVAILABLE = "unavailable"


class RetailerCartIdentity(BaseModel):
    """Retailer cart identity; browser/session identity is never a substitute."""

    model_config = ConfigDict(frozen=True)

    retailer_id: str
    request_id: str
    plan_id: str
    retailer_cart_id: str | None = None
    identity_available: bool = False


class RetailerCartLine(BaseModel):
    """One observed retailer cart line tied to a target capture."""

    model_config = ConfigDict(frozen=True)

    retailer_product_id: str
    quantity: int
    retailer_cart_line_id: str | None = None
    retailer_id: str
    request_id: str
    plan_id: str
    source_reference: str

    @property
    def deterministic_reference(self) -> str:
        payload = json.dumps(
            {
                "plan_id": self.plan_id,
                "request_id": self.request_id,
                "retailer_id": self.retailer_id,
                "retailer_product_id": self.retailer_product_id,
                "quantity": self.quantity,
                "source_reference": self.source_reference,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RetailerCartSnapshot(BaseModel):
    """Sanitized cart state used only for exact target-plan verification."""

    model_config = ConfigDict(frozen=True)

    identity: RetailerCartIdentity
    lines: tuple[RetailerCartLine, ...] = Field(default_factory=tuple)
    locality_reference: str | None = None
    merchant_reference: str | None = None


class CartConstructionResult(BaseModel):
    """Requested allocation lines and the retailer's verified cart snapshot."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    plan_id: str
    expected_allocations: tuple[CandidateItemAllocation, ...]
    snapshot: RetailerCartSnapshot | None = None
    status: CartVerificationStatus
    reasons: tuple[str, ...] = Field(default_factory=tuple)


class CartOwnershipVerifier:
    """Verify exact plan lines without inventing cart or line identity."""

    def verify(
        self,
        *,
        request_id: str,
        plan_id: str,
        allocations: tuple[CandidateItemAllocation, ...],
        snapshot: RetailerCartSnapshot | None,
    ) -> CartConstructionResult:
        if snapshot is None:
            return CartConstructionResult(
                request_id=request_id,
                plan_id=plan_id,
                expected_allocations=allocations,
                status=CartVerificationStatus.UNAVAILABLE,
                reasons=("retailer cart state is unavailable",),
            )
        if snapshot.identity.request_id != request_id or snapshot.identity.plan_id != plan_id:
            return self._result(request_id, plan_id, allocations, snapshot, CartVerificationStatus.MISMATCH, "cart correlation does not match capture")
        if not snapshot.identity.identity_available or not snapshot.identity.retailer_cart_id:
            return self._result(request_id, plan_id, allocations, snapshot, CartVerificationStatus.UNVERIFIABLE, "retailer cart identity is unavailable")

        expected = sorted(
            (a.retailer_id, a.listing_provenance.retailer_product_id, a.quantity)
            for a in allocations
            if a.listing_provenance.retailer_product_id
        )
        observed = sorted((line.retailer_id, line.retailer_product_id, line.quantity) for line in snapshot.lines)
        if any(not a.listing_provenance.retailer_product_id for a in allocations):
            return self._result(request_id, plan_id, allocations, snapshot, CartVerificationStatus.UNVERIFIABLE, "allocation lacks authoritative retailer product identity")
        if expected != observed:
            return self._result(request_id, plan_id, allocations, snapshot, CartVerificationStatus.CONTAMINATED, "retailer cart contains unexpected or mismatched lines")
        return self._result(request_id, plan_id, allocations, snapshot, CartVerificationStatus.VERIFIED)

    @staticmethod
    def _result(request_id, plan_id, allocations, snapshot, status, reason=None):
        return CartConstructionResult(
            request_id=request_id,
            plan_id=plan_id,
            expected_allocations=allocations,
            snapshot=snapshot,
            status=status,
            reasons=(reason,) if reason else (),
        )
