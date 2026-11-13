"""Executor-minted authorization tokens for adapter invocation.

The token is the only way an adapter operation can learn that the shared
enforcement path has resolved the connection, checked ownership, enforced the
lifecycle matrix, verified the capability declaration, and resolved the
adapter's declared secrets. Constructing a token requires the module-private
sentinel held by the executor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.retailer_adapters.contracts import (
    AdapterCapability,
    UnauthorizedAdapterInvocation,
)
from app.retailer_adapters.credentials import RetailerCredentialBundle
from app.retailer_connections.lifecycle import (
    RetailerConnectionStatus,
    RetailerOperation,
)

_EXECUTOR_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class AuthorizedRetailerOperation:
    """Proof that one adapter operation passed the shared enforcement path."""

    user_id: UUID
    connection_id: UUID
    retailer_id: str
    lifecycle_status: RetailerConnectionStatus
    capability: AdapterCapability
    adapter_id: str
    lifecycle_operation: RetailerOperation
    request_id: str | None
    _sentinel: object = field(repr=False, compare=False)
    credentials: RetailerCredentialBundle = field(
        default_factory=lambda: RetailerCredentialBundle({}),
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self._sentinel is not _EXECUTOR_SENTINEL:
            raise UnauthorizedAdapterInvocation(
                "adapter operations may only be authorized by the shared executor"
            )

    def authorizes(
        self,
        *,
        adapter_id: str,
        retailer_id: str,
        capability: AdapterCapability,
    ) -> bool:
        return (
            self.adapter_id == adapter_id
            and self.retailer_id == retailer_id
            and self.capability is capability
        )


__all__ = ["AuthorizedRetailerOperation"]
