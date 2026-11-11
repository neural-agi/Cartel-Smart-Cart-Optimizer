"""Behavioural integration tests for the retailer-connection service."""

from __future__ import annotations

import threading
from datetime import timedelta

import pytest

from app.retailer_connections import lifecycle, repository, service
from app.retailer_connections.lifecycle import (
    InvalidRetailerConnectionInput,
    InvalidRetailerConnectionTransition,
    RetailerConnectionAlreadyExists,
    RetailerConnectionConflict,
    RetailerConnectionNotFound,
    RetailerConnectionReason,
    RetailerConnectionStatus,
    RetailerOperation,
    RetailerOperationDenied,
)
from tests.integration.retailer_connections.conftest import (
    LATER,
    NOW,
    audit_events_for,
)
from tests.unit.timestamp_support import FrozenClock


def _at(clock_base, minutes: int) -> FrozenClock:
    return FrozenClock(clock_base + timedelta(minutes=minutes))


def test_create_pending_connection_defaults_and_audit(
    db_session, make_user, clock
) -> None:
    user = make_user()
    connection = service.create_pending_connection(
        db_session,
        user_id=user.id,
        retailer_id="BLINKIT",
        authentication_method="oauth_pkce",
        external_authorization_reference="blinkit-ref-123",
        retailer_location_reference="loc-123",
        request_id="req-create",
        clock=clock,
    )

    assert connection.status == RetailerConnectionStatus.PENDING_AUTH.value
    assert connection.version == 1
    assert connection.connected_at is None
    assert connection.last_validated_at is None
    assert connection.last_auth_failure_at is None
    assert connection.reauth_required_at is None
    assert connection.disconnected_at is None
    assert connection.created_at == NOW
    assert connection.updated_at == NOW
    assert connection.authentication_method == "oauth_pkce"
    assert connection.external_authorization_reference == "blinkit-ref-123"
    assert connection.retailer_location_reference == "loc-123"

    events = audit_events_for(db_session, connection.id)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == lifecycle.AUDIT_CREATED
    assert event.request_id == "req-create"
    assert event.payload == {
        "connection_id": str(connection.id),
        "user_id": str(user.id),
        "retailer_id": "BLINKIT",
        "from_state": None,
        "to_state": "PENDING_AUTH",
        "reason_code": "authorization_pending",
        "occurred_at": NOW.isoformat(),
    }

    assert service.get_connection(
        db_session, user_id=user.id, connection_id=connection.id
    ).id == connection.id
    assert [item.id for item in service.list_connections(db_session, user_id=user.id)] == [
        connection.id
    ]


def test_duplicate_active_connection_rejected(db_session, make_user, clock) -> None:
    user = make_user()
    service.create_pending_connection(
        db_session, user_id=user.id, retailer_id="BLINKIT", clock=clock
    )
    with pytest.raises(RetailerConnectionAlreadyExists):
        service.create_pending_connection(
            db_session, user_id=user.id, retailer_id="BLINKIT", clock=clock
        )

    assert len(service.list_connections(db_session, user_id=user.id)) == 1
    assert len(
        audit_events_for(db_session, service.list_connections(db_session, user_id=user.id)[0].id)
    ) == 1

    other = service.create_pending_connection(
        db_session, user_id=user.id, retailer_id="ZEPTO", clock=clock
    )
    assert other.retailer_id == "ZEPTO"


