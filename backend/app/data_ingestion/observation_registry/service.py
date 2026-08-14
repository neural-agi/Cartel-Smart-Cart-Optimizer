from __future__ import annotations

import json
from threading import RLock

from app.data_ingestion.observation_registry.exceptions import ObservationRegistrationConflict
from app.data_ingestion.observation_registry.interface import ObservationRegistry
from app.data_ingestion.types import NormalizedObservation


def _canonical_payload(observation: NormalizedObservation) -> str:
    return json.dumps(
        observation.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


class InMemoryObservationRegistry(ObservationRegistry):
    """Single-process, immutable observation registry."""

    def __init__(self) -> None:
        self._records: dict[str, tuple[NormalizedObservation, str]] = {}
        self._lock = RLock()

    def register(self, observation: NormalizedObservation) -> NormalizedObservation:
        observation_id = observation.observation_id
        payload = _canonical_payload(observation)
        with self._lock:
            existing = self._records.get(observation_id)
            if existing is not None:
                if existing[1] != payload:
                    raise ObservationRegistrationConflict(observation_id)
                return existing[0].model_copy(deep=True)
            canonical = observation.model_copy(deep=True)
            self._records[observation_id] = (canonical, payload)
            return canonical.model_copy(deep=True)

    def get(self, observation_id: str) -> NormalizedObservation | None:
        self._validate_lookup_key(observation_id)
        with self._lock:
            record = self._records.get(observation_id)
            return None if record is None else record[0].model_copy(deep=True)

    def exists(self, observation_id: str) -> bool:
        self._validate_lookup_key(observation_id)
        with self._lock:
            return observation_id in self._records

    def list_all(self) -> tuple[NormalizedObservation, ...]:
        with self._lock:
            return tuple(
                self._records[observation_id][0].model_copy(deep=True)
                for observation_id in sorted(self._records)
            )

    @staticmethod
    def _validate_lookup_key(observation_id: str) -> None:
        if not isinstance(observation_id, str) or not observation_id.strip():
            raise ValueError("observation_id must be non-empty")
