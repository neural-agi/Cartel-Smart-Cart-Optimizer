"""Declarative lifecycle vocabulary and transition table for retailer connections.

The table in :data:`TRANSITIONS` is the single source of truth for every state
change. Service methods must not branch on status strings themselves: they lock
the record, look the requested edge up here, and apply the returned
:class:`TransitionSpec`.

Phase F.1 ratifies the policy below. The lifecycle states and the transition
table remain the single source of truth. Operation permissions are expressed as
a complete state-by-operation matrix rather than broad booleans, so callers
cannot collapse Cartel data access, connection management, health checks,
discovery, acquisition, cart preparation, and checkout into one capability.

Unresolved policy cells are represented by :attr:`OperationPermission.DEFERRED`
and are governed by existing Cartel data / connection-metadata authorization.
They are not silently granted by this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.data_ingestion.enums import Platform


class RetailerConnectionStatus(StrEnum):
    """Durable lifecycle states for one user's retailer connection."""

    PENDING_AUTH = "PENDING_AUTH"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    REAUTH_REQUIRED = "REAUTH_REQUIRED"
    REVOKED = "REVOKED"
    BLOCKED = "BLOCKED"
    DISCONNECTED = "DISCONNECTED"


class RetailerConnectionReason(StrEnum):
    """Constrained, non-secret reason codes accepted by the service.

    Reason inputs are codes rather than free text so a caller cannot paste a
    password, OTP, token, cookie, or session blob into an audit payload.
    """

    AUTHORIZATION_PENDING = "authorization_pending"
    AUTHENTICATION_COMPLETED = "authentication_completed"
    HEALTH_DEGRADED = "health_degraded"
    AUTH_FAILED = "auth_failed"
    REVALIDATED = "revalidated"
    REVOKED = "revoked"
    BLOCKED = "blocked"
    DISCONNECTED = "disconnected"


class RetailerOperation(StrEnum):
    """Distinct operation classes that must never be collapsed together.

    The first two are Cartel-owned / management operations. The remaining five
    are retailer-facing operations with materially different risk.
    """

    CARTEL_DATA_ACCESS = "cartel_data_access"
    CONNECTION_METADATA = "connection_metadata"
    RETAILER_HEALTH_CHECK = "retailer_health_check"
    PRODUCT_DISCOVERY = "product_discovery"
    PRICE_AVAILABILITY_ACQUISITION = "price_availability_acquisition"
    CART_PREPARATION = "cart_preparation"
    CHECKOUT = "checkout"


class OperationPermission(StrEnum):
    """Outcome of the domain-layer operation authorization matrix.

    ``PERMITTED`` means the lifecycle state does not block the operation; any
    separate capability or Cartel authorization check still applies.
    ``DENIED`` is an unconditional lifecycle denial.
    ``DEFERRED`` means this policy does not decide the cell; existing Cartel
    data or connection-metadata authorization must decide it.
    """

    PERMITTED = "permitted"
    DENIED = "denied"
    DEFERRED = "deferred"


class RestrictionSource(StrEnum):
    """Controlled source of an explicit ``BLOCKED`` restriction."""

    RETAILER = "retailer"
    CARTEL_OPERATOR = "cartel_operator"
    USER = "user"
    LEGAL = "legal"
    SYSTEM = "system"


class RestrictionCategory(StrEnum):
    """Controlled category of an explicit ``BLOCKED`` restriction."""

    ACCOUNT_SUSPENDED = "account_suspended"
    TERMS_VIOLATION = "terms_violation"
    FRAUD_REVIEW = "fraud_review"
    LEGAL_HOLD = "legal_hold"
    USER_REQUEST = "user_request"
    UNKNOWN = "unknown"


# Existing retailer vocabulary from the ingestion contract. Reusing it avoids
# inventing retailer identifiers or capabilities in this phase.
#
# ``CARTEL_DEMO`` shares the platform vocabulary because synthetic observations
# must carry an explicit, non-retailer source identity. It is intentionally not a
# connectable retailer: it has no account, credential, adapter, acquisition, cart,
# or checkout capability.
SUPPORTED_RETAILER_IDS: Final[frozenset[str]] = frozenset(
    platform.value
    for platform in Platform
    if platform is not Platform.CARTEL_DEMO
)

# Non-secret references are code-shaped tokens, not free text. The same shape is
# enforced by CHECK constraints in the database.
REFERENCE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$"
)
AUTHENTICATION_METHOD_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z][a-z0-9_]{0,63}$"
)

