from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.responses import JSONResponse

from app.api.dependencies.consumer import ConsumerPrincipal, csrf_protected, current_consumer
from app.cart_optimization.automatic_planning import (
    AutomaticCartItem,
    AutomaticPlanningRequest,
    AutomaticPlanningStatus,
)
from app.cart_optimization.enums import OptimizationOutcome
from app.cart_optimization.providers import PlanningProviderUnavailable
from app.db.models import (
    OptimizationAllocationRecord,
    OptimizationPlanRecord,
    OptimizationRequestRecord,
    ShoppingList,
)
from app.db.session import get_db
from app.schemas.shopping_lists import OptimizationCreate, OptimizationResponse
from app.services.idempotency import claim, complete, idempotency_key


router = APIRouter(prefix="/optimizations", tags=["consumer-optimizations"])


def _owned_list(db: Session, user_id: UUID, list_id: UUID, *, lock: bool = False) -> ShoppingList:
    statement = (
        select(ShoppingList)
        .where(ShoppingList.id == list_id, ShoppingList.user_id == user_id)
        .options(selectinload(ShoppingList.items))
    )
    if lock:
        statement = statement.with_for_update()
    result = db.scalar(statement)
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "shopping_list_not_found"})
    return result


def _response(record: OptimizationRequestRecord) -> OptimizationResponse:
    return OptimizationResponse(
        request_id=record.request_id,
        list_id=record.shopping_list_id,
        list_revision=record.list_revision,
        input_digest=record.input_digest,
        policy_version=record.policy_version,
        status=record.status,
        input_snapshot=record.input_snapshot,
        result_snapshot=record.result_snapshot,
        created_at=record.created_at,
    )


def _persist_plans(db: Session, record: OptimizationRequestRecord, optimizer_result: dict[str, Any] | None) -> None:
    if not optimizer_result:
        return
    plans = []
    chosen = optimizer_result.get("chosen_plan")
    if chosen:
        plans.append((chosen, True, 0))
    plans.extend((plan, False, index + 1) for index, plan in enumerate(optimizer_result.get("alternative_plans", [])))
    plans.extend((plan, False, None) for plan in optimizer_result.get("rejected_plans", []))
    for plan, selected, ranking_position in plans:
        plan_row = OptimizationPlanRecord(
            request_record_id=record.id,
            user_id=record.user_id,
            plan_id=plan["plan_id"],
            feasibility=plan.get("feasibility", "rejected"),
            ranking_position=ranking_position,
            selected=selected,
            plan_snapshot=plan,
        )
        db.add(plan_row)
        db.flush()
        for allocation in plan.get("candidate_item_allocations", []):
            provenance = allocation["listing_provenance"]
            db.add(OptimizationAllocationRecord(
                plan_record_id=plan_row.id,
                user_id=record.user_id,
                item_id_snapshot=allocation["item_id"],
                canonical_product_id=allocation["canonical_product_id"],
                canonical_variant_id=allocation["canonical_variant_id"],
                quantity=allocation["quantity"],
                retailer_id=allocation["retailer_id"],
                platform=provenance["platform"],
                platform_listing_id=provenance["platform_listing_id"],
                observation_id=provenance["observation_id"],
                checkout_group_id=allocation["checkout_group_id"],
                evidence_snapshot=provenance,
            ))


def _run_planner(request: Request, request_id: str, items: list[Any]) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    exact = [
        item for item in items
        if item.resolution_status == "exact_confirmed"
        and item.canonical_product_id and item.canonical_variant_id
    ]
    if len(exact) != len(items):
        unresolved = [str(item.id) for item in items if item not in exact]
        return "unresolved", {"unresolved_item_ids": unresolved, "offers": [], "observed_listing_prices": []}, None
    if not items:
        return "no_plan", {"unresolved_item_ids": [], "offers": [], "observed_listing_prices": []}, None

    runtime = request.app.state.product_intelligence_runtime
    requested_items = []
    for item in items:
        product = runtime.catalog.get_product(item.canonical_product_id)
        variant = runtime.catalog.get_variant(item.canonical_variant_id)
        if (
            product is None or variant is None
            or variant.canonical_product_id != product.canonical_product_id
            or product.product_identity_status.value != "established"
            or product.lifecycle_status.value != "active"
            or variant.variant_identity_status.value != "established"
            or variant.lifecycle_status.value != "active"
            or variant.pack_configuration.pack_configuration_status != "complete"
        ):
            return "unresolved", {"unresolved_item_ids": [str(item.id)], "offers": [], "observed_listing_prices": []}, None
        requested_items.append({
            "item_id": str(item.id),
            "query": item.query,
            "quantity": item.quantity,
            "canonical_product_id": product.canonical_product_id,
            "canonical_variant_id": variant.canonical_variant_id,
            "canonical_product_revision": product.catalog_revision,
            "canonical_variant_revision": variant.catalog_revision,
        })

    status_value = "unavailable"
    optimizer_json = None
    explanation = "The current planner has no complete current checkout evidence; observed listing prices are not payable totals."
    try:
        planned = request.app.state.automatic_cart_planning.plan(AutomaticPlanningRequest(
            cart_id=request_id,
            items=tuple(AutomaticCartItem(
                item_id=str(item.id),
                canonical_product_id=item.canonical_product_id,
                canonical_variant_id=item.canonical_variant_id,
                quantity=item.quantity,
            ) for item in exact),
        ))
        optimizer = planned.optimization_result
        optimizer_json = optimizer.model_dump(mode="json") if optimizer is not None else None
        if optimizer is not None and optimizer.outcome is OptimizationOutcome.SELECTED and planned.status is AutomaticPlanningStatus.READY:
            status_value = "ready"
            explanation = "A plan was selected using the configured checkout-cost evidence. Listing observations remain separate from payable checkout cost."
        elif optimizer is not None and optimizer.outcome is OptimizationOutcome.INFEASIBLE:
            status_value = "infeasible"
            explanation = "; ".join(optimizer.rationale or optimizer.rejection_reasons) or "No feasible plan was selected."
        elif planned.status is AutomaticPlanningStatus.UNRESOLVED:
            status_value = "unresolved"
            explanation = "; ".join(planned.unresolved_reasons) or "The planner could not resolve a complete plan."
        else:
            status_value = "unavailable"
            explanation = "; ".join(planned.unresolved_reasons) or explanation
    except PlanningProviderUnavailable as exc:
        explanation = str(exc)

    return status_value, {
        "requested_items": requested_items,
        "unresolved_item_ids": [] if status_value in {"ready", "infeasible"} else [str(item.id) for item in items],
        "offers": [],
        "observed_listing_prices": [],
        "explanation": explanation,
    }, optimizer_json