def test_new_record_allowed_after_terminal_states(
    db_session, make_user, clock
) -> None:
    user = make_user()
    first = service.create_pending_connection(
        db_session, user_id=user.id, retailer_id="BLINKIT", clock=clock
    )
    service.record_successful_validation(
        db_session, user_id=user.id, connection_id=first.id, clock=clock
    )
    service.disconnect(db_session, user_id=user.id, connection_id=first.id, clock=clock)

    second = service.create_pending_connection(
        db_session, user_id=user.id, retailer_id="BLINKIT", clock=clock
    )
    assert second.id != first.id
    assert len(service.list_connections(db_session, user_id=user.id)) == 2

    service.transition(
        db_session,
        user_id=user.id,
        connection_id=second.id,
        to_state=RetailerConnectionStatus.REVOKED,
        reason=RetailerConnectionReason.REVOKED,
        clock=clock,
    )
    third = service.create_pending_connection(
        db_session, user_id=user.id, retailer_id="BLINKIT", clock=clock
    )
    assert third.id not in {first.id, second.id}
    assert len(service.list_connections(db_session, user_id=user.id)) == 3


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"retailer_id": "UNKNOWN"}, "unsupported_retailer_id"),
        ({"retailer_id": "BLINKIT", "authentication_method": "Bad Method"}, "invalid_authentication_method"),
        (
            {
                "retailer_id": "BLINKIT",
                "external_authorization_reference": "has space",
            },
            "invalid_external_authorization_reference",
        ),
        (
            {
                "retailer_id": "BLINKIT",
                "retailer_location_reference": "bad!reference",
            },
            "invalid_retailer_location_reference",
        ),
    ],
)
def test_invalid_create_inputs_rejected_without_rows(
    db_session, make_user, clock, kwargs, code
) -> None:
    user = make_user()
    with pytest.raises(InvalidRetailerConnectionInput) as excinfo:
        service.create_pending_connection(
            db_session, user_id=user.id, clock=clock, **kwargs
        )
    assert excinfo.value.code == code
    assert service.list_connections(db_session, user_id=user.id) == []


def test_ownership_isolation_for_every_method(
    db_session, make_user, make_connection, clock
) -> None:
    owner = make_user()
    intruder = make_user()
    connection = make_connection(
        user_id=owner.id, status=RetailerConnectionStatus.CONNECTED
    )
    connection_id = connection.id
    before = (
        connection.status,
        connection.version,
        connection.updated_at,
        connection.connected_at,
    )

    with pytest.raises(RetailerConnectionNotFound):
        service.get_connection(
            db_session, user_id=intruder.id, connection_id=connection_id
        )
    assert service.list_connections(db_session, user_id=intruder.id) == []

    with pytest.raises(RetailerConnectionNotFound):
        service.transition(
            db_session,
            user_id=intruder.id,
            connection_id=connection_id,
            to_state=RetailerConnectionStatus.DEGRADED,
            reason=RetailerConnectionReason.HEALTH_DEGRADED,
            clock=clock,
        )
    with pytest.raises(RetailerConnectionNotFound):
        service.record_successful_validation(
            db_session, user_id=intruder.id, connection_id=connection_id, clock=clock
        )
    with pytest.raises(RetailerConnectionNotFound):
        service.record_authentication_failure(
            db_session, user_id=intruder.id, connection_id=connection_id, clock=clock
        )
    with pytest.raises(RetailerConnectionNotFound):
        service.disconnect(
            db_session, user_id=intruder.id, connection_id=connection_id, clock=clock
        )

    db_session.refresh(connection)
    assert (
        connection.status,
        connection.version,
        connection.updated_at,
        connection.connected_at,
    ) == before
    assert audit_events_for(db_session, connection_id) == []

    assert service.get_connection(
        db_session, user_id=owner.id, connection_id=connection_id
    ).id == connection_id


