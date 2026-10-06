from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.config import get_settings
from app.retailer_data.types import RetailerObservation


class RetailerObservationConflict(ValueError):
    pass


class FilesystemRetailerObservationStore:
    """Append-only retailer observation store preserving historical snapshots."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or get_settings().data_dir / "retailer_data" / "observations"
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def register(self, observation: RetailerObservation) -> RetailerObservation:
        path = self.root_dir / f"{observation.observation_id}.json"
        payload = json.dumps(observation.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if path.exists():
            existing = RetailerObservation.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if existing != observation:
                raise RetailerObservationConflict(f"conflicting retailer observation: {observation.observation_id}")
            return existing
        temp = path.with_suffix(".json.tmp")
        temp.write_text(payload, encoding="utf-8")
        os.replace(temp, path)
        return observation

    def get(self, observation_id: str) -> RetailerObservation | None:
        path = self.root_dir / f"{observation_id}.json"
        if not path.exists():
            return None
        return RetailerObservation.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_for_listing(self, provider: str, retailer_listing_id: str) -> tuple[RetailerObservation, ...]:
        values = []
        for path in self.root_dir.glob("*.json"):
            observation = RetailerObservation.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if observation.provider == provider and observation.retailer_listing_id == retailer_listing_id:
                values.append(observation)
        return tuple(sorted(values, key=lambda item: (item.observed_at, item.observation_id)))

    def all(self) -> tuple[RetailerObservation, ...]:
        values = [
            RetailerObservation.model_validate(json.loads(path.read_text(encoding="utf-8")))
            for path in self.root_dir.glob("*.json")
        ]
        return tuple(sorted(values, key=lambda item: item.observation_id))
