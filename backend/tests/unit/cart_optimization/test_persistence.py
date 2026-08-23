import json

import pytest

from app.cart_optimization.enums import OptimizationOutcome
from app.cart_optimization.persistence import (
    FilesystemPlanningRequestRepository,
    FilesystemPlanningResultRepository,
    PlanningRecordConflict,
    PlanningRecordMalformed,
)
from app.cart_optimization.planning import CartPlanningRequest
from app.cart_optimization.types import CartOptimizationResult


def _request() -> CartPlanningRequest:
    return CartPlanningRequest(
        discovery={"items": []},
        candidate_contexts=(),
        plans=(),
        request_id="request/1",
        optimization_policy_version="policy-v1",
    )


def _result() -> CartOptimizationResult:
    return CartOptimizationResult(
        optimization_id="optimization/1",
        request_id="request/1",
        outcome=OptimizationOutcome.UNRESOLVED,
    )


def test_request_repository_round_trips_and_replays_identical_writes(tmp_path) -> None:
    repository = FilesystemPlanningRequestRepository(tmp_path / "requests")
    request = _request()

    assert repository.get(request.request_id) is None
    assert repository.save(request) == request
    assert repository.save(request) == request
    assert repository.get(request.request_id) == request


def test_request_repository_rejects_conflicting_identity_payload(tmp_path) -> None:
    repository = FilesystemPlanningRequestRepository(tmp_path / "requests")
    repository.save(_request())
    conflicting = _request().model_copy(update={"optimization_policy_version": "policy-v2"})

    with pytest.raises(PlanningRecordConflict):
        repository.save(conflicting)


def test_result_repository_round_trips_and_rejects_malformed_payload(tmp_path) -> None:
    repository = FilesystemPlanningResultRepository(tmp_path / "results")
    result = _result()
    assert repository.get(result.optimization_id) is None
    assert repository.save(result) == result
    assert repository.get(result.optimization_id) == result

    path = next((tmp_path / "results").glob("*.json"))
    path.write_text(json.dumps({"optimization_id": result.optimization_id}), encoding="utf-8")
    with pytest.raises(PlanningRecordMalformed):
        repository.get(result.optimization_id)
