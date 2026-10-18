from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies.consumer import ConsumerPrincipal, current_consumer, csrf_protected
from app.db.models import AuditEvent, ShoppingList, ShoppingListItem
from app.db.session import get_db
from app.schemas.shopping_lists import (
    ShoppingListCreate,
    ShoppingListItemCreate,
    ShoppingListItemResponse,
    ShoppingListItemUpdate,
    ShoppingListResponse,
    ShoppingListUpdate,
)
from app.services.idempotency import claim, complete, idempotency_key


router = APIRouter(prefix="/lists", tags=["shopping-lists"])


def _response(shopping_list: ShoppingList) -> ShoppingListResponse:
    return ShoppingListResponse(
        id=shopping_list.id,
        name=shopping_list.name,
        revision=shopping_list.revision,
        archived=shopping_list.archived_at is not None,
        created_at=shopping_list.created_at,
        updated_at=shopping_list.updated_at,
        items=tuple(
            ShoppingListItemResponse(
                id=item.id,
                query=item.query,
                quantity=item.quantity,
                unit=item.unit,
                resolution_status=item.resolution_status,
                canonical_product_id=item.canonical_product_id,
                canonical_variant_id=item.canonical_variant_id,
                display_name=item.display_name_snapshot,
                source_platform=item.source_platform,
                source_listing_id=item.source_listing_id,
                source_observation_id=item.source_observation_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in shopping_list.items
        ),
    )


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


def _ensure_active(shopping_list: ShoppingList) -> None:
    if shopping_list.archived_at is not None:
        raise HTTPException(status_code=409, detail={"code": "shopping_list_archived"})


def _audit(db: Session, user_id: UUID, event: str, object_id: UUID, request_id: str | None) -> None:
    db.add(AuditEvent(
        user_id=user_id,
        event_type=event,
        object_type="shopping_list",
        object_id=str(object_id),
        request_id=request_id,
    ))


def _claim(request: Request, db: Session, user_id: UUID, operation: str, key_payload: object):
    key = idempotency_key(request)
    if key is None:
        raise HTTPException(status_code=400, detail={"code": "idempotency_key_required"})
    return claim(
        db,
        user_id=user_id,
        operation=operation,
        key=key,
        payload=key_payload,
        ttl_seconds=request.app.state.settings.idempotency_ttl_seconds,
    )


def _replay(claim_result):
    if claim_result.is_replay:
        return JSONResponse(status_code=claim_result.status_code, content=claim_result.response_body)
    return None


@router.get("", response_model=tuple[ShoppingListResponse, ...])
def get_lists(principal: ConsumerPrincipal = Depends(current_consumer), db: Session = Depends(get_db)):
    lists = db.scalars(
        select(ShoppingList)
        .where(ShoppingList.user_id == principal.user.id)
        .options(selectinload(ShoppingList.items))
        .order_by(ShoppingList.updated_at.desc(), ShoppingList.id)
    ).all()
    return tuple(_response(item) for item in lists)


@router.post("", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
def create_list(
    payload: ShoppingListCreate,
    request: Request,
    principal: ConsumerPrincipal = Depends(csrf_protected),
    db: Session = Depends(get_db),
):
    operation = "shopping_list.create"
    claimed = _claim(request, db, principal.user.id, operation, payload.model_dump(mode="json"))
    replay = _replay(claimed)
    if replay is not None:
        return replay
    shopping_list = ShoppingList(user_id=principal.user.id, name=payload.name)
    db.add(shopping_list)
    db.flush()
    _audit(db, principal.user.id, "shopping_list_created", shopping_list.id, request.state.request_id)
    db.refresh(shopping_list)
    result = _response(shopping_list)
    complete(claimed, status_code=status.HTTP_201_CREATED, response_body=result.model_dump(mode="json"))
    db.commit()
    return result


@router.get("/{list_id}", response_model=ShoppingListResponse)
def get_list(list_id: UUID, principal: ConsumerPrincipal = Depends(current_consumer), db: Session = Depends(get_db)):
    return _response(_owned_list(db, principal.user.id, list_id))


@router.patch("/{list_id}", response_model=ShoppingListResponse)
def update_list(
    list_id: UUID,
    payload: ShoppingListUpdate,
    request: Request,
    principal: ConsumerPrincipal = Depends(csrf_protected),
    db: Session = Depends(get_db),
):
    operation = "shopping_list.update"
    claimed = _claim(
        request, db, principal.user.id, operation,
        {"list_id": str(list_id), **payload.model_dump(mode="json")},
    )
    replay = _replay(claimed)
    if replay is not None:
        return replay
    shopping_list = _owned_list(db, principal.user.id, list_id, lock=True)
    if payload.name is not None:
        shopping_list.name = payload.name
    if payload.archived is not None:
        shopping_list.archived_at = datetime.now(timezone.utc) if payload.archived else None
    shopping_list.revision += 1
    _audit(db, principal.user.id, "shopping_list_updated", shopping_list.id, request.state.request_id)
    result = _response(shopping_list)
    complete(claimed, status_code=status.HTTP_200_OK, response_body=result.model_dump(mode="json"))
    db.commit()
    return result


@router.post("/{list_id}/items", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
def add_item(
    list_id: UUID,
    payload: ShoppingListItemCreate,
    request: Request,
    principal: ConsumerPrincipal = Depends(csrf_protected),
    db: Session = Depends(get_db),
):
    operation = "shopping_list.add_item"
    claimed = _claim(
        request, db, principal.user.id, operation,
        {"list_id": str(list_id), **payload.model_dump(mode="json")},
    )
    replay = _replay(claimed)
    if replay is not None:
        return replay
    shopping_list = _owned_list(db, principal.user.id, list_id, lock=True)
    _ensure_active(shopping_list)
    display_name = None
    if payload.canonical_product_id is not None:
        runtime = request.app.state.product_intelligence_runtime
        product = runtime.catalog.get_product(payload.canonical_product_id)
        variant = runtime.catalog.get_variant(payload.canonical_variant_id)
        association = next((
            candidate for candidate in runtime.association_registry.all()
            if candidate.platform == payload.source_platform
            and candidate.platform_listing_id == payload.source_listing_id
            and candidate.observation_id == payload.source_observation_id
        ), None)
        observation = runtime.observation_registry.get(payload.source_observation_id)
        observations = [
            runtime.observation_registry.get(candidate.observation_id)
            for candidate in runtime.association_registry.all()
            if candidate.platform == payload.source_platform
            and candidate.platform_listing_id == payload.source_listing_id
        ]
        observations = [candidate for candidate in observations if candidate is not None]
        newest_timestamp = max(
            (candidate.raw_artifact_reference.capture_timestamp for candidate in observations),
            default=None,
        )
        if (
            product is None or variant is None
            or variant.canonical_product_id != product.canonical_product_id
            or product.product_identity_status.value != "established"
            or product.lifecycle_status.value != "active"
            or variant.variant_identity_status.value != "established"
            or variant.lifecycle_status.value != "active"
            or variant.pack_configuration.pack_configuration_status != "complete"
            or association is None
            or association.canonical_product_id != product.canonical_product_id
            or association.canonical_variant_id != variant.canonical_variant_id
            or observation is None
            or observation.observation_id != payload.source_observation_id
            or newest_timestamp is None
            or observation.raw_artifact_reference.capture_timestamp != newest_timestamp
            or observation.observed_selling_price is None
        ):
            raise HTTPException(status_code=409, detail={"code": "selected_product_evidence_stale"})
        display_name = product.canonical_display_name

    item = ShoppingListItem(
        list_id=shopping_list.id,
        user_id=principal.user.id,
        query=payload.query,
        quantity=payload.quantity,
        unit=payload.unit,
        resolution_status="exact_confirmed" if display_name else "unresolved",
        canonical_product_id=payload.canonical_product_id,
        canonical_variant_id=payload.canonical_variant_id,
        display_name_snapshot=display_name,
        source_platform=payload.source_platform,
        source_listing_id=payload.source_listing_id,
        source_observation_id=payload.source_observation_id,
    )
    shopping_list.items.append(item)
    shopping_list.revision += 1
    _audit(db, principal.user.id, "shopping_list_item_added", shopping_list.id, request.state.request_id)
    db.flush()
    result = _response(shopping_list)
    complete(claimed, status_code=status.HTTP_201_CREATED, response_body=result.model_dump(mode="json"))
    db.commit()
    return result

@router.patch("/{list_id}/items/{item_id}", response_model=ShoppingListResponse)
def update_item(
    list_id: UUID,
    item_id: UUID,
    payload: ShoppingListItemUpdate,
    request: Request,
    principal: ConsumerPrincipal = Depends(csrf_protected),
    db: Session = Depends(get_db),
):
    operation = "shopping_list.update_item"
    claimed = _claim(
        request, db, principal.user.id, operation,
        {"list_id": str(list_id), "item_id": str(item_id), **payload.model_dump(mode="json")},
    )
    replay = _replay(claimed)
    if replay is not None:
        return replay
    shopping_list = _owned_list(db, principal.user.id, list_id, lock=True)
    _ensure_active(shopping_list)
    item = next((candidate for candidate in shopping_list.items if candidate.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "shopping_list_item_not_found"})
    item.quantity = payload.quantity
    shopping_list.revision += 1
    _audit(db, principal.user.id, "shopping_list_item_updated", shopping_list.id, request.state.request_id)
    result = _response(shopping_list)
    complete(claimed, status_code=status.HTTP_200_OK, response_body=result.model_dump(mode="json"))
    db.commit()
    return result


@router.delete("/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    list_id: UUID,
    item_id: UUID,
    request: Request,
    principal: ConsumerPrincipal = Depends(csrf_protected),
    db: Session = Depends(get_db),
):
    operation = "shopping_list.remove_item"
    claimed = _claim(
        request, db, principal.user.id, operation,
        {"list_id": str(list_id), "item_id": str(item_id)},
    )
    replay = _replay(claimed)
    if replay is not None:
        return replay
    shopping_list = _owned_list(db, principal.user.id, list_id, lock=True)
    _ensure_active(shopping_list)
    item = next((candidate for candidate in shopping_list.items if candidate.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "shopping_list_item_not_found"})
    db.delete(item)
    shopping_list.revision += 1
    _audit(db, principal.user.id, "shopping_list_item_removed", shopping_list.id, request.state.request_id)
    result = Response(status_code=status.HTTP_204_NO_CONTENT)
    complete(claimed, status_code=status.HTTP_204_NO_CONTENT, response_body={})
    db.commit()
    return result
