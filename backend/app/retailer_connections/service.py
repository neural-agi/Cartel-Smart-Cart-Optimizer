"""Transactional service for retailer connection lifecycle operations.

Transaction boundaries follow the existing consumer services: the service takes
the row lock, validates against the declarative table, mutates the row, inserts
the audit event, and commits in one transaction. Callers receive typed errors
and never see a partially applied transition.

No method here authenticates to a retailer, stores credentials, or performs
acquisition. The external authorization reference is an opaque, non-secret
identifier supplied by a future authentication phase.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.data_ingestion.timestamp_integrity import Clock, SystemClock
from app.db.models import AuditEvent
from app.db.models.retailer_connections import RetailerConnection
from app.retailer_connections import lifecycle, repository
from app.retailer_policy import ensure_retailer_allowed
from app.retailer_connections.lifecycle import (
    AUTHENTICATION_METHOD_PATTERN,
    REFERENCE_PATTERN,
    SUPPORTED_RETAILER_IDS,
    InvalidRetailerConnectionInput,
    InvalidRetailerConnectionTransition,
    RestrictionCategory,
    RestrictionSource,
    RetailerConnectionAlreadyExists,
    RetailerConnectionConflict,
    RetailerConnectionNotFound,
    RetailerConnectionReason,
    RetailerConnectionStatus,
    RetailerOperation,
    RetailerOperationDenied,
)

# The audit payload is deliberately tiny and allowlisted. It never includes the
# external authorization reference, location reference, authentication method,
# or any caller-supplied free text.
AUDIT_PAYLOAD_FIELDS: frozenset[str] = frozenset(
    {
        "connection_id",
        "user_id",
        "retailer_id",
        "from_state",
        "to_state",
        "reason_code",
        "occurred_at",
    }
)

_ACTIVE_CONNECTION_INDEX = "uq_retailer_connections_active_user_retailer"


def _now(clock: Clock) -> datetime:
    value = clock.now()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _coerce_status(value: RetailerConnectionStatus | str) -> RetailerConnectionStatus:
    try:
        return RetailerConnectionStatus(value)
    except ValueError as exc:
        raise InvalidRetailerConnectionInput("invalid_status") from exc


def _coerce_reason(value: RetailerConnectionReason | str) -> RetailerConnectionReason:
    try:
        return RetailerConnectionReason(value)
    except ValueError as exc:
        raise InvalidRetailerConnectionInput("invalid_reason_code") from exc


def _coerce_restriction_source(
    value: RestrictionSource | str | None,
) -> RestrictionSource | None:
    if value is None:
        return None
    try:
        return RestrictionSource(value)
    except ValueError as exc:
        raise InvalidRetailerConnectionInput("invalid_restriction_source") from exc


def _coerce_restriction_category(
    value: RestrictionCategory | str | None,
) -> RestrictionCategory | None:
    if value is None:
        return None
    try:
        return RestrictionCategory(value)
    except ValueError as exc:
        raise InvalidRetailerConnectionInput("invalid_restriction_category") from exc


def _validate_retailer_id(value: str) -> None:
    if value not in SUPPORTED_RETAILER_IDS:
        raise InvalidRetailerConnectionInput("unsupported_retailer_id")
    try:
        ensure_retailer_allowed(value, "retailer connection")
    except RuntimeError as exc:
        raise InvalidRetailerConnectionInput("retailer_policy_blocked") from exc


def _validate_authentication_method(value: str | None) -> None:
    if value is not None and not AUTHENTICATION_METHOD_PATTERN.fullmatch(value):
        raise InvalidRetailerConnectionInput("invalid_authentication_method")


def _validate_reference(name: str, value: str | None) -> None:
    if value is not None and not REFERENCE_PATTERN.fullmatch(value):
        raise InvalidRetailerConnectionInput(f"invalid_{name}")


def _audit_payload(
    *,
    connection: RetailerConnection,
    from_state: RetailerConnectionStatus | None,
    to_state: RetailerConnectionStatus,
    reason: RetailerConnectionReason,
    occurred_at: datetime,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "connection_id": str(connection.id),
        "user_id": str(connection.user_id),
        "retailer_id": connection.retailer_id,
        "from_state": from_state.value if from_state is not None else None,
        "to_state": to_state.value,
        "reason_code": reason.value,
        "occurred_at": occurred_at.isoformat(),
    }
    if set(payload) != AUDIT_PAYLOAD_FIELDS:
        raise RuntimeError("retailer connection audit payload field allowlist violated")
    return payload


def _audit(
    db: Session,
    *,
    connection: RetailerConnection,
    from_state: RetailerConnectionStatus | None,
    to_state: RetailerConnectionStatus,
    reason: RetailerConnectionReason,
    occurred_at: datetime,
    event: str,
    request_id: str | None,
) -> None:
    db.add(
        AuditEvent(
            user_id=connection.user_id,
            event_type=event,
            object_type="retailer_connection",
            object_id=str(connection.id),
            request_id=request_id,
            payload=_audit_payload(
                connection=connection,
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                occurred_at=occurred_at,
            ),
        )
    )


def _is_unique_violation(exc: IntegrityError, constraint_name: str) -> bool:
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    if getattr(diag, "constraint_name", None) == constraint_name:
        return True
    return constraint_name in str(orig or exc)


def _apply(
    connection: RetailerConnection,
    spec: lifecycle.TransitionSpec,
    now: datetime,
    *,
    restriction_source: RestrictionSource | None = None,
    restriction_category: RestrictionCategory | None = None,
) -> None:
    connection.status = spec.to_state.value
    for field in spec.timestamps:
        # connected_at records the first time the connection reached CONNECTED.
        # Revalidation from DEGRADED/REAUTH_REQUIRED must never overwrite it.
        if field == "connected_at" and connection.connected_at is not None:
            continue
        setattr(connection, field, now)
    if spec.to_state is RetailerConnectionStatus.BLOCKED:
        # A BLOCKED record always carries controlled provenance. Leaving BLOCKED
        # (only to DISCONNECTED) retains it as historical metadata.
        connection.blocked_at = now
        connection.blocked_source = restriction_source.value  # type: ignore[union-attr]
        connection.blocked_category = restriction_category.value  # type: ignore[union-attr]
    connection.updated_at = now
    connection.version += 1


def _locked_owned(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    expected_version: int | None,
) -> RetailerConnection:
    connection = repository.get_owned(
        db,
        user_id=user_id,
        connection_id=connection_id,
        for_update=True,
    )
    if connection is None:
        db.rollback()
        raise RetailerConnectionNotFound(connection_id)
    if expected_version is not None and connection.version != expected_version:
        actual_version = connection.version
        db.rollback()
        raise RetailerConnectionConflict(
            connection_id=connection_id,
            expected_version=expected_version,
            actual_version=actual_version,
        )
    return connection


def _transition_locked(
    db: Session,
    connection: RetailerConnection,
    *,
    to_state: RetailerConnectionStatus,
    reason: RetailerConnectionReason,
    now: datetime,
    request_id: str | None,
    restriction_source: RestrictionSource | None = None,
    restriction_category: RestrictionCategory | None = None,
) -> RetailerConnection:
    if to_state is RetailerConnectionStatus.BLOCKED:
        if restriction_source is None or restriction_category is None:
            db.rollback()
            raise InvalidRetailerConnectionInput("blocked_requires_restriction")
    elif restriction_source is not None or restriction_category is not None:
        db.rollback()
        raise InvalidRetailerConnectionInput("restriction_metadata_only_for_blocked")

    from_state = _coerce_status(connection.status)
    spec = lifecycle.lookup(from_state, to_state, reason)
    if spec is None:
        db.rollback()
        raise InvalidRetailerConnectionTransition(
            from_state=from_state,
            to_state=to_state,
            reason=reason,
        )
    if spec.noop:
        # Same-state-same-reason repeat: return the current record with no
        # timestamp change, no version bump, and no audit event.
        db.commit()
        return connection
    _apply(
        connection,
        spec,
        now,
        restriction_source=restriction_source,
        restriction_category=restriction_category,
    )
    _audit(
        db,
        connection=connection,
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        occurred_at=now,
        event=spec.audit_event,
        request_id=request_id,
    )
    db.commit()
    db.refresh(connection)
    return connection


def create_pending_connection(
    db: Session,
    *,
    user_id: UUID,
    retailer_id: str,
    authentication_method: str | None = None,
    external_authorization_reference: str | None = None,
    retailer_location_reference: str | None = None,
    request_id: str | None = None,
    clock: Clock | None = None,
) -> RetailerConnection:
    """Create one PENDING_AUTH connection owned by ``user_id``.

    The partial unique index allows at most one non-terminal connection per
    user+retailer. A second create raises ``RetailerConnectionAlreadyExists``;
    after DISCONNECTED or REVOKED a new record may be created.
    """

    _validate_retailer_id(retailer_id)
    _validate_authentication_method(authentication_method)
    _validate_reference("external_authorization_reference", external_authorization_reference)
    _validate_reference("retailer_location_reference", retailer_location_reference)

    now = _now(clock or SystemClock())
    spec = lifecycle.creation_spec()
    connection = RetailerConnection(
        user_id=user_id,
        retailer_id=retailer_id,
        status=spec.to_state.value,
        authentication_method=authentication_method,
        external_authorization_reference=external_authorization_reference,
        retailer_location_reference=retailer_location_reference,
        version=1,
        created_at=now,
        updated_at=now,
    )
    try:
        repository.add(db, connection)
    except IntegrityError as exc:
        db.rollback()
        if _is_unique_violation(exc, _ACTIVE_CONNECTION_INDEX):
            raise RetailerConnectionAlreadyExists(
                user_id=user_id,
                retailer_id=retailer_id,
            ) from exc
        raise
    _audit(
        db,
        connection=connection,
        from_state=None,
        to_state=spec.to_state,
        reason=spec.reason,
        occurred_at=now,
        event=spec.audit_event,
        request_id=request_id,
    )
    db.commit()
    db.refresh(connection)
    return connection


def get_connection(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
) -> RetailerConnection:
    """Return one owner-scoped connection or raise not-found."""

    connection = repository.get_owned(
        db,
        user_id=user_id,
        connection_id=connection_id,
    )
    if connection is None:
        raise RetailerConnectionNotFound(connection_id)
    return connection


def list_connections(db: Session, *, user_id: UUID) -> list[RetailerConnection]:
    """Return all connections owned by ``user_id``."""

    return repository.list_owned(db, user_id=user_id)


def transition(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    to_state: RetailerConnectionStatus | str,
    reason: RetailerConnectionReason | str,
    expected_version: int | None = None,
    request_id: str | None = None,
    clock: Clock | None = None,
    restriction_source: RestrictionSource | str | None = None,
    restriction_category: RestrictionCategory | str | None = None,
) -> RetailerConnection:
    """Apply one edge from the declarative transition table.

    ``expected_version`` is the optimistic-concurrency guard. A stale value
    raises ``RetailerConnectionConflict`` after the row lock is acquired.
    Entering ``BLOCKED`` requires a controlled restriction source and category;
    supplying them for any other target is rejected.
    """

    target = _coerce_status(to_state)
    reason_code = _coerce_reason(reason)
    source = _coerce_restriction_source(restriction_source)
    category = _coerce_restriction_category(restriction_category)
    now = _now(clock or SystemClock())
    connection = _locked_owned(
        db,
        user_id=user_id,
        connection_id=connection_id,
        expected_version=expected_version,
    )
    return _transition_locked(
        db,
        connection,
        to_state=target,
        reason=reason_code,
        now=now,
        request_id=request_id,
        restriction_source=source,
        restriction_category=category,
    )


def record_successful_validation(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    expected_version: int | None = None,
    request_id: str | None = None,
    clock: Clock | None = None,
) -> RetailerConnection:
    """Record a successful validation.

    State-changing cases use the transition table (PENDING_AUTH -> CONNECTED,
    DEGRADED -> CONNECTED, REAUTH_REQUIRED -> CONNECTED). A validation while
    already CONNECTED is a timestamp-only observation, not a state transition:
    it refreshes ``last_validated_at`` without bumping the optimistic version or
    emitting an audit event. Repeated successful validations must not create
    unbounded permanent audit rows.
    """

    now = _now(clock or SystemClock())
    connection = _locked_owned(
        db,
        user_id=user_id,
        connection_id=connection_id,
        expected_version=expected_version,
    )
    current = _coerce_status(connection.status)
    if current == RetailerConnectionStatus.CONNECTED:
        connection.last_validated_at = now
        connection.updated_at = now
        db.commit()
        db.refresh(connection)
        return connection

    target = lifecycle.VALIDATION_TARGETS.get(current)
    if target is None:
        db.rollback()
        raise InvalidRetailerConnectionTransition(
            from_state=current,
            to_state=RetailerConnectionStatus.CONNECTED,
            reason=RetailerConnectionReason.REVALIDATED,
        )
    to_state, reason = target
    return _transition_locked(
        db,
        connection,
        to_state=to_state,
        reason=reason,
        now=now,
        request_id=request_id,
    )


def record_authentication_failure(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    expected_version: int | None = None,
    request_id: str | None = None,
    clock: Clock | None = None,
) -> RetailerConnection:
    """Move a connection to REAUTH_REQUIRED; never to REVOKED."""

    now = _now(clock or SystemClock())
    connection = _locked_owned(
        db,
        user_id=user_id,
        connection_id=connection_id,
        expected_version=expected_version,
    )
    return _transition_locked(
        db,
        connection,
        to_state=RetailerConnectionStatus.REAUTH_REQUIRED,
        reason=RetailerConnectionReason.AUTH_FAILED,
        now=now,
        request_id=request_id,
    )


def disconnect(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    expected_version: int | None = None,
    request_id: str | None = None,
    clock: Clock | None = None,
) -> RetailerConnection:
    """Move a non-terminal connection to terminal DISCONNECTED.

    A repeat disconnect is an idempotent no-op. REVOKED is terminal and cannot
    be disconnected; a reconnect creates a new record.
    """

    now = _now(clock or SystemClock())
    connection = _locked_owned(
        db,
        user_id=user_id,
        connection_id=connection_id,
        expected_version=expected_version,
    )
    return _transition_locked(
        db,
        connection,
        to_state=RetailerConnectionStatus.DISCONNECTED,
        reason=RetailerConnectionReason.DISCONNECTED,
        now=now,
        request_id=request_id,
    )


def record_health_check(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    expected_version: int | None = None,
    clock: Clock | None = None,
) -> RetailerConnection:
    """Record one bounded health observation without a state change.

    The lifecycle matrix permits this only while CONNECTED or DEGRADED. It
    refreshes ``last_validated_at`` without bumping the optimistic version and
    without writing an audit event, so polling cannot flood the audit log.
    Recovery from DEGRADED still requires an explicit
    :func:`record_successful_validation` transition.
    """

    now = _now(clock or SystemClock())
    connection = _locked_owned(
        db,
        user_id=user_id,
        connection_id=connection_id,
        expected_version=expected_version,
    )
    current = _coerce_status(connection.status)
    if not lifecycle.operation_is_permitted(
        current, RetailerOperation.RETAILER_HEALTH_CHECK
    ):
        db.rollback()
        raise RetailerOperationDenied(
            status=current,
            operation=RetailerOperation.RETAILER_HEALTH_CHECK,
        )
    connection.last_validated_at = now
    connection.updated_at = now
    db.commit()
    db.refresh(connection)
    return connection


def record_block(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    restriction_source: RestrictionSource | str,
    restriction_category: RestrictionCategory | str,
    expected_version: int | None = None,
    request_id: str | None = None,
    clock: Clock | None = None,
) -> RetailerConnection:
    """Enter BLOCKED with explicit, controlled restriction provenance.

    There is no automatic unblock. Recovery from BLOCKED requires an explicitly
    authorized transition (currently DISCONNECTED only); reconnection creates a
    new record.
    """

    return transition(
        db,
        user_id=user_id,
        connection_id=connection_id,
        to_state=RetailerConnectionStatus.BLOCKED,
        reason=RetailerConnectionReason.BLOCKED,
        expected_version=expected_version,
        request_id=request_id,
        clock=clock,
        restriction_source=restriction_source,
        restriction_category=restriction_category,
    )
