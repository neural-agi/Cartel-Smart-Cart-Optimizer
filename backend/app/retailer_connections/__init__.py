"""Retailer connection lifecycle domain (persistence and state only).

This package deliberately contains no retailer authentication, credential
storage, acquisition, or HTTP surface. It models the durable lifecycle of a
user's connection to a retailer so later phases can attach those concerns to a
reviewed state machine.
"""

from app.retailer_connections.lifecycle import (
    AUTHENTICATION_METHOD_PATTERN,
    OPERATION_MATRIX,
    REFERENCE_PATTERN,
    SUPPORTED_RETAILER_IDS,
    InvalidRetailerConnectionInput,
    InvalidRetailerConnectionTransition,
    OperationPermission,
    RestrictionCategory,
    RestrictionSource,
    RetailerConnectionAlreadyExists,
    RetailerConnectionConflict,
    RetailerConnectionNotFound,
    RetailerConnectionReason,
    RetailerConnectionStatus,
    RetailerOperation,
    RetailerOperationDenied,
    RetailerOperationRequiresExistingAuthorization,
    TransitionSpec,
    authorize_operation,
    canonical_reason,
    creation_spec,
    lookup,
    operation_is_permitted,
    operation_requires_existing_authorization,
    permission_for,
)

__all__ = [
    "AUTHENTICATION_METHOD_PATTERN",
    "OPERATION_MATRIX",
    "REFERENCE_PATTERN",
    "SUPPORTED_RETAILER_IDS",
    "InvalidRetailerConnectionInput",
    "InvalidRetailerConnectionTransition",
    "OperationPermission",
    "RestrictionCategory",
    "RestrictionSource",
    "RetailerConnectionAlreadyExists",
    "RetailerConnectionConflict",
    "RetailerConnectionNotFound",
    "RetailerConnectionReason",
    "RetailerConnectionStatus",
    "RetailerOperation",
    "RetailerOperationDenied",
    "RetailerOperationRequiresExistingAuthorization",
    "TransitionSpec",
    "authorize_operation",
    "canonical_reason",
    "creation_spec",
    "lookup",
    "operation_is_permitted",
    "operation_requires_existing_authorization",
    "permission_for",
]