# Audit event names. Idempotent repeats emit nothing; rejected transitions emit
# nothing; the service inserts these in the same transaction as the row change.
AUDIT_CREATED: Final[str] = "retailer_connection_created"
AUDIT_AUTHENTICATED: Final[str] = "retailer_connection_authenticated"
AUDIT_DEGRADED: Final[str] = "retailer_connection_degraded"
AUDIT_REAUTH_REQUIRED: Final[str] = "retailer_connection_reauth_required"
AUDIT_REVALIDATED: Final[str] = "retailer_connection_revalidated"
AUDIT_REVOKED: Final[str] = "retailer_connection_revoked"
AUDIT_BLOCKED: Final[str] = "retailer_connection_blocked"
AUDIT_DISCONNECTED: Final[str] = "retailer_connection_disconnected"


@dataclass(frozen=True)
class TransitionSpec:
    """One reviewed edge (or idempotent same-state repeat) in the table.

    ``from_state`` is ``None`` only for the creation edge. ``timestamps`` names
    the model columns that a real transition sets to the injected clock's now.
    ``connected_at`` is special-cased by the service: it is written only when it
    is currently null, so revalidation can never overwrite the first connection
    time. ``noop`` edges return the current record without mutating it.
    """

    from_state: RetailerConnectionStatus | None
    to_state: RetailerConnectionStatus
    reason: RetailerConnectionReason
    audit_event: str
    noop: bool = False
    timestamps: tuple[str, ...] = ()


def _edge(
    from_state: RetailerConnectionStatus | None,
    to_state: RetailerConnectionStatus,
    reason: RetailerConnectionReason,
    audit_event: str,
    *,
    noop: bool = False,
    timestamps: tuple[str, ...] = (),
) -> TransitionSpec:
    return TransitionSpec(
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        audit_event=audit_event,
        noop=noop,
        timestamps=timestamps,
    )


