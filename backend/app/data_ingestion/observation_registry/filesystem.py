from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock

from pydantic import ValidationError

from app.core.config import get_settings
from app.data_ingestion.observation_registry.exceptions import ObservationRegistrationConflict
from app.data_ingestion.observation_registry.interface import ObservationRegistry
from app.data_ingestion.observation_registry.service import _canonical_payload
from app.data_ingestion.timestamp_integrity import (
    CaptureTimestampRejection,
    CaptureTimestampRejectionReason,
    Clock,
    InvalidCaptureTimestamp,
    SystemClock,
    normalize_capture_timestamp,
)
from app.data_ingestion.types import NormalizedObservation


class FilesystemObservationRegistry(ObservationRegistry):
    """Durable local registry for immutable normalized observations."""

    def __init__(self, root_dir: Path | None = None, *, clock: Clock | None = None) -> None:
        self.root_dir = root_dir or (
            get_settings().data_dir / "product_intelligence" / "observations"
        )
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._clock = clock or SystemClock()
        self._lock = RLock()
        self._rejections: list[CaptureTimestampRejection] = []

    @property
    def rejections(self) -> tuple[CaptureTimestampRejection, ...]:
        """Typed quarantine outcomes observed while reading stored artifacts."""

        with self._lock:
            return tuple(self._rejections)

    def register(self, observation: NormalizedObservation) -> NormalizedObservation:
        normalize_capture_timestamp(
            observation.raw_artifact_reference.capture_timestamp,
            artifact_id=observation.raw_artifact_reference.artifact_id,
            clock=self._clock,
        )
        observation_id = observation.observation_id
        payload = _canonical_payload(observation)
        path = self._path(observation_id)
        with self._lock:
            if path.exists():
                try:
                    existing = self._read(path)
                except InvalidCaptureTimestamp as exc:
                    self._record_rejection(exc.rejection)
                    raise
                if _canonical_payload(existing) != payload:
                    raise ObservationRegistrationConflict(observation_id)
                return existing.model_copy(deep=True)

            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(payload, encoding="utf-8")
            os.replace(temporary, path)
            return observation.model_copy(deep=True)

    def get(self, observation_id: str) -> NormalizedObservation | None:
        self._validate_lookup_key(observation_id)
        path = self._path(observation_id)
        with self._lock:
            if not path.exists():
                return None
            try:
                return self._read(path).model_copy(deep=True)
            except InvalidCaptureTimestamp as exc:
                self._record_rejection(exc.rejection)
                return None

    def exists(self, observation_id: str) -> bool:
        self._validate_lookup_key(observation_id)
        with self._lock:
            return self._path(observation_id).exists()

    def list_all(self) -> tuple[NormalizedObservation, ...]:
        with self._lock:
            observations: list[NormalizedObservation] = []
            for path in sorted(self.root_dir.glob("*.json"), key=lambda item: item.name):
                try:
                    observations.append(self._read(path).model_copy(deep=True))
                except InvalidCaptureTimestamp as exc:
                    self._record_rejection(exc.rejection)
            return tuple(observations)

    def _record_rejection(self, rejection: CaptureTimestampRejection) -> None:
        if rejection not in self._rejections:
            self._rejections.append(rejection)

    def _path(self, observation_id: str) -> Path:
        return self.root_dir / f"{observation_id}.json"

    def _read(self, path: Path) -> NormalizedObservation:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidCaptureTimestamp(
                CaptureTimestampRejection(
                    artifact_id=path.stem,
                    reason=CaptureTimestampRejectionReason.malformed,
                    detail="stored observation is not readable JSON",
                )
            ) from exc

        artifact_id = self._artifact_id(payload, fallback=path.stem)
        try:
            observation = NormalizedObservation.model_validate(payload)
        except ValidationError as exc:
            raise InvalidCaptureTimestamp(
                CaptureTimestampRejection(
                    artifact_id=artifact_id,
                    reason=self._validation_reason(exc),
                    detail="stored observation failed capture-timestamp validation",
                )
            ) from exc

        normalize_capture_timestamp(
            observation.raw_artifact_reference.capture_timestamp,
            artifact_id=observation.raw_artifact_reference.artifact_id,
            clock=self._clock,
        )
        return observation

    @staticmethod
    def _artifact_id(payload: object, *, fallback: str) -> str:
        if not isinstance(payload, dict):
            return fallback
        artifact = payload.get("raw_artifact_reference")
        if not isinstance(artifact, dict):
            return fallback
        candidate = artifact.get("artifact_id")
        if isinstance(candidate, str) and candidate.strip():
            return candidate
        return fallback

    @staticmethod
    def _validation_reason(exc: ValidationError) -> CaptureTimestampRejectionReason:
        for error in exc.errors():
            if "capture_timestamp" not in tuple(error.get("loc", ())):
                continue
            message = str(error.get("msg", "")).casefold()
            if "timezone-aware" in message:
                return CaptureTimestampRejectionReason.naive
            return CaptureTimestampRejectionReason.malformed
        return CaptureTimestampRejectionReason.malformed

    @staticmethod
    def _validate_lookup_key(observation_id: str) -> None:
        if not isinstance(observation_id, str) or not observation_id.strip():
            raise ValueError("observation_id must be non-empty")
