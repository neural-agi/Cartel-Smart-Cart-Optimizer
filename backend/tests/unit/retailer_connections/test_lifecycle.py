"""Unit coverage for the declarative retailer-connection lifecycle table."""

from __future__ import annotations

import pytest

from app.retailer_connections import lifecycle
from app.retailer_connections.lifecycle import (
    OperationPermission,
    RestrictionCategory,
    RestrictionSource,
    RetailerConnectionReason,
    RetailerConnectionStatus,
    RetailerOperation,
    RetailerOperationDenied,
    RetailerOperationRequiresExistingAuthorization,
)

ALL_STATES = tuple(RetailerConnectionStatus)
LEGAL_CROSS_STATE_EDGES = frozenset(
    {
        (RetailerConnectionStatus.PENDING_AUTH, RetailerConnectionStatus.CONNECTED),
        (RetailerConnectionStatus.PENDING_AUTH, RetailerConnectionStatus.REAUTH_REQUIRED),
        (RetailerConnectionStatus.PENDING_AUTH, RetailerConnectionStatus.BLOCKED),
        (RetailerConnectionStatus.PENDING_AUTH, RetailerConnectionStatus.REVOKED),
        (RetailerConnectionStatus.PENDING_AUTH, RetailerConnectionStatus.DISCONNECTED),
        (RetailerConnectionStatus.CONNECTED, RetailerConnectionStatus.DEGRADED),
        (RetailerConnectionStatus.CONNECTED, RetailerConnectionStatus.REAUTH_REQUIRED),
        (RetailerConnectionStatus.CONNECTED, RetailerConnectionStatus.BLOCKED),
        (RetailerConnectionStatus.CONNECTED, RetailerConnectionStatus.REVOKED),
        (RetailerConnectionStatus.CONNECTED, RetailerConnectionStatus.DISCONNECTED),
        (RetailerConnectionStatus.DEGRADED, RetailerConnectionStatus.CONNECTED),
        (RetailerConnectionStatus.DEGRADED, RetailerConnectionStatus.REAUTH_REQUIRED),
        (RetailerConnectionStatus.DEGRADED, RetailerConnectionStatus.BLOCKED),
        (RetailerConnectionStatus.DEGRADED, RetailerConnectionStatus.REVOKED),
        (RetailerConnectionStatus.DEGRADED, RetailerConnectionStatus.DISCONNECTED),
        (RetailerConnectionStatus.REAUTH_REQUIRED, RetailerConnectionStatus.CONNECTED),
        (RetailerConnectionStatus.REAUTH_REQUIRED, RetailerConnectionStatus.BLOCKED),
        (RetailerConnectionStatus.REAUTH_REQUIRED, RetailerConnectionStatus.REVOKED),
        (RetailerConnectionStatus.REAUTH_REQUIRED, RetailerConnectionStatus.DISCONNECTED),
        (RetailerConnectionStatus.BLOCKED, RetailerConnectionStatus.DISCONNECTED),
    }
)


def _cross_edges() -> set[tuple[RetailerConnectionStatus, RetailerConnectionStatus]]:
    return {
        (spec.from_state, spec.to_state)
        for spec in lifecycle.TRANSITIONS
        if spec.from_state is not None and spec.from_state != spec.to_state
    }


def test_status_vocabulary_is_exactly_the_seven_brief_states() -> None:
    assert {status.value for status in ALL_STATES} == {
        "PENDING_AUTH",
        "CONNECTED",
        "DEGRADED",
        "REAUTH_REQUIRED",
        "REVOKED",
        "BLOCKED",
        "DISCONNECTED",
    }


def test_reason_vocabulary_is_constrained_codes() -> None:
    assert {reason.value for reason in RetailerConnectionReason} == {
        "authorization_pending",
        "authentication_completed",
        "health_degraded",
        "auth_failed",
        "revalidated",
        "revoked",
        "blocked",
        "disconnected",
    }


def test_supported_retailer_ids_reuse_existing_platform_vocabulary() -> None:
    assert lifecycle.SUPPORTED_RETAILER_IDS == {
        "BLINKIT",
        "ZEPTO",
        "INSTAMART",
        "BIGBASKET",
        "FLIPKART_MINUTES",
    }


def test_transition_table_has_no_duplicate_keys() -> None:
    keys = [(spec.from_state, spec.to_state, spec.reason) for spec in lifecycle.TRANSITIONS]
    assert len(keys) == len(set(keys))


