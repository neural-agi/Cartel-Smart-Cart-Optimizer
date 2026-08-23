"""Contract-safe filesystem persistence for immutable planning records.

This module persists request and result payloads independently. It deliberately
does not define lifecycle, retention, ownership, or request/result atomicity.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import quote

from app.cart_optimization.planning import CartPlanningRequest
from app.cart_optimization.serialization import CartPlanningSerialization
from app.cart_optimization.types import CartOptimizationResult


class PlanningPersistenceError(ValueError):
    """Base error for invalid or conflicting planning records."""


class PlanningRecordConflict(PlanningPersistenceError):
    """Raised when an identity is reused with a different payload."""


class PlanningRecordMalformed(PlanningPersistenceError):
    """Raised when a stored planning payload cannot be validated."""


class PlanningRequestRepository(ABC):
    @abstractmethod
    def save(self, request: CartPlanningRequest) -> CartPlanningRequest:
        """Save or replay a request with the same request identity."""

    @abstractmethod
    def get(self, request_id: str) -> CartPlanningRequest | None:
        """Load a request, or return None when it does not exist."""


class PlanningResultRepository(ABC):
    @abstractmethod
    def save(self, result: CartOptimizationResult) -> CartOptimizationResult:
        """Save or replay a result with the same optimization identity."""

    @abstractmethod
    def get(self, optimization_id: str) -> CartOptimizationResult | None:
        """Load a result, or return None when it does not exist."""


class FilesystemPlanningRequestRepository(PlanningRequestRepository):
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save(self, request: CartPlanningRequest) -> CartPlanningRequest:
        path = self._path(request.request_id)
        payload = CartPlanningSerialization.request_json(request)
        if path.exists():
            existing = self._read(path)
            if CartPlanningSerialization.request_json(existing) != payload:
                raise PlanningRecordConflict(
                    f"conflicting planning request for request_id={request.request_id}"
                )
            return existing
        self._atomic_write(path, payload)
        return request.model_copy(deep=True)

    def get(self, request_id: str) -> CartPlanningRequest | None:
        path = self._path(request_id)
        if not path.exists():
            return None
        return self._read(path)

    def _path(self, request_id: str) -> Path:
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id must be non-empty")
        return self.root_dir / f"{quote(request_id, safe='')}.json"

    @staticmethod
    def _read(path: Path) -> CartPlanningRequest:
        try:
            return CartPlanningSerialization.request_from_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PlanningRecordMalformed(f"malformed planning request: {path}") from exc

    @staticmethod
    def _atomic_write(path: Path, payload: str) -> None:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)


class FilesystemPlanningResultRepository(PlanningResultRepository):
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save(self, result: CartOptimizationResult) -> CartOptimizationResult:
        path = self._path(result.optimization_id)
        payload = CartPlanningSerialization.result_json(result)
        if path.exists():
            existing = self._read(path)
            if CartPlanningSerialization.result_json(existing) != payload:
                raise PlanningRecordConflict(
                    f"conflicting optimization result for optimization_id={result.optimization_id}"
                )
            return existing
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)
        return result.model_copy(deep=True)

    def get(self, optimization_id: str) -> CartOptimizationResult | None:
        path = self._path(optimization_id)
        if not path.exists():
            return None
        return self._read(path)

    def _path(self, optimization_id: str) -> Path:
        if not isinstance(optimization_id, str) or not optimization_id.strip():
            raise ValueError("optimization_id must be non-empty")
        return self.root_dir / f"{quote(optimization_id, safe='')}.json"

    @staticmethod
    def _read(path: Path) -> CartOptimizationResult:
        try:
            return CartPlanningSerialization.result_from_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PlanningRecordMalformed(f"malformed optimization result: {path}") from exc