# ---------------------------------------------------------------------------
# Transition table
#
# Legal cross-state edges (ratified by Phase F.1):
#
# PENDING_AUTH -> CONNECTED        authentication completed
# PENDING_AUTH -> REAUTH_REQUIRED  authentication failed (not revocation)
# PENDING_AUTH -> BLOCKED          retailer blocked the account
# PENDING_AUTH -> REVOKED          explicit revocation
# PENDING_AUTH -> DISCONNECTED     user abandoned the connection
#
# CONNECTED -> DEGRADED            health degraded (network/partial failure)
# CONNECTED -> REAUTH_REQUIRED     authentication failed (not revocation)
# CONNECTED -> BLOCKED             retailer blocked the account
# CONNECTED -> REVOKED             explicit revocation
# CONNECTED -> DISCONNECTED        user disconnected
#
# DEGRADED -> CONNECTED            successful revalidation
# DEGRADED -> REAUTH_REQUIRED      authentication failed
# DEGRADED -> BLOCKED              retailer blocked the account
# DEGRADED -> REVOKED              explicit revocation
# DEGRADED -> DISCONNECTED         user disconnected
#
# REAUTH_REQUIRED -> CONNECTED     successful revalidation repaired auth
# REAUTH_REQUIRED -> BLOCKED       retailer blocked the account
# REAUTH_REQUIRED -> REVOKED       explicit revocation
# REAUTH_REQUIRED -> DISCONNECTED  user disconnected
#
# BLOCKED -> DISCONNECTED          user disconnected; no unblock edge is modeled
#
# REVOKED and DISCONNECTED are terminal. A reconnect
# creates a new record. This is why the partial unique index excludes both
# terminal states.
#
# Deliberately absent: any edge from a network/health failure directly to
# REVOKED, and any edge from an authentication failure directly to REVOKED.
# ---------------------------------------------------------------------------
TRANSITIONS: Final[tuple[TransitionSpec, ...]] = (
    # Creation is a mutating operation and lives in the same table as every
    # other mutation, even though it is not a state-to-state transition.
    _edge(
        None,
        RetailerConnectionStatus.PENDING_AUTH,
        RetailerConnectionReason.AUTHORIZATION_PENDING,
        AUDIT_CREATED,
    ),
    # Idempotent same-state repeats. Each state has exactly one canonical
    # entry reason; CONNECTED has two because both authentication completion
    # and revalidation can establish it.
    _edge(
        RetailerConnectionStatus.PENDING_AUTH,
        RetailerConnectionStatus.PENDING_AUTH,
        RetailerConnectionReason.AUTHORIZATION_PENDING,
        AUDIT_CREATED,
        noop=True,
    ),
    _edge(
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionReason.AUTHENTICATION_COMPLETED,
        AUDIT_AUTHENTICATED,
        noop=True,
    ),
    _edge(
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionReason.REVALIDATED,
        AUDIT_REVALIDATED,
        noop=True,
    ),
    _edge(
        RetailerConnectionStatus.DEGRADED,
        RetailerConnectionStatus.DEGRADED,
        RetailerConnectionReason.HEALTH_DEGRADED,
        AUDIT_DEGRADED,
        noop=True,
    ),
    _edge(
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerConnectionReason.AUTH_FAILED,
        AUDIT_REAUTH_REQUIRED,
        noop=True,
    ),
    _edge(
        RetailerConnectionStatus.REVOKED,
        RetailerConnectionStatus.REVOKED,
        RetailerConnectionReason.REVOKED,
        AUDIT_REVOKED,
        noop=True,
    ),
    _edge(
        RetailerConnectionStatus.BLOCKED,
        RetailerConnectionStatus.BLOCKED,
        RetailerConnectionReason.BLOCKED,
        AUDIT_BLOCKED,
        noop=True,
    ),
    _edge(
        RetailerConnectionStatus.DISCONNECTED,
        RetailerConnectionStatus.DISCONNECTED,
        RetailerConnectionReason.DISCONNECTED,
        AUDIT_DISCONNECTED,
        noop=True,
    ),
    # PENDING_AUTH exits.
    _edge(
        RetailerConnectionStatus.PENDING_AUTH,
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionReason.AUTHENTICATION_COMPLETED,
        AUDIT_AUTHENTICATED,
        timestamps=("connected_at", "last_validated_at"),
    ),
    _edge(
        RetailerConnectionStatus.PENDING_AUTH,
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerConnectionReason.AUTH_FAILED,
        AUDIT_REAUTH_REQUIRED,
        timestamps=("last_auth_failure_at", "reauth_required_at"),
    ),
    _edge(
        RetailerConnectionStatus.PENDING_AUTH,
        RetailerConnectionStatus.BLOCKED,
        RetailerConnectionReason.BLOCKED,
        AUDIT_BLOCKED,
    ),
    _edge(
        RetailerConnectionStatus.PENDING_AUTH,
        RetailerConnectionStatus.REVOKED,
        RetailerConnectionReason.REVOKED,
        AUDIT_REVOKED,
    ),
    _edge(
        RetailerConnectionStatus.PENDING_AUTH,
        RetailerConnectionStatus.DISCONNECTED,
        RetailerConnectionReason.DISCONNECTED,
        AUDIT_DISCONNECTED,
        timestamps=("disconnected_at",),
    ),
    # CONNECTED exits.
    _edge(
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionStatus.DEGRADED,
        RetailerConnectionReason.HEALTH_DEGRADED,
        AUDIT_DEGRADED,
    ),
    _edge(
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerConnectionReason.AUTH_FAILED,
        AUDIT_REAUTH_REQUIRED,
        timestamps=("last_auth_failure_at", "reauth_required_at"),
    ),
    _edge(
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionStatus.BLOCKED,
        RetailerConnectionReason.BLOCKED,
        AUDIT_BLOCKED,
    ),
    _edge(
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionStatus.REVOKED,
        RetailerConnectionReason.REVOKED,
        AUDIT_REVOKED,
    ),
    _edge(
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionStatus.DISCONNECTED,
        RetailerConnectionReason.DISCONNECTED,
        AUDIT_DISCONNECTED,
        timestamps=("disconnected_at",),
    ),
    # DEGRADED exits.
    _edge(
        RetailerConnectionStatus.DEGRADED,
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionReason.REVALIDATED,
        AUDIT_REVALIDATED,
        timestamps=("connected_at", "last_validated_at"),
    ),
    _edge(
        RetailerConnectionStatus.DEGRADED,
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerConnectionReason.AUTH_FAILED,
        AUDIT_REAUTH_REQUIRED,
        timestamps=("last_auth_failure_at", "reauth_required_at"),
    ),
    _edge(
        RetailerConnectionStatus.DEGRADED,
        RetailerConnectionStatus.BLOCKED,
        RetailerConnectionReason.BLOCKED,
        AUDIT_BLOCKED,
    ),
    _edge(
        RetailerConnectionStatus.DEGRADED,
        RetailerConnectionStatus.REVOKED,
        RetailerConnectionReason.REVOKED,
        AUDIT_REVOKED,
    ),
    _edge(
        RetailerConnectionStatus.DEGRADED,
        RetailerConnectionStatus.DISCONNECTED,
        RetailerConnectionReason.DISCONNECTED,
        AUDIT_DISCONNECTED,
        timestamps=("disconnected_at",),
    ),
    # REAUTH_REQUIRED exits.
    _edge(
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerConnectionStatus.CONNECTED,
        RetailerConnectionReason.REVALIDATED,
        AUDIT_REVALIDATED,
        timestamps=("connected_at", "last_validated_at"),
    ),
    _edge(
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerConnectionStatus.BLOCKED,
        RetailerConnectionReason.BLOCKED,
        AUDIT_BLOCKED,
    ),
    _edge(
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerConnectionStatus.REVOKED,
        RetailerConnectionReason.REVOKED,
        AUDIT_REVOKED,
    ),
    _edge(
        RetailerConnectionStatus.REAUTH_REQUIRED,
        RetailerConnectionStatus.DISCONNECTED,
        RetailerConnectionReason.DISCONNECTED,
        AUDIT_DISCONNECTED,
        timestamps=("disconnected_at",),
    ),
    # BLOCKED exits only to DISCONNECTED. No automatic unblock exists; an
    # explicitly authorized unblock transition is an unresolved policy cell.
    _edge(
        RetailerConnectionStatus.BLOCKED,
        RetailerConnectionStatus.DISCONNECTED,
        RetailerConnectionReason.DISCONNECTED,
        AUDIT_DISCONNECTED,
        timestamps=("disconnected_at",),
    ),
)