def test_timestamp_history_is_preserved(
    db_session, make_user, clock
) -> None:
    user = make_user()
    connection = service.create_pending_connection(
        db_session, user_id=user.id, retailer_id="BLINKIT", clock=_at(NOW, 0)
    )
    connection = service.record_successful_validation(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        clock=_at(NOW, 1),
    )
    assert connection.status == RetailerConnectionStatus.CONNECTED.value
    assert connection.connected_at == NOW + timedelta(minutes=1)
    assert connection.last_validated_at == NOW + timedelta(minutes=1)

    connection = service.record_authentication_failure(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        clock=_at(NOW, 2),
    )
    assert connection.status == RetailerConnectionStatus.REAUTH_REQUIRED.value
    assert connection.last_auth_failure_at == NOW + timedelta(minutes=2)
    assert connection.reauth_required_at == NOW + timedelta(minutes=2)
    assert connection.connected_at == NOW + timedelta(minutes=1)
    assert connection.last_validated_at == NOW + timedelta(minutes=1)

    connection = service.record_successful_validation(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        clock=_at(NOW, 3),
    )
    assert connection.status == RetailerConnectionStatus.CONNECTED.value
    assert connection.connected_at == NOW + timedelta(minutes=1)
    assert connection.last_validated_at == NOW + timedelta(minutes=3)
    assert connection.last_auth_failure_at == NOW + timedelta(minutes=2)
    assert connection.reauth_required_at == NOW + timedelta(minutes=2)

    connection = service.transition(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        to_state=RetailerConnectionStatus.DEGRADED,
        reason=RetailerConnectionReason.HEALTH_DEGRADED,
        clock=_at(NOW, 4),
    )
    assert connection.status == RetailerConnectionStatus.DEGRADED.value
    assert connection.connected_at == NOW + timedelta(minutes=1)
    assert connection.last_validated_at == NOW + timedelta(minutes=3)
    assert connection.last_auth_failure_at == NOW + timedelta(minutes=2)
    assert connection.reauth_required_at == NOW + timedelta(minutes=2)

    connection = service.record_successful_validation(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        clock=_at(NOW, 5),
    )
    assert connection.status == RetailerConnectionStatus.CONNECTED.value
    assert connection.connected_at == NOW + timedelta(minutes=1)
    assert connection.last_validated_at == NOW + timedelta(minutes=5)
    assert connection.last_auth_failure_at == NOW + timedelta(minutes=2)
    assert connection.reauth_required_at == NOW + timedelta(minutes=2)

    connection = service.disconnect(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        clock=_at(NOW, 6),
    )
    assert connection.status == RetailerConnectionStatus.DISCONNECTED.value
    assert connection.disconnected_at == NOW + timedelta(minutes=6)
    assert connection.connected_at == NOW + timedelta(minutes=1)
    assert connection.last_validated_at == NOW + timedelta(minutes=5)
    assert connection.last_auth_failure_at == NOW + timedelta(minutes=2)
    assert connection.reauth_required_at == NOW + timedelta(minutes=2)
    version_at_disconnect = connection.version
    audit_count_at_disconnect = len(audit_events_for(db_session, connection.id))

    repeated = service.disconnect(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        clock=_at(NOW, 7),
    )
    assert repeated.version == version_at_disconnect
    assert repeated.disconnected_at == NOW + timedelta(minutes=6)
    assert len(audit_events_for(db_session, connection.id)) == audit_count_at_disconnect