def test_creation_edge_is_declarative() -> None:
    spec = lifecycle.creation_spec()
    assert spec.from_state is None
    assert spec.to_state == RetailerConnectionStatus.PENDING_AUTH
    assert spec.reason == RetailerConnectionReason.AUTHORIZATION_PENDING
    assert spec.audit_event == lifecycle.AUDIT_CREATED
    assert spec.noop is False


def test_cross_state_edges_match_the_documented_conservative_set() -> None:
    assert _cross_edges() == LEGAL_CROSS_STATE_EDGES


def test_every_state_has_a_canonical_idempotent_same_state_entry() -> None:
    for status in ALL_STATES:
        reason = lifecycle.canonical_reason(status)
        spec = lifecycle.lookup(status, status, reason)
        assert spec is not None, status
        assert spec.noop is True, status


@pytest.mark.parametrize("status", ALL_STATES)
def test_same_state_lookup_is_noop_only_for_declared_reasons(
    status: RetailerConnectionStatus,
) -> None:
    canonical = lifecycle.lookup(status, status, lifecycle.canonical_reason(status))
    assert canonical is not None and canonical.noop is True

    for reason in RetailerConnectionReason:
        spec = lifecycle.lookup(status, status, reason)
        if spec is not None:
            assert spec.noop is True


@pytest.mark.parametrize("status", ALL_STATES)
def test_same_state_with_an_unrelated_reason_is_illegal(
    status: RetailerConnectionStatus,
) -> None:
    valid_reasons = {
        reason
        for reason in RetailerConnectionReason
        if lifecycle.lookup(status, status, reason) is not None
    }
    wrong_reason = next(
        reason for reason in RetailerConnectionReason if reason not in valid_reasons
    )
    assert lifecycle.lookup(status, status, wrong_reason) is None


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (from_state, to_state)
        for from_state in ALL_STATES
        for to_state in ALL_STATES
        if from_state != to_state
    ],
)
def test_every_cross_state_pair_is_either_declared_or_illegal(
    from_state: RetailerConnectionStatus,
    to_state: RetailerConnectionStatus,
) -> None:
    declared = [
        spec
        for spec in lifecycle.TRANSITIONS
        if spec.from_state == from_state and spec.to_state == to_state and not spec.noop
    ]
    if (from_state, to_state) in LEGAL_CROSS_STATE_EDGES:
        assert len(declared) == 1
    else:
        assert declared == []


def test_revoked_and_disconnected_are_terminal() -> None:
    for terminal in (
        RetailerConnectionStatus.REVOKED,
        RetailerConnectionStatus.DISCONNECTED,
    ):
        assert terminal in lifecycle.TERMINAL_STATES
        outgoing = {
            spec.to_state
            for spec in lifecycle.TRANSITIONS
            if spec.from_state == terminal and not spec.noop
        }
        assert outgoing == set()


def test_blocked_exits_only_to_disconnected() -> None:
    outgoing = {
        spec.to_state
        for spec in lifecycle.TRANSITIONS
        if spec.from_state == RetailerConnectionStatus.BLOCKED and not spec.noop
    }
    assert outgoing == {RetailerConnectionStatus.DISCONNECTED}


def test_no_failure_reason_edges_directly_to_revoked() -> None:
    for from_state in ALL_STATES:
        assert (
            lifecycle.lookup(
                from_state,
                RetailerConnectionStatus.REVOKED,
                RetailerConnectionReason.HEALTH_DEGRADED,
            )
            is None
        )
        assert (
            lifecycle.lookup(
                from_state,
                RetailerConnectionStatus.REVOKED,
                RetailerConnectionReason.AUTH_FAILED,
            )
            is None
        )


def test_nothing_transitions_back_to_pending_auth() -> None:
    cross_edges_to_pending = {
        spec.from_state
        for spec in lifecycle.TRANSITIONS
        if spec.to_state == RetailerConnectionStatus.PENDING_AUTH
        and spec.from_state is not None
        and spec.from_state != RetailerConnectionStatus.PENDING_AUTH
        and not spec.noop
    }
    assert cross_edges_to_pending == set()


def test_operation_vocabulary_covers_all_seven_classes() -> None:
    assert {operation.value for operation in RetailerOperation} == {
        "cartel_data_access",
        "connection_metadata",
        "retailer_health_check",
        "product_discovery",
        "price_availability_acquisition",
        "cart_preparation",
        "checkout",
    }