_INDEX: Final[dict[tuple[RetailerConnectionStatus | None, RetailerConnectionStatus, RetailerConnectionReason], TransitionSpec]] = {
    (spec.from_state, spec.to_state, spec.reason): spec for spec in TRANSITIONS
}

# One canonical reason per state, used for idempotent same-state repeats and by
# the full-matrix test. CONNECTED also accepts REVALIDATED for a same-state
# repeat; the table contains both entries.
_CANONICAL_REASON: Final[dict[RetailerConnectionStatus, RetailerConnectionReason]] = {
    RetailerConnectionStatus.PENDING_AUTH: RetailerConnectionReason.AUTHORIZATION_PENDING,
    RetailerConnectionStatus.CONNECTED: RetailerConnectionReason.AUTHENTICATION_COMPLETED,
    RetailerConnectionStatus.DEGRADED: RetailerConnectionReason.HEALTH_DEGRADED,
    RetailerConnectionStatus.REAUTH_REQUIRED: RetailerConnectionReason.AUTH_FAILED,
    RetailerConnectionStatus.REVOKED: RetailerConnectionReason.REVOKED,
    RetailerConnectionStatus.BLOCKED: RetailerConnectionReason.BLOCKED,
    RetailerConnectionStatus.DISCONNECTED: RetailerConnectionReason.DISCONNECTED,
}

TERMINAL_STATES: Final[frozenset[RetailerConnectionStatus]] = frozenset(
    {RetailerConnectionStatus.REVOKED, RetailerConnectionStatus.DISCONNECTED}
)

_PERMITTED = OperationPermission.PERMITTED
_DENIED = OperationPermission.DENIED
_DEFERRED = OperationPermission.DEFERRED

