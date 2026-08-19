"""Application boundary for registering externally captured checkout evidence."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.cost_intelligence.observation.checkout_capture import (
    CheckoutObservationCorrelation,
    CheckoutObservationCorrelationStore,
)
from app.cost_intelligence.observation.types import CheckoutObservation


class CheckoutCaptureRegistration(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    plan_id: str
    observation: CheckoutObservation


class CheckoutCaptureRegistrationService:
    """Persist an explicitly captured observation without acquiring it."""

    def __init__(self, store: CheckoutObservationCorrelationStore) -> None:
        self._store = store

    def register(
        self, registration: CheckoutCaptureRegistration
    ) -> CheckoutObservationCorrelation:
        request_id = self._require_text(registration.request_id, "request_id")
        plan_id = self._require_text(registration.plan_id, "plan_id")
        return self._store.register(request_id, plan_id, registration.observation)

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        if not value.strip():
            raise ValueError(f"{field_name} must be non-empty")
        return value.strip()
