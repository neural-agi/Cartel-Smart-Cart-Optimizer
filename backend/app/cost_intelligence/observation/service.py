from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.cost_intelligence.observation.interfaces import CheckoutObservationRegistry
from app.cost_intelligence.observation.types import (
    CheckoutFeeObservation,
    CheckoutLineItemObservation,
    CheckoutMembershipObservation,
    CheckoutObservation,
    CheckoutObservationRegistrationRequest,
    CheckoutObservationRegistrationResponse,
    CheckoutOfferObservation,
    CheckoutPaymentObservation,
    CheckoutThresholdObservation,
    CheckoutTotalObservation,
)
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _CheckoutObservationRecord:
    observation_id: str
    observation: CheckoutObservation
    payload: str


class DeterministicCheckoutObservationRegistry(CheckoutObservationRegistry):
    """Deterministic in-memory registry for checkout observations."""

    def __init__(self) -> None:
        self._records: dict[str, _CheckoutObservationRecord] = {}

    async def register(
        self,
        request: CheckoutObservationRegistrationRequest,
    ) -> CheckoutObservationRegistrationResponse:
        canonical = self._canonicalize_observation(request.observation)
        observation_id = self._observation_id(canonical)
        payload = self._payload(canonical)

        existing = self._records.get(observation_id)
        if existing is not None:
            if existing.payload != payload:
                raise ValueError("checkout observation id collision detected")
            logger.info("checkout_observation_reused observation_id=%s", observation_id)
            return CheckoutObservationRegistrationResponse(
                observation_id=observation_id,
                observation=existing.observation.model_copy(deep=True),
            )

        record = _CheckoutObservationRecord(
            observation_id=observation_id,
            observation=canonical,
            payload=payload,
        )
        self._records[observation_id] = record
        logger.info(
            "checkout_observation_registered platform=%s observation_id=%s source_artifact_reference=%s",
            canonical.platform,
            observation_id,
            canonical.source_artifact_reference,
        )
        return CheckoutObservationRegistrationResponse(
            observation_id=observation_id,
            observation=canonical.model_copy(deep=True),
        )

    def get_checkout_observation(self, observation_id: str) -> CheckoutObservation | None:
        record = self._records.get(observation_id)
        if record is None:
            return None
        return record.observation.model_copy(deep=True)

    def list_checkout_observations(self) -> list[CheckoutObservation]:
        return [
            self._records[observation_id].observation.model_copy(deep=True)
            for observation_id in sorted(self._records)
        ]

    def _canonicalize_observation(
        self,
        observation: CheckoutObservation,
    ) -> CheckoutObservation:
        canonical = observation.model_copy(
            update={
                "platform": self._normalize_platform(observation.platform),
                "source_artifact_reference": self._normalize_required_text(
                    observation.source_artifact_reference,
                    "source_artifact_reference",
                ),
                "parser_version": self._normalize_required_text(
                    observation.parser_version,
                    "parser_version",
                ),
                "capture_context_reference": self._normalize_optional_text(
                    observation.capture_context_reference
                ),
                "capture_timestamp": self._normalize_timestamp(
                    observation.capture_timestamp
                ),
                "evidence_references": self._canonicalize_evidence_references(
                    observation.evidence_references
                ),
                "line_items": self._canonicalize_sequence(observation.line_items),
                "fees": self._canonicalize_sequence(observation.fees),
                "offers": self._canonicalize_sequence(observation.offers),
                "memberships": self._canonicalize_sequence(observation.memberships),
                "payment_methods": self._canonicalize_sequence(
                    observation.payment_methods
                ),
                "thresholds": self._canonicalize_sequence(observation.thresholds),
                "totals": self._canonicalize_sequence(observation.totals),
            },
            deep=True,
        )
        self._validate_observation(canonical)
        return canonical

    def _validate_observation(self, observation: CheckoutObservation) -> None:
        if not observation.evidence_references:
            raise ValueError("checkout observation requires at least one evidence reference")
        if not any(
            (
                observation.line_items,
                observation.fees,
                observation.offers,
                observation.memberships,
                observation.payment_methods,
                observation.thresholds,
                observation.totals,
            )
        ):
            raise ValueError("checkout observation requires at least one child observation")
        for child in observation.line_items:
            self._validate_label(child.label, "line_items.label")
            self._validate_optional_text(child.quantity_text, "line_items.quantity_text")
            self._validate_optional_text(child.raw_text, "line_items.raw_text")
        for child in observation.fees:
            self._validate_label(child.label, "fees.label")
            self._validate_optional_text(child.raw_text, "fees.raw_text")
        for child in observation.offers:
            self._validate_label(child.label, "offers.label")
            self._validate_optional_text(child.raw_text, "offers.raw_text")
        for child in observation.memberships:
            self._validate_label(child.label, "memberships.label")
            self._validate_optional_text(child.raw_text, "memberships.raw_text")
        for child in observation.payment_methods:
            self._validate_label(child.label, "payment_methods.label")
            self._validate_optional_text(child.raw_text, "payment_methods.raw_text")
        for child in observation.thresholds:
            self._validate_label(child.label, "thresholds.label")
            self._validate_optional_text(child.raw_text, "thresholds.raw_text")
        for child in observation.totals:
            self._validate_label(child.label, "totals.label")
            self._validate_optional_text(child.raw_text, "totals.raw_text")

    def _canonicalize_sequence(self, items):
        canonical_items = [self._canonicalize_child(item) for item in items]
        ranked = [
            (
                json.dumps(
                    item.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                index,
                item,
            )
            for index, item in enumerate(canonical_items)
        ]
        ranked.sort(key=lambda item: (item[0], item[1]))
        return tuple(item for _, _, item in ranked)

    def _canonicalize_child(
        self,
        item: (
            CheckoutLineItemObservation
            | CheckoutFeeObservation
            | CheckoutOfferObservation
            | CheckoutMembershipObservation
            | CheckoutPaymentObservation
            | CheckoutThresholdObservation
            | CheckoutTotalObservation
        ),
    ):
        updates: dict[str, object] = {}
        if hasattr(item, "label"):
            updates["label"] = self._normalize_required_text(item.label, "label")
        if hasattr(item, "raw_text"):
            updates["raw_text"] = self._normalize_optional_text(item.raw_text)
        if hasattr(item, "quantity_text"):
            updates["quantity_text"] = self._normalize_optional_text(item.quantity_text)
        if hasattr(item, "displayed_price"):
            updates["displayed_price"] = self._canonicalize_money(
                item.displayed_price
            )
        if hasattr(item, "reference_price"):
            updates["reference_price"] = self._canonicalize_money(item.reference_price)
        if hasattr(item, "amount"):
            updates["amount"] = self._canonicalize_money(item.amount)
        if hasattr(item, "threshold_amount"):
            updates["threshold_amount"] = self._canonicalize_money(
                item.threshold_amount
            )
        return item.model_copy(update=updates, deep=True)

    def _canonicalize_money(self, money: Money | None) -> Money | None:
        if money is None:
            return None
        return Money(currency=money.currency, minor_units=money.minor_units)

    def _canonicalize_evidence_references(
        self,
        evidence_references: tuple[EvidenceReference, ...],
    ) -> tuple[EvidenceReference, ...]:
        canonical: dict[tuple[str, str], tuple[str, EvidenceReference]] = {}
        for evidence_reference in evidence_references:
            source_type = self._normalize_required_text(
                evidence_reference.source_type,
                "evidence_references.source_type",
            )
            source_id = self._normalize_required_text(
                evidence_reference.source_id,
                "evidence_references.source_id",
            )
            canonical_reference = evidence_reference.model_copy(
                update={
                    "source_type": source_type,
                    "source_id": source_id,
                    "capture_timestamp": (
                        self._normalize_timestamp(evidence_reference.capture_timestamp)
                        if evidence_reference.capture_timestamp is not None
                        else None
                    ),
                    "note": self._normalize_optional_text(evidence_reference.note),
                },
                deep=True,
            )
            payload = json.dumps(
                canonical_reference.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            key = (source_type, source_id)
            existing = canonical.get(key)
            if existing is None or payload < existing[0]:
                canonical[key] = (payload, canonical_reference)
        return tuple(canonical[key][1] for key in sorted(canonical))

    def _normalize_platform(self, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("platform must not be blank")
        return normalized

    def _normalize_required_text(self, value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be blank")
        return normalized

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _normalize_timestamp(self, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    def _validate_label(self, value: str, field_name: str) -> None:
        if not value.strip():
            raise ValueError(f"{field_name} must not be blank")

    def _validate_optional_text(self, value: str | None, field_name: str) -> None:
        if value is None:
            return
        if not value.strip():
            raise ValueError(f"{field_name} must not be blank when provided")

    def _payload(self, observation: CheckoutObservation) -> str:
        return json.dumps(
            observation.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )

    def _observation_id(self, observation: CheckoutObservation) -> str:
        digest = hashlib.sha256(self._payload(observation).encode("utf-8")).hexdigest()
        return f"checkout_observation_{digest[:24]}"