# Complete state-by-operation authorization matrix. Every state and every
# operation must appear exactly once; tests assert both dimensions.
#
# Rationale:
# * CONNECTED permits every operation subject to separate capability and
#   authorization checks.
# * DEGRADED keeps Cartel data and connection management available and permits
#   only bounded health/recovery checks. Normal retailer operations are denied.
# * REAUTH_REQUIRED keeps Cartel data and connection management available
#   (including user-initiated reauthentication/disconnect) but denies every
#   retailer operation, including health checks.
# * BLOCKED denies every retailer operation. Connection management is limited to
#   the explicit recovery path (disconnect); no automatic unblock exists.
# * REVOKED and DISCONNECTED deny every retailer operation.
# * DEFERRED cells are not specified by lifecycle policy and remain governed by
#   existing Cartel data / connection-metadata authorization.
OPERATION_MATRIX: Final[
    dict[RetailerConnectionStatus, dict[RetailerOperation, OperationPermission]]
] = {
    RetailerConnectionStatus.PENDING_AUTH: {
        RetailerOperation.CARTEL_DATA_ACCESS: _DEFERRED,
        RetailerOperation.CONNECTION_METADATA: _DEFERRED,
        RetailerOperation.RETAILER_HEALTH_CHECK: _DENIED,
        RetailerOperation.PRODUCT_DISCOVERY: _DENIED,
        RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: _DENIED,
        RetailerOperation.CART_PREPARATION: _DENIED,
        RetailerOperation.CHECKOUT: _DENIED,
    },
    RetailerConnectionStatus.CONNECTED: {
        RetailerOperation.CARTEL_DATA_ACCESS: _PERMITTED,
        RetailerOperation.CONNECTION_METADATA: _PERMITTED,
        RetailerOperation.RETAILER_HEALTH_CHECK: _PERMITTED,
        RetailerOperation.PRODUCT_DISCOVERY: _PERMITTED,
        RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: _PERMITTED,
        RetailerOperation.CART_PREPARATION: _PERMITTED,
        RetailerOperation.CHECKOUT: _PERMITTED,
    },
    RetailerConnectionStatus.DEGRADED: {
        RetailerOperation.CARTEL_DATA_ACCESS: _PERMITTED,
        RetailerOperation.CONNECTION_METADATA: _PERMITTED,
        RetailerOperation.RETAILER_HEALTH_CHECK: _PERMITTED,
        RetailerOperation.PRODUCT_DISCOVERY: _DENIED,
        RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: _DENIED,
        RetailerOperation.CART_PREPARATION: _DENIED,
        RetailerOperation.CHECKOUT: _DENIED,
    },
    RetailerConnectionStatus.REAUTH_REQUIRED: {
        RetailerOperation.CARTEL_DATA_ACCESS: _PERMITTED,
        RetailerOperation.CONNECTION_METADATA: _PERMITTED,
        RetailerOperation.RETAILER_HEALTH_CHECK: _DENIED,
        RetailerOperation.PRODUCT_DISCOVERY: _DENIED,
        RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: _DENIED,
        RetailerOperation.CART_PREPARATION: _DENIED,
        RetailerOperation.CHECKOUT: _DENIED,
    },
    RetailerConnectionStatus.BLOCKED: {
        RetailerOperation.CARTEL_DATA_ACCESS: _DEFERRED,
        RetailerOperation.CONNECTION_METADATA: _PERMITTED,
        RetailerOperation.RETAILER_HEALTH_CHECK: _DENIED,
        RetailerOperation.PRODUCT_DISCOVERY: _DENIED,
        RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: _DENIED,
        RetailerOperation.CART_PREPARATION: _DENIED,
        RetailerOperation.CHECKOUT: _DENIED,
    },
    RetailerConnectionStatus.REVOKED: {
        RetailerOperation.CARTEL_DATA_ACCESS: _DEFERRED,
        RetailerOperation.CONNECTION_METADATA: _DEFERRED,
        RetailerOperation.RETAILER_HEALTH_CHECK: _DENIED,
        RetailerOperation.PRODUCT_DISCOVERY: _DENIED,
        RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: _DENIED,
        RetailerOperation.CART_PREPARATION: _DENIED,
        RetailerOperation.CHECKOUT: _DENIED,
    },
    RetailerConnectionStatus.DISCONNECTED: {
        RetailerOperation.CARTEL_DATA_ACCESS: _DEFERRED,
        RetailerOperation.CONNECTION_METADATA: _DEFERRED,
        RetailerOperation.RETAILER_HEALTH_CHECK: _DENIED,
        RetailerOperation.PRODUCT_DISCOVERY: _DENIED,
        RetailerOperation.PRICE_AVAILABILITY_ACQUISITION: _DENIED,
        RetailerOperation.CART_PREPARATION: _DENIED,
        RetailerOperation.CHECKOUT: _DENIED,
    },
}

