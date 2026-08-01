from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.cart_optimization.types import CartOptimizationRequest
from app.cost_intelligence.observation.types import CheckoutObservation
from app.cost_intelligence.pipeline.service import (
    CostIntelligencePipelineResult,
    CostIntelligencePipelineService,
)


class CostIntelligenceEvaluateRequest(BaseModel):
    """Transport request for one deterministic Cost Intelligence evaluation."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "observation": {
                    "platform": "blinkit",
                    "source_artifact_reference": "checkout-artifact-1",
                    "capture_timestamp": "2026-01-01T00:00:00Z",
                    "parser_version": "checkout-v1",
                    "evidence_references": [
                        {"source_type": "artifact", "source_id": "checkout-1"}
                    ],
                },
                "optimization_request": {
                    "request_id": "api-request-1",
                    "optimization_policy_version": "policy-v1",
                    "candidate_plan_coverage": {
                        "state": "complete",
                        "scope_reference": "scope-1",
                        "candidate_set_reference": "set-1",
                        "coverage_basis": "api",
                        "validation_reference": "validation-1",
                    },
                },
            }
        },
    )

    observation: CheckoutObservation = Field(
        description="Immutable checkout observation to evaluate.",
    )
    optimization_request: CartOptimizationRequest = Field(
        description="Explicit Cart Optimization inputs; no optimization defaults are inferred.",
    )


router = APIRouter()
pipeline_service = CostIntelligencePipelineService()


@router.post(
    "/cost-intelligence/evaluate",
    response_model=CostIntelligencePipelineResult,
    status_code=status.HTTP_200_OK,
    summary="Evaluate checkout cost intelligence",
    response_description="Complete deterministic Cost Intelligence pipeline result.",
    responses={
        200: {
            "description": "Complete deterministic Cost Intelligence pipeline result.",
            "content": {
                "application/json": {
                    "example": {
                        "context": {"context_id": "deterministic-context-id"},
                        "offer_results": [],
                        "fee_results": [],
                        "membership_results": [],
                        "effective_cost_result": {
                            "evaluation_id": "deterministic-effective-cost-id",
                            "context_id": "deterministic-context-id",
                            "effective_cost": None,
                        },
                        "optimization_result": {
                            "optimization_id": "deterministic-optimization-id",
                            "request_id": "api-request-1",
                            "outcome": "infeasible",
                            "chosen_plan_id": None,
                        },
                    }
                }
            },
        }
    },
    tags=["cost-intelligence"],
)
def evaluate_cost_intelligence(
    request: CostIntelligenceEvaluateRequest,
) -> CostIntelligencePipelineResult:
    try:
        return pipeline_service.run(request.observation, request.optimization_request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal cost intelligence pipeline error",
        ) from exc
