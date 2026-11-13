"""Full 7x7 transition matrix against real PostgreSQL."""

from __future__ import annotations

import pytest

from app.retailer_connections import lifecycle, service
from app.retailer_connections.lifecycle import (
    InvalidRetailerConnectionTransition,
    RetailerConnectionReason,
    RetailerConnectionStatus,
)
from tests.integration.retailer_connections.conftest import (
    NOW,
    audit_events_for,
)

ALL_STATES = tuple(RetailerConnectionStatus)
MATRIX = tuple((from_state, to_state) for from_state in ALL_STATES for to_state in ALL_STATES)


def _reason_for(
    from_state: RetailerConnectionStatus,
    to_state: RetailerConnectionStatus,
) -> RetailerConnectionReason:
    if from_state == to_state:
        return lifecycle.canonical_reason(from_state)
    for spec in lifecycle.TRANSITIONS:
        if (
            spec.from_state == from_state
            and spec.to_state == to_state
            and not spec.noop
        ):
            return spec.reason
    # The creation reason is deliberately never legal for a cross-state edge, so
    # this produces a deterministic illegal transition for the matrix.
    return RetailerConnectionReason.AUTHORIZATION_PENDING


def _snapshot(connection) -> dict[str, object]:
    return {
        "status": connection.status,
        "version": connection.version,
        "updated_at": connection.updated_at,
        "connected_at": connection.connected_at,
        "last_validated_at": connection.last_validated_at,
        "last_auth_failure_at": connection.last_auth_failure_at,
        "reauth_required_at": connection.reauth_required_at,
        "disconnected_at": connection.disconnected_at,
        "blocked_at": connection.blocked_at,
        "blocked_source": connection.blocked_source,
        "blocked_category": connection.blocked_category,
    }


def _restriction_for(to_state: RetailerConnectionStatus) -> dict[str, str]:
    if to_state is RetailerConnectionStatus.BLOCKED:
        return {
            "restriction_source": "retailer",
            "restriction_category": "account_suspended",
        }
    return {}


@pytest.mark.parametrize(("from_state", "to_state"), MATRIX)
def test_every_state_pair_is_legal_noop_or_rejected(
    db_session,
    make_user,
    make_connection,
    clock,
    from_state: RetailerConnectionStatus,
    to_state: RetailerConnectionStatus,
) -> None:
    user = make_user()
    connection = make_connection(user_id=user.id, status=from_state)
    connection_id = connection.id
    reason = _reason_for(from_state, to_state)
    before = _snapshot(connection)
    spec = lifecycle.lookup(from_state, to_state, reason)

    if spec is None:
        with pytest.raises(InvalidRetailerConnectionTransition):
            service.transition(
                db_session,
                user_id=user.id,
                connection_id=connection_id,
                to_state=to_state,
                reason=reason,
                expected_version=1,
                clock=clock,
                **_restriction_for(to_state),
            )
        db_session.refresh(connection)
        assert _snapshot(connection) == before
        assert audit_events_for(db_session, connection_id) == []
        return

    result = service.transition(
        db_session,
        user_id=user.id,
        connection_id=connection_id,
        to_state=to_state,
        reason=reason,
        expected_version=1,
        clock=clock,
        **_restriction_for(to_state),
    )
    assert result.id == connection_id
    assert result.status == to_state.value

    if spec.noop:
        assert _snapshot(result) == before
        assert audit_events_for(db_session, connection_id) == []
        return

    after = _snapshot(result)
    assert after["version"] == before["version"] + 1
    assert after["updated_at"] == NOW
    assert after["status"] == to_state.value

    expected_connected_at = before["connected_at"]
    if to_state == RetailerConnectionStatus.CONNECTED:
        expected_connected_at = expected_connected_at or NOW
    assert after["connected_at"] == expected_connected_at

    expected_last_validated_at = before["last_validated_at"]
    if to_state == RetailerConnectionStatus.CONNECTED:
        expected_last_validated_at = NOW
    assert after["last_validated_at"] == expected_last_validated_at

    expected_last_auth_failure_at = before["last_auth_failure_at"]
    expected_reauth_required_at = before["reauth_required_at"]
    if to_state == RetailerConnectionStatus.REAUTH_REQUIRED:
        expected_last_auth_failure_at = NOW
        expected_reauth_required_at = NOW
    assert after["last_auth_failure_at"] == expected_last_auth_failure_at
    assert after["reauth_required_at"] == expected_reauth_required_at

    expected_disconnected_at = before["disconnected_at"]
    if to_state == RetailerConnectionStatus.DISCONNECTED:
        expected_disconnected_at = NOW
    assert after["disconnected_at"] == expected_disconnected_at

    if to_state == RetailerConnectionStatus.BLOCKED:
        assert after["blocked_at"] == NOW
        assert after["blocked_source"] == "retailer"
        assert after["blocked_category"] == "account_suspended"
    else:
        # Blocked provenance is retained as historical metadata when a BLOCKED
        # record is disconnected; otherwise it stays unchanged.
        assert after["blocked_at"] == before["blocked_at"]
        assert after["blocked_source"] == before["blocked_source"]
        assert after["blocked_category"] == before["blocked_category"]

    events = audit_events_for(db_session, connection_id)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == spec.audit_event
    assert event.object_type == "retailer_connection"
    assert event.object_id == str(connection_id)
    assert event.user_id == user.id
    assert set(event.payload or {}) == service.AUDIT_PAYLOAD_FIELDS
    assert event.payload == {
        "connection_id": str(connection_id),
        "user_id": str(user.id),
        "retailer_id": "BLINKIT",
        "from_state": from_state.value,
        "to_state": to_state.value,
        "reason_code": reason.value,
        "occurred_at": NOW.isoformat(),
    }
