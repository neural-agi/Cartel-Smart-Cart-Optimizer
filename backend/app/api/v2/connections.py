"""Owner-scoped HTTP API for retailer connection lifecycle metadata.

This module exposes only connection management. It never authenticates to a
retailer, never starts an OAuth flow, never opens a browser session, and never
retrieves, rotates, or returns credential material. The credential vault is used
solely to revoke active secrets when the owner disconnects.

Ownership is always derived from the authenticated Cartel session. No endpoint
accepts a ``user_id`` in a path or body, and every domain call is owner-scoped.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.v2.dependencies import ConsumerPrincipal, csrf_protected, current_consumer
from app.core.logging import get_logger
from app.credential_vault.service import CredentialVault
from app.credential_vault.types import (
    CredentialVaultError,
    SecretOwner,
    SecretStateConflict,
    SecretStatus,
)
from app.db.models.retailer_connections import RetailerConnection
from app.db.session import get_db
from app.retailer_connections import lifecycle, service
from app.retailer_policy import is_blinkit
from app.schemas.retailer_connections import (
    RetailerConnectionCapabilities,
    RetailerConnectionCreate,
    RetailerConnectionResponse,
)

router = APIRouter(prefix="/connections", tags=["retailer-connections"])

logger = get_logger(__name__)

_NOT_FOUND = {"code": "retailer_connection_not_found"}

# Statuses in which the lifecycle table allows the connection to be moved into
# REAUTH_REQUIRED. BLOCKED, REVOKED, and DISCONNECTED are excluded by policy.
_REAUTHORIZABLE_STATES = frozenset(
    {
        lifecycle.RetailerConnectionStatus.PENDING_AUTH,
        lifecycle.RetailerConnectionStatus.CONNECTED,
        lifecycle.RetailerConnectionStatus.DEGRADED,
    }
)

_AUTHENTICATED_STATES = frozenset(
    {
        lifecycle.RetailerConnectionStatus.CONNECTED,
        lifecycle.RetailerConnectionStatus.DEGRADED,
    }
)

_CAPABILITY_OPERATIONS = (
    ("cartel_data_access", lifecycle.RetailerOperation.CARTEL_DATA_ACCESS),
    ("connection_metadata", lifecycle.RetailerOperation.CONNECTION_METADATA),
    ("retailer_health_check", lifecycle.RetailerOperation.RETAILER_HEALTH_CHECK),
    ("product_discovery", lifecycle.RetailerOperation.PRODUCT_DISCOVERY),
    (
        "price_availability_acquisition",
        lifecycle.RetailerOperation.PRICE_AVAILABILITY_ACQUISITION,
    ),
    ("cart_preparation", lifecycle.RetailerOperation.CART_PREPARATION),
    ("checkout", lifecycle.RetailerOperation.CHECKOUT),
)


def get_credential_vault(request: Request) -> CredentialVault:
    """Return the application-scoped vault.

    The vault is used for revocation only. With the default fail-closed key
    provider, revocation still works because it does not need key material.
    """

    return request.app.state.credential_vault


def _connection_status(connection: RetailerConnection) -> lifecycle.RetailerConnectionStatus:
    return lifecycle.RetailerConnectionStatus(connection.status)


def _authorize_metadata(connection: RetailerConnection) -> None:
    """Enforce the CONNECTION_METADATA cell for the persisted owner.

    The caller has already authenticated the Cartel session and loaded an
    owner-scoped row, so ``existing_authorization`` is explicit. ``DEFERRED``
    cells are therefore decided by that owner check, never granted by default.
    """

    status_value = _connection_status(connection)
    try:
        lifecycle.authorize_operation(
            status_value,
            lifecycle.RetailerOperation.CONNECTION_METADATA,
            existing_authorization=True,
        )
    except lifecycle.RetailerOperationDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "connection_metadata_denied"},
        ) from exc


def _response(connection: RetailerConnection) -> RetailerConnectionResponse:
    status_value = _connection_status(connection)
    policy_blocked = is_blinkit(connection.retailer_id)
    capabilities = RetailerConnectionCapabilities(
        **{
            name: False
            if policy_blocked
            else lifecycle.permission_for(status_value, operation)
            for name, operation in _CAPABILITY_OPERATIONS
        }
    )
    reported_status = (
        lifecycle.RetailerConnectionStatus.BLOCKED if policy_blocked else status_value
    )
    return RetailerConnectionResponse(
        id=connection.id,
        retailer_id=connection.retailer_id,
        status=reported_status,
        authentication_method=connection.authentication_method,
        connected_at=connection.connected_at,
        last_validated_at=connection.last_validated_at,
        reauthorization_required=(
            False
            if policy_blocked
            else status_value is lifecycle.RetailerConnectionStatus.REAUTH_REQUIRED
        ),
        capabilities=capabilities,
        cartel_account_authenticated=True,
        retailer_connection_exists=True,
        retailer_authenticated=(
            False if policy_blocked else status_value in _AUTHENTICATED_STATES
        ),
        retailer_operational=(
            False
            if policy_blocked
            else status_value is lifecycle.RetailerConnectionStatus.CONNECTED
        ),
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )


def _owned_connection(
    db: Session,
    principal: ConsumerPrincipal,
    connection_id: UUID,
) -> RetailerConnection:
    try:
        return service.get_connection(
            db,
            user_id=principal.user.id,
            connection_id=connection_id,
        )
    except lifecycle.RetailerConnectionNotFound as exc:
        # Another user's record and a nonexistent record are indistinguishable.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_NOT_FOUND,
        ) from exc


def _revoke_active_secrets(
    db: Session,
    vault: CredentialVault,
    connection: RetailerConnection,
    request_id: str | None,
) -> None:
    """Revoke every ACTIVE secret lineage bound to this connection.

    Revocation preserves audit evidence; it does not delete or crypto-shred.
    The lifecycle state already denies retailer operations, so a revocation
    failure cannot re-enable retrieval. The loop tolerates a concurrent
    rotation by re-reading the active set a bounded number of times.
    """

    owner = SecretOwner(
        user_id=connection.user_id,
        connection_id=connection.id,
        retailer_id=connection.retailer_id,
    )
    for _ in range(3):
        active = [
            metadata
            for metadata in vault.list_metadata(db, owner=owner)
            if metadata.status == SecretStatus.ACTIVE
        ]
        if not active:
            return
        for metadata in active:
            try:
                vault.revoke(
                    db,
                    owner=owner,
                    reference=metadata.reference,
                    request_id=request_id,
                )
            except SecretStateConflict:
                # Another writer changed the row between listing and locking.
                continue


@router.post(
    "",
    response_model=RetailerConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_connection(
    payload: RetailerConnectionCreate,
    request: Request,
    principal: ConsumerPrincipal = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> RetailerConnectionResponse:
    """Create one PENDING_AUTH connection for the authenticated user.

    This does not authenticate to the retailer and does not imply success.
    """

    try:
        connection = service.create_pending_connection(
            db,
            user_id=principal.user.id,
            retailer_id=payload.retailer_id,
            request_id=request.state.request_id,
        )
    except lifecycle.RetailerConnectionAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "retailer_connection_exists"},
        ) from exc
    except lifecycle.InvalidRetailerConnectionInput as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_retailer_connection_input"},
        ) from exc
    return _response(connection)


@router.get("", response_model=tuple[RetailerConnectionResponse, ...])
def list_connections(
    principal: ConsumerPrincipal = Depends(current_consumer),
    db: Session = Depends(get_db),
) -> tuple[RetailerConnectionResponse, ...]:
    """List only the authenticated user's connections, newest first."""

    connections = service.list_connections(db, user_id=principal.user.id)
    for connection in connections:
        _authorize_metadata(connection)
    return tuple(_response(connection) for connection in connections)


