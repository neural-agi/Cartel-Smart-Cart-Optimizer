"""Authenticated, immutable optimization runs over a shopping-list revision."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.v2.dependencies import ConsumerPrincipal, current_consumer, csrf_protected
from app.cart_optimization.automatic_planning import AutomaticCartItem, AutomaticPlanningRequest, AutomaticPlanningStatus
from app.cart_optimization.providers import PlanningProviderUnavailable
from app.db.models import (
    OptimizationAllocationRecord,
    OptimizationPlanRecord,
    OptimizationRequestRecord,
    ShoppingList,
)
from app.db.session import get_db
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryItemRequest,
    CartCandidateDiscoveryRequest,
    PersistedCandidateReadiness,
)
from app.services.idempotency import claim, complete, idempotency_key


router = APIRouter(prefix="/optimizations", tags=["consumer-optimizations"])


class OptimizationCreate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    list_id: UUID
    expected_revision: int = Field(ge=1)


class OptimizationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    list_id: UUID
    list_revision: int
    input_digest: str
    policy_version: str
    status: Literal["ready", "unresolved", "unavailable", "infeasible", "no_plan"]
    completeness: Literal["complete", "partial", "unavailable"]
    created_at: datetime | None = None
    requested_items: tuple[dict[str, Any], ...] = ()
    offers: tuple[dict[str, Any], ...] = ()
    unresolved_items: tuple[dict[str, Any], ...] = ()
    optimizer_result: dict[str, Any] | None = None
    explanation: str


def _list_or_404(db: Session, user_id: UUID, list_id: UUID, *, lock: bool = False) -> ShoppingList:
    query = select(ShoppingList).where(
        ShoppingList.id == list_id,
        ShoppingList.user_id == user_id,
    ).options(selectinload(ShoppingList.items))
    if lock:
        query = query.with_for_update()
    result = db.scalar(query)
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "shopping_list_not_found"})
    return result


def _response(record: OptimizationRequestRecord) -> OptimizationResponse:
    data = record.result_snapshot
    return OptimizationResponse(
        request_id=record.request_id,
        list_id=record.shopping_list_id,
        list_revision=record.list_revision,
        input_digest=record.input_digest,
        policy_version=record.policy_version,
        status=record.status,
        completeness=data["completeness"],
        created_at=record.created_at,
        requested_items=tuple(data["requested_items"]),
        offers=tuple(data["offers"]),
        unresolved_items=tuple(data["unresolved_items"]),
        optimizer_result=data.get("optimizer_result"),
        explanation=data["explanation"],
    )


def _persist_plan_rows(db: Session, record: OptimizationRequestRecord, result: dict, items: dict[str, Any]) -> None:
    optimizer = result.get("optimizer_result")
    if not optimizer:
        return
    plans: list[tuple[dict[str, Any], bool, int | None]] = []
    chosen = optimizer.get("chosen_plan")
    if chosen:
        plans.append((chosen, True, 0))
    plans.extend((plan, False, index + 1) for index, plan in enumerate(optimizer.get("alternative_plans", [])))
    for rejected in optimizer.get("rejected_plans", []):
        plans.append((rejected, False, None))
    for plan, selected, rank in plans:
        plan_id = plan["plan_id"]
        row = OptimizationPlanRecord(
            request_record_id=record.id,
            user_id=record.user_id,
            plan_id=plan_id,
            feasibility=plan.get("feasibility", "rejected"),
            ranking_position=rank,
            selected=selected,
            plan_snapshot=plan,
        )
        db.add(row)
        db.flush()
        for allocation in plan.get("candidate_item_allocations", []):
            item = items.get(allocation["item_id"])
            provenance = allocation["listing_provenance"]
            db.add(OptimizationAllocationRecord(
                plan_record_id=row.id,
                user_id=record.user_id,
                item_id_snapshot=allocation["item_id"],
                canonical_product_id=item.canonical_product_id,
                canonical_variant_id=allocation["canonical_variant_id"],
                quantity=allocation["quantity"],
                retailer_id=allocation["retailer_id"],
                platform=provenance["platform"],
                platform_listing_id=provenance["platform_listing_id"],
                observation_id=provenance["observation_id"],
                checkout_group_id=allocation["checkout_group_id"],
                evidence_snapshot=provenance,
            ))


@router.post("", response_model=OptimizationResponse, status_code=201)
def create_optimization(
    payload: OptimizationCreate,
    request: Request,
    response: Response,
    principal: ConsumerPrincipal = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> OptimizationResponse:
    shopping_list = _list_or_404(db, principal.user.id, payload.list_id, lock=True)
    if shopping_list.archived_at is not None:
        raise HTTPException(status_code=409, detail={"code": "shopping_list_archived"})
    if shopping_list.revision != payload.expected_revision:
        raise HTTPException(status_code=409, detail={"code": "stale_list_revision", "current_revision": shopping_list.revision})

    replay = claim(
        db,
        user_id=principal.user.id,
        operation="optimization.create",
        key=idempotency_key(request),
        payload=payload.model_dump(mode="json"),
        ttl_seconds=request.app.state.settings.idempotency_ttl_seconds,
    )
    if replay is not None and replay.status_code:
        return JSONResponse(status_code=replay.status_code, content=replay.response_body)

    settings = request.app.state.settings
    policy_version = settings.optimization_policy_version
    list_items = sorted(shopping_list.items, key=lambda item: str(item.id))
    catalog = request.app.state.product_intelligence_runtime.catalog
    requested = []
    for item in list_items:
        product = catalog.get_product(item.canonical_product_id) if item.canonical_product_id else None
        variant = catalog.get_variant(item.canonical_variant_id) if item.canonical_variant_id else None
        requested.append({
            "item_id": str(item.id), "query": item.query, "quantity": item.quantity,
            "resolution_status": item.resolution_status,
            "canonical_product_id": item.canonical_product_id,
            "canonical_variant_id": item.canonical_variant_id,
            "canonical_product_revision": product.catalog_revision if product else None,
            "canonical_variant_revision": variant.catalog_revision if variant else None,
            "source_platform": item.source_platform,
            "source_listing_id": item.source_listing_id,
            "source_observation_id": item.source_observation_id,
        })
    exact_items = [item for item in list_items if item.resolution_status == "exact_confirmed" and item.canonical_product_id and item.canonical_variant_id]
    discovery = request.app.state.cart_candidate_discovery.discover(CartCandidateDiscoveryRequest(items=tuple(
        CartCandidateDiscoveryItemRequest(
            item_id=str(item.id), quantity=item.quantity,
            canonical_product_id=item.canonical_product_id,
            canonical_variant_id=item.canonical_variant_id,
        ) for item in exact_items
    ))) if exact_items else None

    offers: list[dict[str, Any]] = []
    item_status: dict[str, str] = {}
    if discovery:
        for found in discovery.items:
            item_status[found.item_id] = found.status.value
            for candidate in found.candidates:
                if candidate.readiness is not PersistedCandidateReadiness.ready_for_allocation:
                    continue
                price = candidate.observation.observed_selling_price
                retailer_id = None
                try:
                    retailer_id = request.app.state.planning_retailer_provider.retailer_id(
                        item_id=found.item_id,
                        platform=candidate.platform,
                        listing_id=candidate.platform_listing_id,
                    )
                except PlanningProviderUnavailable:
                    pass
                product = catalog.get_product(found.canonical_product_id)
                variant = catalog.get_variant(found.canonical_variant_id)
                offers.append({
                    "item_id": found.item_id,
                    "canonical_product_id": found.canonical_product_id,
                    "canonical_variant_id": found.canonical_variant_id,
                    "quantity": found.quantity,
                    "platform": candidate.platform,
                    "retailer_id": retailer_id,
                    "platform_listing_id": candidate.platform_listing_id,
                    "observation_id": candidate.observation_id,
                    "observed_unit_price": {"currency": price.currency, "minor_units": price.minor_units},
                    "observed_product_subtotal": {"currency": price.currency, "minor_units": price.minor_units * found.quantity},
                    "observed_at": candidate.observation.raw_artifact_reference.capture_timestamp.isoformat(),
                    "parser_version": candidate.observation.parser_version,
                    "normalization_version": candidate.observation.normalization_version,
                    "availability": candidate.observation.availability_signal,
                    "observation_state": "latest_governed_observation",
                    "source_reference": candidate.observation.raw_artifact_reference.source_reference,
                    "raw_content_digest": candidate.observation.raw_artifact_reference.content_digest,
                    "canonical_product_revision": product.catalog_revision,
                    "canonical_variant_revision": variant.catalog_revision,
                })

    snapshot = {
        "user_id": str(principal.user.id),
        "list_id": str(shopping_list.id),
        "list_revision": shopping_list.revision,
        "requested_items": requested,
        "offers": sorted(offers, key=lambda offer: (offer["item_id"], offer["platform"], offer["platform_listing_id"], offer["observation_id"])),
        "policy_version": policy_version,
        "policy_context_digest": hashlib.sha256(json.dumps({
            "retailer_map": settings.planning_retailer_identity_map,
            "checkout_group_map": settings.planning_checkout_group_map,
            "feasibility": settings.planning_feasibility,
            "feasibility_evidence": settings.planning_feasibility_evidence,
            "inconvenience_penalty_units": settings.planning_inconvenience_penalty_units,
            "retailer_preference_priority": settings.planning_retailer_preference_priority,
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    request_id = "consumer-opt-" + hashlib.sha256(f"{principal.user.id}:{shopping_list.id}:{shopping_list.revision}:{digest}:{policy_version}".encode()).hexdigest()[:32]

    existing = db.scalar(select(OptimizationRequestRecord).where(
        OptimizationRequestRecord.user_id == principal.user.id,
        OptimizationRequestRecord.request_id == request_id,
    ))
    if existing:
        if existing.input_digest != digest:
            raise HTTPException(status_code=409, detail={"code": "optimization_identity_conflict"})
        response.status_code = 200
        result = _response(existing)
        complete(replay, status_code=200, response_body=result.model_dump(mode="json"))
        db.commit()
        return result

    unresolved_items = [item for item in requested if item["resolution_status"] != "exact_confirmed" or item_status.get(item["item_id"]) != "candidates_available"]
    status = "no_plan" if not requested else "unresolved" if unresolved_items else "unavailable"
    optimizer_result = None
    explanation = (
        "The shopping list revision contains no requested items; no plan was generated."
        if not requested else
        "One or more requested items lack exact, current governed retailer offers. No complete allocation was claimed."
        if unresolved_items else
        "Governed observed prices are available, but no correlated checkout ECE is available. They are not payable totals."
    )
    completeness = "partial" if offers and unresolved_items else "unavailable" if not offers else "complete"

    if not unresolved_items and offers:
        try:
            planned = request.app.state.consumer_automatic_planning.plan(AutomaticPlanningRequest(
                cart_id=request_id,
                items=tuple(AutomaticCartItem(
                    item_id=str(item.id), canonical_product_id=item.canonical_product_id,
                    canonical_variant_id=item.canonical_variant_id, quantity=item.quantity,
                ) for item in exact_items),
            ))
            if planned.optimization_result is not None:
                optimizer_result = planned.optimization_result.model_dump(mode="json")
            if (
                planned.optimization_result is not None
                and planned.optimization_result.outcome.value == "selected"
                and planned.status is not AutomaticPlanningStatus.READY
            ):
                optimizer_result = None
                status = "unresolved"
                explanation = "Planning status conflicted with a selected optimizer result; the result was withheld."
            elif (
                planned.status is AutomaticPlanningStatus.READY
                and planned.optimization_result is not None
                and planned.optimization_result.outcome.value == "selected"
                and planned.optimization_result.chosen_plan is not None
            ):
                status = "ready"
                explanation = "The existing optimizer selected a plan backed by its correlated checkout ECE. Observed listing prices remain separate from checkout cost."
            elif planned.optimization_result is not None and planned.optimization_result.outcome.value == "infeasible":
                status = "infeasible"
                explanation = "; ".join(planned.optimization_result.rationale or planned.optimization_result.rejection_reasons) or "No candidate plan satisfies the configured constraints."
            elif planned.status is AutomaticPlanningStatus.UNRESOLVED:
                status = "unresolved"
                explanation = "; ".join(planned.unresolved_reasons) or "The optimizer did not select a plan."
            elif planned.status is AutomaticPlanningStatus.READY:
                status = "unresolved"
                explanation = "The planning service reported ready without a selected optimizer result; no successful plan is exposed."
            else:
                status = "unavailable"
                explanation = "; ".join(planned.unresolved_reasons) or "Checkout evidence is unavailable."
        except PlanningProviderUnavailable as exc:
            status = "unavailable"
            explanation = str(exc)

    result_data = {
        "completeness": completeness,
        "requested_items": requested,
        "offers": snapshot["offers"],
        "unresolved_items": unresolved_items,
        "optimizer_result": optimizer_result,
        "explanation": explanation,
    }
    record = OptimizationRequestRecord(
        user_id=principal.user.id,
        shopping_list_id=shopping_list.id,
        request_id=request_id,
        list_revision=shopping_list.revision,
        input_digest=digest,
        policy_version=policy_version,
        status=status,
        input_snapshot=snapshot,
        result_snapshot=result_data,
    )
    db.add(record)
    db.flush()
    if optimizer_result:
        _persist_plan_rows(db, record, result_data, {str(item.id): item for item in exact_items})
    db.refresh(record)
    result = _response(record)
    complete(replay, status_code=201, response_body=result.model_dump(mode="json"))
    db.commit()
    return result


@router.get("/{request_id}", response_model=OptimizationResponse)
def get_optimization(
    request_id: str,
    principal: ConsumerPrincipal = Depends(current_consumer),
    db: Session = Depends(get_db),
) -> OptimizationResponse:
    record = db.scalar(select(OptimizationRequestRecord).where(
        OptimizationRequestRecord.user_id == principal.user.id,
        OptimizationRequestRecord.request_id == request_id,
    ))
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "optimization_not_found"})
    return _response(record)