def test_same_state_repeat_is_idempotent_and_different_reason_is_error(
    db_session, make_user, make_connection, clock
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    connection_id = connection.id
    before = (
        connection.status,
        connection.version,
        connection.updated_at,
        connection.connected_at,
        connection.last_validated_at,
    )
    audit_before = len(audit_events_for(db_session, connection_id))

    repeated = service.transition(
        db_session,
        user_id=user.id,
        connection_id=connection_id,
        to_state=RetailerConnectionStatus.CONNECTED,
        reason=RetailerConnectionReason.AUTHENTICATION_COMPLETED,
        clock=clock,
    )
    assert (
        repeated.status,
        repeated.version,
        repeated.updated_at,
        repeated.connected_at,
        repeated.last_validated_at,
    ) == before
    assert len(audit_events_for(db_session, connection_id)) == audit_before

    repeated = service.transition(
        db_session,
        user_id=user.id,
        connection_id=connection_id,
        to_state=RetailerConnectionStatus.CONNECTED,
        reason=RetailerConnectionReason.REVALIDATED,
        clock=clock,
    )
    assert repeated.version == before[1]
    assert len(audit_events_for(db_session, connection_id)) == audit_before

    with pytest.raises(InvalidRetailerConnectionTransition):
        service.transition(
            db_session,
            user_id=user.id,
            connection_id=connection_id,
            to_state=RetailerConnectionStatus.CONNECTED,
            reason=RetailerConnectionReason.HEALTH_DEGRADED,
            clock=clock,
        )
    db_session.refresh(connection)
    assert connection.version == before[1]
    assert len(audit_events_for(db_session, connection_id)) == audit_before


def test_validation_while_connected_is_a_timestamp_only_observation(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    before_version = connection.version
    before_connected_at = connection.connected_at

    result = service.record_successful_validation(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        clock=FrozenClock(LATER),
    )
    assert result.status == RetailerConnectionStatus.CONNECTED.value
    # Timestamp-only observation: no optimistic version bump and no audit row.
    assert result.version == before_version
    assert result.connected_at == before_connected_at
    assert result.last_validated_at == LATER
    assert result.updated_at == LATER
    assert audit_events_for(db_session, connection.id) == []


def test_repeated_health_checks_do_not_audit_or_bump_version(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    before_version = connection.version

    for offset in range(5):
        result = service.record_health_check(
            db_session,
            user_id=user.id,
            connection_id=connection.id,
            clock=FrozenClock(LATER),
        )
        assert result.version == before_version
        assert result.last_validated_at == LATER

    assert audit_events_for(db_session, connection.id) == []


def test_health_check_is_denied_outside_connected_and_degraded(
    db_session, make_user, make_connection, clock
) -> None:
    for status in (
        RetailerConnectionStatus.PENDING_AUTH,
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerConnectionStatus.BLOCKED,
        RetailerConnectionStatus.REVOKED,
        RetailerConnectionStatus.DISCONNECTED,
    ):
        user = make_user()
        connection = make_connection(user_id=user.id, status=status)
        with pytest.raises(RetailerOperationDenied):
            service.record_health_check(
                db_session,
                user_id=user.id,
                connection_id=connection.id,
                clock=clock,
            )


def test_rejected_transition_leaves_no_trace(
    db_session, make_user, make_connection, clock
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    connection_id = connection.id
    before = (
        connection.status,
        connection.version,
        connection.updated_at,
        connection.connected_at,
    )
    audit_before = len(audit_events_for(db_session, connection_id))

    with pytest.raises(InvalidRetailerConnectionTransition):
        service.transition(
            db_session,
            user_id=user.id,
            connection_id=connection_id,
            to_state=RetailerConnectionStatus.PENDING_AUTH,
            reason=RetailerConnectionReason.AUTHORIZATION_PENDING,
            clock=clock,
        )
    with pytest.raises(InvalidRetailerConnectionTransition):
        service.transition(
            db_session,
            user_id=user.id,
            connection_id=connection_id,
            to_state=RetailerConnectionStatus.CONNECTED,
            reason=RetailerConnectionReason.HEALTH_DEGRADED,
            clock=clock,
        )

    db_session.refresh(connection)
    assert (
        connection.status,
        connection.version,
        connection.updated_at,
        connection.connected_at,
    ) == before
    assert len(audit_events_for(db_session, connection_id)) == audit_before


def test_repeated_authentication_failure_is_an_idempotent_noop(
    db_session, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.REAUTH_REQUIRED
    )
    before = (
        connection.version,
        connection.updated_at,
        connection.last_auth_failure_at,
        connection.reauth_required_at,
    )
    audit_before = len(audit_events_for(db_session, connection.id))

    repeated = service.record_authentication_failure(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        clock=FrozenClock(LATER),
    )
    assert (
        repeated.version,
        repeated.updated_at,
        repeated.last_auth_failure_at,
        repeated.reauth_required_at,
    ) == before
    assert len(audit_events_for(db_session, connection.id)) == audit_before


def test_authentication_failure_never_revokes(
    db_session, make_user, make_connection, clock
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    result = service.record_authentication_failure(
        db_session, user_id=user.id, connection_id=connection.id, clock=clock
    )
    assert result.status == RetailerConnectionStatus.REAUTH_REQUIRED.value
    assert result.status != RetailerConnectionStatus.REVOKED.value
    assert result.last_auth_failure_at == NOW
    assert result.reauth_required_at == NOW
    assert (
        lifecycle.lookup(
            RetailerConnectionStatus.CONNECTED,
            RetailerConnectionStatus.REVOKED,
            RetailerConnectionReason.AUTH_FAILED,
        )
        is None
    )


def test_network_failure_degrades_and_never_revokes(
    db_session, make_user, make_connection, clock
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    result = service.transition(
        db_session,
        user_id=user.id,
        connection_id=connection.id,
        to_state=RetailerConnectionStatus.DEGRADED,
        reason=RetailerConnectionReason.HEALTH_DEGRADED,
        clock=clock,
    )
    assert result.status == RetailerConnectionStatus.DEGRADED.value
    assert (
        lifecycle.lookup(
            RetailerConnectionStatus.CONNECTED,
            RetailerConnectionStatus.REVOKED,
            RetailerConnectionReason.HEALTH_DEGRADED,
        )
        is None
    )


def test_blocked_blocks_operations_and_can_only_disconnect(
    db_session, make_user, make_connection, clock
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.BLOCKED
    )
    assert connection.blocked_at == NOW
    assert connection.blocked_source == "retailer"
    assert connection.blocked_category == "account_suspended"
    for operation in (
        RetailerOperation.RETAILER_HEALTH_CHECK,
        RetailerOperation.PRODUCT_DISCOVERY,
        RetailerOperation.PRICE_AVAILABILITY_ACQUISITION,
        RetailerOperation.CART_PREPARATION,
        RetailerOperation.CHECKOUT,
    ):
        assert not lifecycle.operation_is_permitted(
            RetailerConnectionStatus.BLOCKED, operation
        )

    with pytest.raises(InvalidRetailerConnectionTransition):
        service.record_successful_validation(
            db_session, user_id=user.id, connection_id=connection.id, clock=clock
        )
    with pytest.raises(RetailerOperationDenied):
        service.record_health_check(
            db_session, user_id=user.id, connection_id=connection.id, clock=clock
        )
    with pytest.raises(InvalidRetailerConnectionTransition):
        service.transition(
            db_session,
            user_id=user.id,
            connection_id=connection.id,
            to_state=RetailerConnectionStatus.CONNECTED,
            reason=RetailerConnectionReason.REVALIDATED,
            clock=clock,
        )

    result = service.disconnect(
        db_session, user_id=user.id, connection_id=connection.id, clock=clock
    )
    assert result.status == RetailerConnectionStatus.DISCONNECTED.value


def test_reauth_required_blocks_authenticated_but_allows_ordinary_and_repair(
    db_session, make_user, make_connection, clock
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.REAUTH_REQUIRED
    )
    assert lifecycle.operation_is_permitted(
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerOperation.CARTEL_DATA_ACCESS,
    )
    assert lifecycle.operation_is_permitted(
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerOperation.CONNECTION_METADATA,
    )
    for operation in (
        RetailerOperation.RETAILER_HEALTH_CHECK,
        RetailerOperation.PRODUCT_DISCOVERY,
        RetailerOperation.PRICE_AVAILABILITY_ACQUISITION,
        RetailerOperation.CART_PREPARATION,
        RetailerOperation.CHECKOUT,
    ):
        assert not lifecycle.operation_is_permitted(
            RetailerConnectionStatus.REAUTH_REQUIRED, operation
        )

    result = service.record_successful_validation(
        db_session, user_id=user.id, connection_id=connection.id, clock=clock
    )
    assert result.status == RetailerConnectionStatus.CONNECTED.value
    assert result.connected_at == NOW
    assert result.last_validated_at == NOW


def test_disconnected_is_terminal_and_disconnect_is_idempotent(
    db_session, make_user, make_connection, clock
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.DISCONNECTED
    )
    with pytest.raises(InvalidRetailerConnectionTransition):
        service.transition(
            db_session,
            user_id=user.id,
            connection_id=connection.id,
            to_state=RetailerConnectionStatus.CONNECTED,
            reason=RetailerConnectionReason.REVALIDATED,
            clock=clock,
        )
    with pytest.raises(InvalidRetailerConnectionTransition):
        service.record_successful_validation(
            db_session, user_id=user.id, connection_id=connection.id, clock=clock
        )
    with pytest.raises(InvalidRetailerConnectionTransition):
        service.record_authentication_failure(
            db_session, user_id=user.id, connection_id=connection.id, clock=clock
        )

    repeated = service.disconnect(
        db_session, user_id=user.id, connection_id=connection.id, clock=clock
    )
    assert repeated.status == RetailerConnectionStatus.DISCONNECTED.value
    assert repeated.version == 1


def test_revoked_is_terminal_and_new_record_is_allowed(
    db_session, make_user, make_connection, clock
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.REVOKED
    )
    with pytest.raises(InvalidRetailerConnectionTransition):
        service.disconnect(
            db_session, user_id=user.id, connection_id=connection.id, clock=clock
        )
    with pytest.raises(InvalidRetailerConnectionTransition):
        service.transition(
            db_session,
            user_id=user.id,
            connection_id=connection.id,
            to_state=RetailerConnectionStatus.CONNECTED,
            reason=RetailerConnectionReason.REVALIDATED,
            clock=clock,
        )
    with pytest.raises(InvalidRetailerConnectionTransition):
        service.record_successful_validation(
            db_session, user_id=user.id, connection_id=connection.id, clock=clock
        )
    with pytest.raises(InvalidRetailerConnectionTransition):
        service.record_authentication_failure(
            db_session, user_id=user.id, connection_id=connection.id, clock=clock
        )

    replacement = service.create_pending_connection(
        db_session, user_id=user.id, retailer_id="BLINKIT", clock=clock
    )
    assert replacement.id != connection.id


def test_repository_find_non_terminal_tracks_the_partial_index(
    db_session, make_user, clock
) -> None:
    user = make_user()
    connection = service.create_pending_connection(
        db_session, user_id=user.id, retailer_id="BLINKIT", clock=clock
    )
    found = repository.find_non_terminal(
        db_session, user_id=user.id, retailer_id="BLINKIT"
    )
    assert found is not None
    assert found.id == connection.id

    service.disconnect(
        db_session, user_id=user.id, connection_id=connection.id, clock=clock
    )
    assert (
        repository.find_non_terminal(
            db_session, user_id=user.id, retailer_id="BLINKIT"
        )
        is None
    )


def test_audit_payload_secrecy_and_reason_code_canary(
    db_session, make_user, clock
) -> None:
    user = make_user()
    external_canary = "CANARY-SECRET-7f3a9c"
    location_canary = "CANARY-LOCATION-7f3a9c"
    method_canary = "canary_secret_method"

    connection = service.create_pending_connection(
        db_session,
        user_id=user.id,
        retailer_id="BLINKIT",
        authentication_method=method_canary,
        external_authorization_reference=external_canary,
        retailer_location_reference=location_canary,
        clock=clock,
    )
    service.record_successful_validation(
        db_session, user_id=user.id, connection_id=connection.id, clock=clock
    )
    service.record_authentication_failure(
        db_session, user_id=user.id, connection_id=connection.id, clock=clock
    )
    service.record_successful_validation(
        db_session, user_id=user.id, connection_id=connection.id, clock=clock
    )
    service.disconnect(
        db_session, user_id=user.id, connection_id=connection.id, clock=clock
    )

    events = audit_events_for(db_session, connection.id)
    assert len(events) == 5
    for event in events:
        payload = event.payload or {}
        assert set(payload) == service.AUDIT_PAYLOAD_FIELDS
        serialized = repr(payload)
        assert external_canary not in serialized
        assert location_canary not in serialized
        assert method_canary not in serialized

    audit_before = len(events)
    with pytest.raises(InvalidRetailerConnectionInput):
        service.transition(
            db_session,
            user_id=user.id,
            connection_id=connection.id,
            to_state=RetailerConnectionStatus.CONNECTED,
            reason="CANARY SECRET REASON",
            clock=clock,
        )
    assert len(audit_events_for(db_session, connection.id)) == audit_before

    with pytest.raises(InvalidRetailerConnectionInput):
        service.create_pending_connection(
            db_session,
            user_id=user.id,
            retailer_id="ZEPTO",
            external_authorization_reference="CANARY SECRET WITH SPACE",
            clock=clock,
        )
    assert service.list_connections(db_session, user_id=user.id)[0].retailer_id == "BLINKIT"


def test_failed_transaction_leaves_no_audit_row(
    db_session, make_user, make_connection, clock, monkeypatch
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    connection_id = connection.id
    before_version = connection.version
    before_updated_at = connection.updated_at
    before_audit = len(audit_events_for(db_session, connection_id))

    def failing_commit() -> None:
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(db_session, "commit", failing_commit)
    with pytest.raises(RuntimeError):
        service.transition(
            db_session,
            user_id=user.id,
            connection_id=connection_id,
            to_state=RetailerConnectionStatus.DEGRADED,
            reason=RetailerConnectionReason.HEALTH_DEGRADED,
            clock=clock,
        )
    db_session.rollback()
    db_session.refresh(connection)

    assert connection.status == RetailerConnectionStatus.CONNECTED.value
    assert connection.version == before_version
    assert connection.updated_at == before_updated_at
    assert len(audit_events_for(db_session, connection_id)) == before_audit


def test_stale_writer_gets_typed_conflict(
    db_session, session_factory, make_user, make_connection
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    connection_id = connection.id
    assert connection.version == 1

    other = session_factory()
    try:
        winner = service.transition(
            other,
            user_id=user.id,
            connection_id=connection_id,
            to_state=RetailerConnectionStatus.DEGRADED,
            reason=RetailerConnectionReason.HEALTH_DEGRADED,
            expected_version=1,
            clock=FrozenClock(LATER),
        )
        assert winner.version == 2
    finally:
        other.close()

    with pytest.raises(RetailerConnectionConflict) as excinfo:
        service.transition(
            db_session,
            user_id=user.id,
            connection_id=connection_id,
            to_state=RetailerConnectionStatus.BLOCKED,
            reason=RetailerConnectionReason.BLOCKED,
            expected_version=1,
            clock=FrozenClock(LATER),
        )
    assert excinfo.value.expected_version == 1
    assert excinfo.value.actual_version == 2

    db_session.expire_all()
    final = service.get_connection(
        db_session, user_id=user.id, connection_id=connection_id
    )
    assert final.status == RetailerConnectionStatus.DEGRADED.value
    assert final.version == 2
    events = audit_events_for(db_session, connection_id)
    assert len(events) == 1
    assert events[0].event_type == lifecycle.AUDIT_DEGRADED


def test_row_lock_serializes_conflicting_transitions(
    db_session, session_factory, make_user, make_connection, clock
) -> None:
    user = make_user()
    connection = make_connection(
        user_id=user.id, status=RetailerConnectionStatus.CONNECTED
    )
    connection_id = connection.id

    # Hold the row lock in the main session.
    locked = repository.get_owned(
        db_session,
        user_id=user.id,
        connection_id=connection_id,
        for_update=True,
    )
    assert locked is not None

    started = threading.Event()
    outcome: list[BaseException | None] = []

    def contender():
        session = session_factory()
        try:
            started.set()
            try:
                service.transition(
                    session,
                    user_id=user.id,
                    connection_id=connection_id,
                    to_state=RetailerConnectionStatus.BLOCKED,
                    reason=RetailerConnectionReason.BLOCKED,
                    expected_version=1,
                    clock=FrozenClock(LATER),
                )
            except RetailerConnectionConflict as exc:  # handed back to the main thread
                outcome.append(exc)
            else:
                outcome.append(None)
        finally:
            session.close()

    thread = threading.Thread(target=contender, daemon=True)
    thread.start()
    assert started.wait(timeout=5)
    thread.join(timeout=0.2)
    assert thread.is_alive(), "contender should be blocked on the row lock"

    winner = service.transition(
        db_session,
        user_id=user.id,
        connection_id=connection_id,
        to_state=RetailerConnectionStatus.DEGRADED,
        reason=RetailerConnectionReason.HEALTH_DEGRADED,
        expected_version=1,
        clock=clock,
    )
    assert winner.version == 2

    thread.join(timeout=5)
    assert not thread.is_alive()
    assert len(outcome) == 1
    assert isinstance(outcome[0], RetailerConnectionConflict)

    db_session.expire_all()
    final = service.get_connection(
        db_session, user_id=user.id, connection_id=connection_id
    )
    assert final.status == RetailerConnectionStatus.DEGRADED.value
    assert final.version == 2
    events = audit_events_for(db_session, connection_id)
    assert len(events) == 1
    assert events[0].event_type == lifecycle.AUDIT_DEGRADED
