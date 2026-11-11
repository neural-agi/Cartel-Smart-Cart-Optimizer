"""Explicit request and response schemas for retailer connection management.

These schemas are the disclosure boundary for the HTTP API. They contain only
lifecycle metadata that is safe to show to the owning user. They deliberately
exclude vault references, secret material, ciphertext, nonces, key versions,
external authorization references, and internal audit payloads.

The request schema is intentionally minimal: a caller may supply a retailer
identifier and nothing else. Credential material is rejected by ``extra="forbid"``
before it reaches the domain service.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.retailer_connections.lifecycle import (
    SUPPORTED_RETAILER_IDS,
    OperationPermission,
    RetailerConnectionStatus,
)


class RetailerConnectionCreate(BaseModel):
    """Create a PENDING_AUTH connection for the authenticated Cartel user.

    There is deliberately no password, OTP, cookie, token, authorization
    reference, or authentication-method field. Creating a connection record is
    not retailer authentication.
    """

    model_config = ConfigDict(extra="forbid")

    retailer_id: str = Field(min_length=1, max_length=32)

    @field_validator("retailer_id")
    @classmethod
    def validate_retailer_id(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in SUPPORTED_RETAILER_IDS:
            # Do not echo the supplied value; it may contain arbitrary input.
            raise ValueError("unsupported retailer identifier")
        return normalized


class RetailerConnectionCapabilities(BaseModel):
    """Lifecycle permission for each distinct operation class.

    ``deferred`` means the lifecycle policy does not grant or deny the cell;
    existing Cartel authorization decides. It must never be read as permitted.
    """

    cartel_data_access: OperationPermission
    connection_metadata: OperationPermission
    retailer_health_check: OperationPermission
    product_discovery: OperationPermission
    price_availability_acquisition: OperationPermission
    cart_preparation: OperationPermission
    checkout: OperationPermission


class RetailerConnectionResponse(BaseModel):
    """Allowlisted, non-secret view of one retailer connection.

    The four booleans keep the distinct concepts separate:

    * ``cartel_account_authenticated`` - the Cartel session is authenticated.
    * ``retailer_connection_exists`` - a lifecycle record exists.
    * ``retailer_authenticated`` - the retailer authorization is currently
      usable (only CONNECTED or DEGRADED).
    * ``retailer_operational`` - normal retailer operations are permitted
      (only CONNECTED).
    """

    id: UUID
    retailer_id: str
    status: RetailerConnectionStatus
    authentication_method: str | None
    connected_at: datetime | None
    last_validated_at: datetime | None
    reauthorization_required: bool
    capabilities: RetailerConnectionCapabilities
    cartel_account_authenticated: bool
    retailer_connection_exists: bool
    retailer_authenticated: bool
    retailer_operational: bool
    created_at: datetime
    updated_at: datetime