def test_operation_matrix_is_complete_and_has_no_extra_cells() -> None:
    assert set(lifecycle.OPERATION_MATRIX) == set(ALL_STATES)
    for status in ALL_STATES:
        assert set(lifecycle.OPERATION_MATRIX[status]) == set(RetailerOperation)


def test_operation_matrix_matches_the_ratified_policy() -> None:
    permitted = OperationPermission.PERMITTED
    denied = OperationPermission.DENIED
    deferred = OperationPermission.DEFERRED

    expected = {
        RetailerConnectionStatus.PENDING_AUTH: {
            RetailerOperation.CARTEL_DATA_ACCESS: deferred,
            RetailerOperation.CONNECTION_METADATA: deferred,
            RetailerOperation.RETAILER_HEALTH_CHECK: denied,
            RetailerOperation.PRODUCT_DISCOVERY: denied,
            RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: denied,
            RetailerOperation.CART_PREPARATION: denied,
            RetailerOperation.CHECKOUT: denied,
        },
        RetailerConnectionStatus.CONNECTED: {
            operation: permitted for operation in RetailerOperation
        },
        RetailerConnectionStatus.DEGRADED: {
            RetailerOperation.CARTEL_DATA_ACCESS: permitted,
            RetailerOperation.CONNECTION_METADATA: permitted,
            RetailerOperation.RETAILER_HEALTH_CHECK: permitted,
            RetailerOperation.PRODUCT_DISCOVERY: denied,
            RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: denied,
            RetailerOperation.CART_PREPARATION: denied,
            RetailerOperation.CHECKOUT: denied,
        },
        RetailerConnectionStatus.REAUTH_REQUIRED: {
            RetailerOperation.CARTEL_DATA_ACCESS: permitted,
            RetailerOperation.CONNECTION_METADATA: permitted,
            RetailerOperation.RETAILER_HEALTH_CHECK: denied,
            RetailerOperation.PRODUCT_DISCOVERY: denied,
            RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: denied,
            RetailerOperation.CART_PREPARATION: denied,
            RetailerOperation.CHECKOUT: denied,
        },
        RetailerConnectionStatus.BLOCKED: {
            RetailerOperation.CARTEL_DATA_ACCESS: deferred,
            RetailerOperation.CONNECTION_METADATA: permitted,
            RetailerOperation.RETAILER_HEALTH_CHECK: denied,
            RetailerOperation.PRODUCT_DISCOVERY: denied,
            RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: denied,
            RetailerOperation.CART_PREPARATION: denied,
            RetailerOperation.CHECKOUT: denied,
        },
        RetailerConnectionStatus.REVOKED: {
            RetailerOperation.CARTEL_DATA_ACCESS: deferred,
            RetailerOperation.CONNECTION_METADATA: deferred,
            RetailerOperation.RETAILER_HEALTH_CHECK: denied,
            RetailerOperation.PRODUCT_DISCOVERY: denied,
            RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: denied,
            RetailerOperation.CART_PREPARATION: denied,
            RetailerOperation.CHECKOUT: denied,
        },
        RetailerConnectionStatus.DISCONNECTED: {
            RetailerOperation.CARTEL_DATA_ACCESS: deferred,
            RetailerOperation.CONNECTION_METADATA: deferred,
            RetailerOperation.RETAILER_HEALTH_CHECK: denied,
            RetailerOperation.PRODUCT_DISCOVERY: denied,
            RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: denied,
            RetailerOperation.CART_PREPARATION: denied,
            RetailerOperation.CHECKOUT: denied,
        },
    }
    assert lifecycle.OPERATION_MATRIX == expected


@pytest.mark.parametrize("status", ALL_STATES)
@pytest.mark.parametrize("operation", tuple(RetailerOperation))
def test_every_state_operation_cell_has_a_defined_permission(
    status: RetailerConnectionStatus,
    operation: RetailerOperation,
) -> None:
    permission = lifecycle.permission_for(status, operation)
    assert permission in {
        OperationPermission.PERMITTED,
        OperationPermission.DENIED,
        OperationPermission.DEFERRED,
    }
    assert lifecycle.operation_is_permitted(status, operation) is (
        permission is OperationPermission.PERMITTED
    )
    assert lifecycle.operation_requires_existing_authorization(status, operation) is (
        permission is OperationPermission.DEFERRED
    )


