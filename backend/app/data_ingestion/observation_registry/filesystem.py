from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock

from app.core.config import get_settings
from app.data_ingestion.observation_registry.exceptions import ObservationRegistrationConflict
from app.data_ingestion.observation_registry.interface import ObservationRegistry
from app.data_ingestion.observation_registry.service import _canonical_payload
from app.data_ingestion.types import NormalizedObservation


class FilesystemObservationRegistry(ObservationRegistry):
    """Durable local registry for immutable normalized observations."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or (
            get_settings().data_dir / "product_intelligence" / "observations"
        )
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def register(self, observation: NormalizedObservation) -> NormalizedObservation:
        observation_id = observation.observation_id
        payload = _canonical_payload(observation)
        path = self._path(observation_id)
        with self._lock:
            if path.exists():
                existing = self._read(path)
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
            return None if not path.exists() else self._read(path).model_copy(deep=True)

    def exists(self, observation_id: str) -> bool:
        self._validate_lookup_key(observation_id)
        with self._lock:
            return self._path(observation_id).exists()

    def list_all(self) -> tuple[NormalizedObservation, ...]:
        with self._lock:
            return tuple(
                self._read(path).model_copy(deep=True)
                for path in sorted(self.root_dir.glob("*.json"), key=lambda item: item.name)
            )

    def _path(self, observation_id: str) -> Path:
        return self.root_dir / f"{observation_id}.json"

    @staticmethod
    def _read(path: Path) -> NormalizedObservation:
        return NormalizedObservation.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )

    @staticmethod
    def _validate_lookup_key(observation_id: str) -> None:
        if not isinstance(observation_id, str) or not observation_id.strip():
            raise ValueError("observation_id must be non-empty")