@router.post("", response_model=OptimizationResponse, status_code=status.HTTP_201_CREATED)
def create_optimization(
    payload: OptimizationCreate,
    request: Request,
    response: Response,
    principal: ConsumerPrincipal = Depends(csrf_protected),
    db: Session = Depends(get_db),
):
    key = idempotency_key(request)
    if key is None:
        raise HTTPException(status_code=400, detail={"code": "idempotency_key_required"})
    claimed = claim(
        db,
        user_id=principal.user.id,
        operation="optimization.create",
        key=key,
        payload=payload.model_dump(mode="json"),
        ttl_seconds=request.app.state.settings.idempotency_ttl_seconds,
    )
    if claimed.is_replay:
        response.status_code = claimed.status_code or status.HTTP_201_CREATED
        return JSONResponse(status_code=claimed.status_code, content=claimed.response_body)

    shopping_list = _owned_list(db, principal.user.id, payload.list_id, lock=True)
    if shopping_list.archived_at is not None:
        raise HTTPException(status_code=409, detail={"code": "shopping_list_archived"})
    if shopping_list.revision != payload.expected_revision:
        raise HTTPException(status_code=409, detail={
            "code": "stale_list_revision",
            "current_revision": shopping_list.revision,
        })
    items = sorted(shopping_list.items, key=lambda item: str(item.id))
    policy_version = request.app.state.settings.optimization_policy_version
    input_snapshot = {
        "user_id": str(principal.user.id),
        "list_id": str(shopping_list.id),
        "list_revision": shopping_list.revision,
        "items": [{
            "id": str(item.id),
            "query": item.query,
            "quantity": item.quantity,
            "resolution_status": item.resolution_status,
            "canonical_product_id": item.canonical_product_id,
            "canonical_variant_id": item.canonical_variant_id,
            "source_platform": item.source_platform,
            "source_listing_id": item.source_listing_id,
            "source_observation_id": item.source_observation_id,
        } for item in items],
        "policy_version": policy_version,
    }
    input_digest = hashlib.sha256(json.dumps(input_snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    request_id = "consumer-opt-" + hashlib.sha256(
        f"{principal.user.id}:{shopping_list.id}:{shopping_list.revision}:{input_digest}:{policy_version}".encode()
    ).hexdigest()[:32]

    existing = db.scalar(select(OptimizationRequestRecord).where(
        OptimizationRequestRecord.user_id == principal.user.id,
        OptimizationRequestRecord.request_id == request_id,
    ))
    if existing is not None:
        if existing.input_digest != input_digest:
            raise HTTPException(status_code=409, detail={"code": "optimization_identity_conflict"})
        result = _response(existing)
        complete(claimed, status_code=status.HTTP_200_OK, response_body=result.model_dump(mode="json"))
        db.commit()
        response.status_code = status.HTTP_200_OK
        return result

    run_status, result_data, optimizer_json = _run_planner(request, request_id, items)
    record = OptimizationRequestRecord(
        user_id=principal.user.id,
        shopping_list_id=shopping_list.id,
        request_id=request_id,
        list_revision=shopping_list.revision,
        input_digest=input_digest,
        policy_version=policy_version,
        status=run_status,
        input_snapshot=input_snapshot,
        result_snapshot={**result_data, "optimizer_result": optimizer_json},
    )
    db.add(record)
    db.flush()
    _persist_plans(db, record, optimizer_json)
    db.flush()
    result = _response(record)
    complete(claimed, status_code=status.HTTP_201_CREATED, response_body=result.model_dump(mode="json"))
    db.commit()
    return result


@router.get("/{request_id}", response_model=OptimizationResponse)
def get_optimization(
    request_id: str,
    principal: ConsumerPrincipal = Depends(current_consumer),
    db: Session = Depends(get_db),
):
    record = db.scalar(select(OptimizationRequestRecord).where(
        OptimizationRequestRecord.request_id == request_id,
        OptimizationRequestRecord.user_id == principal.user.id,
    ))
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "optimization_not_found"})
    return _response(record)