@pytest.mark.parametrize("status", ALL_STATES)
@pytest.mark.parametrize("operation", tuple(RetailerOperation))
def test_authorize_operation_enforces_the_matrix(
    status: RetailerConnectionStatus,
    operation: RetailerOperation,
) -> None:
    permission = lifecycle.permission_for(status, operation)
    if permission is OperationPermission.PERMITTED:
        lifecycle.authorize_operation(status, operation)
        lifecycle.authorize_operation(status, operation, existing_authorization=False)
    elif permission is OperationPermission.DENIED:
        with pytest.raises(RetailerOperationDenied):
            lifecycle.authorize_operation(status, operation)
        # Existing Cartel authorization can never bypass a lifecycle denial.
        with pytest.raises(RetailerOperationDenied):
            lifecycle.authorize_operation(status, operation, existing_authorization=True)
    else:
        with pytest.raises(RetailerOperationRequiresExistingAuthorization):
            lifecycle.authorize_operation(status, operation)
        lifecycle.authorize_operation(status, operation, existing_authorization=True)


def test_denied_cells_cover_every_retailer_operation_in_terminal_states() -> None:
    for status in (
        RetailerConnectionStatus.REVOKED,
        RetailerConnectionStatus.DISCONNECTED,
        RetailerConnectionStatus.BLOCKED,
    ):
        for operation in (
            RetailerOperation.RETAILER_HEALTH_CHECK,
            RetailerOperation.PRODUCT_DISCOVERY,
            RetailerOperation.PRICE_AVAILABILITY_ACQUISITION,
            RetailerOperation.CART_PREPARATION,
            RetailerOperation.CHECKOUT,
        ):
            assert not lifecycle.operation_is_permitted(status, operation)


def test_degraded_permits_only_bounded_health_and_cartel_operations() -> None:
    status = RetailerConnectionStatus.DEGRADED
    permitted = {
        operation
        for operation in RetailerOperation
        if lifecycle.operation_is_permitted(status, operation)
    }
    assert permitted == {
        RetailerOperation.CARTEL_DATA_ACCESS,
        RetailerOperation.CONNECTION_METADATA,
        RetailerOperation.RETAILER_HEALTH_CHECK,
    }


def test_reauth_required_denies_every_retailer_operation() -> None:
    status = RetailerConnectionStatus.REAUTH_REQUIRED
    for operation in (
        RetailerOperation.RETAILER_HEALTH_CHECK,
        RetailerOperation.PRODUCT_DISCOVERY,
        RetailerOperation.PRICE_AVAILABILITY_ACQUISITION,
        RetailerOperation.CART_PREPARATION,
        RetailerOperation.CHECKOUT,
    ):
        assert not lifecycle.operation_is_permitted(status, operation)
    assert lifecycle.operation_is_permitted(
        status, RetailerOperation.CARTEL_DATA_ACCESS
    )
    assert lifecycle.operation_is_permitted(
        status, RetailerOperation.CONNECTION_METADATA
    )


def test_restriction_vocabulary_is_controlled() -> None:
    assert {source.value for source in RestrictionSource} == {
        "retailer",
        "cartel_operator",
        "user",
        "legal",
        "system",
    }
    assert {category.value for category in RestrictionCategory} == {
        "account_suspended",
        "terms_violation",
        "fraud_review",
        "legal_hold",
        "user_request",
        "unknown",
    }


def test_validation_targets_are_table_backed() -> None:
    assert lifecycle.VALIDATION_TARGETS == {
        RetailerConnectionStatus.PENDING_AUTH: (
            RetailerConnectionStatus.CONNECTED,
            RetailerConnectionReason.AUTHENTICATION_COMPLETED,
        ),
        RetailerConnectionStatus.DEGRADED: (
            RetailerConnectionStatus.CONNECTED,
            RetailerConnectionReason.REVALIDATED,
        ),
        RetailerConnectionStatus.REAUTH_REQUIRED: (
            RetailerConnectionStatus.CONNECTED,
            RetailerConnectionReason.REVALIDATED,
        ),
    }
    for status, (to_state, reason) in lifecycle.VALIDATION_TARGETS.items():
        assert lifecycle.lookup(status, to_state, reason) is not None


def test_input_patterns_are_code_shaped() -> None:
    assert lifecycle.REFERENCE_PATTERN.fullmatch("blinkit-auth-ref-123")
    assert not lifecycle.REFERENCE_PATTERN.fullmatch("has space")
    assert not lifecycle.REFERENCE_PATTERN.fullmatch("")
    assert lifecycle.AUTHENTICATION_METHOD_PATTERN.fullmatch("oauth_pkce")
    assert not lifecycle.AUTHENTICATION_METHOD_PATTERN.fullmatch("OAuth PKCE")
