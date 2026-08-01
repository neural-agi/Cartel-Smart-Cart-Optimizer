"""Deterministic Fee Evaluation contracts and services."""

from typing import TYPE_CHECKING

from app.cost_intelligence.fee.types import FeeType

if TYPE_CHECKING:
    from app.cost_intelligence.evaluation.types import FeeEvaluationResult
    from app.cost_intelligence.fee.orchestrator import FeeEvaluationOrchestrator
    from app.cost_intelligence.fee.service import FeeEvaluationService

__all__ = [
    "FeeEvaluationOrchestrator",
    "FeeEvaluationResult",
    "FeeEvaluationService",
    "FeeType",
]


def __getattr__(name: str):
    if name == "FeeEvaluationResult":
        from app.cost_intelligence.evaluation.types import FeeEvaluationResult

        return FeeEvaluationResult
    if name == "FeeEvaluationOrchestrator":
        from app.cost_intelligence.fee.orchestrator import FeeEvaluationOrchestrator

        return FeeEvaluationOrchestrator
    if name == "FeeEvaluationService":
        from app.cost_intelligence.fee.service import FeeEvaluationService

        return FeeEvaluationService
    raise AttributeError(name)