# record_successful_validation uses these targets for state-changing validation.
# CONNECTED is handled as a timestamp-only validation observation by the service
# (it is not a state transition, so the same-state no-op rule does not apply).
VALIDATION_TARGETS: Final[
    dict[
        RetailerConnectionStatus,
        tuple[RetailerConnectionStatus, RetailerConnectionReason],
    ]
] = {
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


def creation_spec() -> TransitionSpec:
    """Return the one creation edge (``None`` -> ``PENDING_AUTH``)."""

    return _INDEX[(None, RetailerConnectionStatus.PENDING_AUTH, RetailerConnectionReason.AUTHORIZATION_PENDING)]


def canonical_reason(status: RetailerConnectionStatus) -> RetailerConnectionReason:
    """Return the canonical entry/repeat reason for ``status``."""

    return _CANONICAL_REASON[status]


def lookup(
    from_state: RetailerConnectionStatus | None,
    to_state: RetailerConnectionStatus,
    reason: RetailerConnectionReason,
) -> TransitionSpec | None:
    """Return the table entry for an edge, or ``None`` when it is illegal."""

    return _INDEX.get((from_state, to_state, reason))


def permission_for(
    status: RetailerConnectionStatus,
    operation: RetailerOperation,
) -> OperationPermission:
    """Return the lifecycle permission for one state/operation cell."""

    return OPERATION_MATRIX[status][operation]


def operation_is_permitted(
    status: RetailerConnectionStatus,
    operation: RetailerOperation,
) -> bool:
    """Whether the lifecycle state permits ``operation`` outright.

    ``DEFERRED`` is deliberately false here: callers must run the existing
    Cartel data / connection-metadata authorization instead of treating the
    lifecycle layer as a grant.
    """

    return permission_for(status, operation) is OperationPermission.PERMITTED


def operation_requires_existing_authorization(
    status: RetailerConnectionStatus,
    operation: RetailerOperation,
) -> bool:
    """Whether this cell is decided by existing authorization, not lifecycle."""

    return permission_for(status, operation) is OperationPermission.DEFERRED


def authorize_operation(
    status: RetailerConnectionStatus,
    operation: RetailerOperation,
    *,
    existing_authorization: bool = False,
) -> None:
    """Enforce the operation matrix, raising a typed error on denial.

    ``existing_authorization`` is only consulted for ``DEFERRED`` cells. It is
    never a bypass for ``DENIED`` cells.
    """

    permission = permission_for(status, operation)
    if permission is OperationPermission.DENIED:
        raise RetailerOperationDenied(status=status, operation=operation)
    if permission is OperationPermission.DEFERRED and not existing_authorization:
        raise RetailerOperationRequiresExistingAuthorization(
            status=status,
            operation=operation,
        )


class RetailerConnectionError(Exception):
    """Base class for typed retailer-connection failures."""


class RetailerOperationDenied(RetailerConnectionError):
    """The lifecycle state unconditionally denies this operation."""

    def __init__(self, *, status: RetailerConnectionStatus, operation: RetailerOperation) -> None:
        self.status = status
        self.operation = operation
        super().__init__(
            f"retailer operation {operation.value} is denied in state {status.value}"
        )


class RetailerOperationRequiresExistingAuthorization(RetailerConnectionError):
    """Lifecycle policy defers this cell to existing Cartel authorization."""

    def __init__(self, *, status: RetailerConnectionStatus, operation: RetailerOperation) -> None:
        self.status = status
        self.operation = operation
        super().__init__(
            f"retailer operation {operation.value} in state {status.value} requires "
            "existing Cartel authorization"
        )


class RetailerConnectionNotFound(RetailerConnectionError):
    """Owner-scoped lookup found nothing (including another user's record)."""

    def __init__(self, connection_id: object) -> None:
        self.connection_id = connection_id
        super().__init__("retailer connection not found")


class RetailerConnectionAlreadyExists(RetailerConnectionError):
    """A non-terminal connection already exists for this user and retailer."""

    def __init__(self, *, user_id: object, retailer_id: str) -> None:
        self.user_id = user_id
        self.retailer_id = retailer_id
        super().__init__("an active retailer connection already exists")


class InvalidRetailerConnectionTransition(RetailerConnectionError):
    """The requested edge is not in the transition table."""

    def __init__(
        self,
        *,
        from_state: RetailerConnectionStatus,
        to_state: RetailerConnectionStatus,
        reason: RetailerConnectionReason,
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        super().__init__(
            f"invalid retailer connection transition: {from_state.value} -> "
            f"{to_state.value} ({reason.value})"
        )


class RetailerConnectionConflict(RetailerConnectionError):
    """A stale writer presented an expected version that is no longer current."""

    def __init__(self, *, connection_id: object, expected_version: int, actual_version: int) -> None:
        self.connection_id = connection_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            "retailer connection version conflict: expected "
            f"{expected_version}, found {actual_version}"
        )


class InvalidRetailerConnectionInput(RetailerConnectionError):
    """A caller supplied a value outside the constrained domain vocabulary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"invalid retailer connection input: {code}")
