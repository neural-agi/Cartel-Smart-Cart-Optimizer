"""Authoritative plan-correlated checkout observation persistence contracts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.cost_intelligence.observation.service import DeterministicCheckoutObservationRegistry
from app.cost_intelligence.observation.types import CheckoutObservation
from app.core.config import get_settings


class CheckoutObservationCorrelation(BaseModel):
    """Explicit immutable correlation between one plan and one checkout capture."""

    model_config = ConfigDict(frozen=True)

    plan_id: str
    request_id: str
    observation_id: str
    observation: CheckoutObservation


class CheckoutObservationCorrelationStore(Protocol):
    def register(self, request_id: str, plan_id: str, observation: CheckoutObservation) -> CheckoutObservationCorrelation: ...

    def get(self, request_id: str, plan_id: str) -> CheckoutObservationCorrelation | None: ...


class FilesystemCheckoutObservationCorrelationStore:
    """Atomic store keyed by explicit ``request_id + plan_id`` ownership."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or (get_settings().data_dir / "cost_intelligence" / "checkout_captures")
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._canonicalizer = DeterministicCheckoutObservationRegistry()

    def register(self, request_id: str, plan_id: str, observation: CheckoutObservation) -> CheckoutObservationCorrelation:
        request_id = self._require_text(request_id, "request_id")
        plan_id = self._require_text(plan_id, "plan_id")
        canonical = self._canonicalizer.canonicalize(observation)
        observation_id = self._observation_id(canonical)
        correlation = CheckoutObservationCorrelation(
            request_id=request_id,
            plan_id=plan_id,
            observation_id=observation_id,
            observation=canonical,
        )
        path = self._path(request_id, plan_id)
        if path.exists():
            existing = CheckoutObservationCorrelation.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
            if existing != correlation:
                raise ValueError(f"conflicting checkout observation correlation for plan_id={plan_id}")
            return existing
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(correlation.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(temporary, path)
        return correlation

    def get(self, request_id: str, plan_id: str) -> CheckoutObservationCorrelation | None:
        request_id = self._require_text(request_id, "request_id")
        plan_id = self._require_text(plan_id, "plan_id")
        path = self._path(request_id, plan_id)
        if not path.exists():
            return None
        return CheckoutObservationCorrelation.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )

    def _path(self, request_id: str, plan_id: str) -> Path:
        digest = hashlib.sha256(f"{request_id}\0{plan_id}".encode("utf-8")).hexdigest()
        return self.root_dir / f"{digest}.json"

    @staticmethod
    def _observation_id(observation: CheckoutObservation) -> str:
        payload = json.dumps(observation.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return "checkout_observation_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be non-empty")
        return value.strip()