@router.get("/{connection_id}", response_model=RetailerConnectionResponse)
def get_connection(
    connection_id: UUID,
    principal: ConsumerPrincipal = Depends(current_consumer),
    db: Session = Depends(get_db),
) -> RetailerConnectionResponse:
    """Return one owner-scoped connection or an indistinguishable 404."""

    connection = _owned_connection(db, principal, connection_id)
    _authorize_metadata(connection)
    return _response(connection)


@router.post(
    "/{connection_id}/reauthorize",
    response_model=RetailerConnectionResponse,
)
def initiate_reauthorization(
    connection_id: UUID,
    request: Request,
    principal: ConsumerPrincipal = Depends(csrf_protected),
    db: Session = Depends(get_db),
) -> RetailerConnectionResponse:
    """Move the connection into REAUTH_REQUIRED.

    This records that reauthorization is required. It does not attempt retailer
    authentication and can never transition to CONNECTED. A repeat request is an
    idempotent no-op that emits no additional audit event.
    """

    connection = _owned_connection(db, principal, connection_id)
    _authorize_metadata(connection)
    current = _connection_status(connection)
    if current is lifecycle.RetailerConnectionStatus.REAUTH_REQUIRED:
        return _response(connection)
    if current not in _REAUTHORIZABLE_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "reauthorization_not_available"},
        )

    try:
        connection = service.transition(
            db,
            user_id=principal.user.id,
            connection_id=connection_id,
            to_state=lifecycle.RetailerConnectionStatus.REAUTH_REQUIRED,
            reason=lifecycle.RetailerConnectionReason.AUTH_FAILED,
            request_id=request.state.request_id,
        )
    except lifecycle.RetailerConnectionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_NOT_FOUND,
        ) from exc
    except (
        lifecycle.InvalidRetailerConnectionTransition,
        lifecycle.RetailerOperationDenied,
        lifecycle.RetailerConnectionConflict,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "reauthorization_not_available"},
        ) from exc
    return _response(connection)


@router.post(
    "/{connection_id}/disconnect",
    response_model=RetailerConnectionResponse,
)
def disconnect_connection(
    connection_id: UUID,
    request: Request,
    principal: ConsumerPrincipal = Depends(csrf_protected),
    db: Session = Depends(get_db),
    vault: CredentialVault = Depends(get_credential_vault),
) -> RetailerConnectionResponse:
    """Disconnect the owner's connection and revoke its active secrets.

    The lifecycle transition is validated first. A repeat disconnect is an
    idempotent no-op and still attempts to revoke any remaining active secret.
    REVOKED is terminal and cannot be disconnected.
    """

    connection = _owned_connection(db, principal, connection_id)
    _authorize_metadata(connection)
    if _connection_status(connection) is lifecycle.RetailerConnectionStatus.REVOKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "connection_not_disconnectable"},
        )

    try:
        connection = service.disconnect(
            db,
            user_id=principal.user.id,
            connection_id=connection_id,
            request_id=request.state.request_id,
        )
    except lifecycle.RetailerConnectionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_NOT_FOUND,
        ) from exc
    except (
        lifecycle.InvalidRetailerConnectionTransition,
        lifecycle.RetailerOperationDenied,
        lifecycle.RetailerConnectionConflict,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "connection_not_disconnectable"},
        ) from exc

    try:
        _revoke_active_secrets(db, vault, connection, request.state.request_id)
    except CredentialVaultError:
        # The connection is already DISCONNECTED, which denies every retailer
        # operation. Log without exposing secret or vault details to the client.
        logger.exception(
            "credential_revocation_failed_after_disconnect",
            extra={"request_id": request.state.request_id, "component": "credential_vault"},
        )
    return _response(connection)
