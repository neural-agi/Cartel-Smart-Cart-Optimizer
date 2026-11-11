"""Shared enforcement path for every retailer adapter operation.

The executor is the only component allowed to mint an authorization token. It
resolves the persisted connection, checks ownership, enforces the lifecycle
matrix, verifies the adapter's declared capability, resolves secrets through the
vault, and runs the operation inside the bounded resilience guard.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.credential_vault.service import CredentialVault
from app.credential_vault.types import (
    CredentialVaultError,
    SecretAccessDenied,
    SecretNotFound,
    SecretOwner,
    SecretType,
    VaultKeyUnavailable,
    VaultUnavailable,
)
from app.db.models.retailer_connections import RetailerConnection
from app.retailer_adapters.authorization import (
    _EXECUTOR_SENTINEL,
    AuthorizedRetailerOperation,
)
from app.retailer_adapters.capabilities import CAPABILITY_OPERATIONS
from app.retailer_adapters.contracts import (
    AdapterCapability,
    AdapterOperationResult,
    AdapterOutcome,
    CapabilityStatus,
    InvalidAdapterOperation,
    failure_result,
    request_type_for,
)
from app.retailer_adapters.credentials import (
    CredentialResolver,
    MissingCredentialMaterial,
    RetailerCredentialBundle,
    VaultCredentialResolver,
    redact_log_fields,
)
from app.retailer_adapters.registry import (
    RetailerAdapterResolver,
    UnknownRetailerAdapter,
)
from app.retailer_adapters.resilience import (
    ExecutionFailure,
    ExecutionPolicy,
    RetailerExecutionGuard,
)
from app.retailer_connections import service
from app.retailer_connections.lifecycle import (
    RetailerConnectionNotFound,
    RetailerConnectionStatus,
    RetailerOperation,
    RetailerOperationDenied,
    RetailerOperationRequiresExistingAuthorization,
    authorize_operation,
)
from app.retailer_policy import is_blinkit

logger = get_logger(__name__)

_USER_ACTION_STATES = frozenset(
    {
        RetailerConnectionStatus.PENDING_AUTH,
        RetailerConnectionStatus.REAUTH_REQUIRED,
    }
)

_STATE_REASON_CODES = {
    RetailerConnectionStatus.PENDING_AUTH: "authentication_pending",
    RetailerConnectionStatus.REAUTH_REQUIRED: "reauthorization_required",
    RetailerConnectionStatus.BLOCKED: "connection_blocked",
    RetailerConnectionStatus.REVOKED: "connection_revoked",
    RetailerConnectionStatus.DISCONNECTED: "connection_disconnected",
    RetailerConnectionStatus.DEGRADED: "connection_degraded",
}


class RetailerAdapterExecutor:
    """Authorize and execute adapter operations behind one shared boundary."""

    def __init__(
        self,
        *,
        registry: RetailerAdapterResolver,
        vault: CredentialVault | None = None,
        credential_resolver: CredentialResolver | None = None,
        guard: RetailerExecutionGuard | None = None,
        policy: ExecutionPolicy | None = None,
    ) -> None:
        if vault is not None and credential_resolver is not None:
            raise ValueError("provide either vault or credential_resolver, not both")
        self._registry = registry
        if credential_resolver is not None:
            self._credentials = credential_resolver
        elif vault is not None:
            self._credentials = VaultCredentialResolver(vault)
        else:
            self._credentials = None
        self._guard = guard or RetailerExecutionGuard(policy=policy)

    async def execute(
        self,
        db: Session,
        *,
        user_id: UUID,
        connection_id: UUID,
        capability: AdapterCapability | str,
        request: object,
        adapter_id: str | None = None,
        request_id: str | None = None,
    ) -> AdapterOperationResult:
        cap = _coerce_capability(capability)
        expected = request_type_for(cap)
        if not isinstance(request, expected):
            raise InvalidAdapterOperation(
                f"{cap.value} requires {expected.__name__}"
            )

        try:
            connection = service.get_connection(
                db,
                user_id=user_id,
                connection_id=connection_id,
            )
        except RetailerConnectionNotFound:
            return failure_result(
                cap,
                AdapterOutcome.ACCESS_DENIED,
                reason_code="connection_not_found",
            )

        retailer_id = connection.retailer_id
        if is_blinkit(retailer_id):
            return failure_result(cap, AdapterOutcome.POLICY_BLOCKED, reason_code="blinkit_commercial_authorization_required")
        try:
            adapter = self._registry.resolve(retailer_id)
        except UnknownRetailerAdapter:
            return failure_result(
                cap,
                AdapterOutcome.UNSUPPORTED,
                reason_code="adapter_not_registered",
            )

        if adapter_id is not None and adapter_id != adapter.adapter_id:
            return failure_result(
                cap,
                AdapterOutcome.ACCESS_DENIED,
                reason_code="adapter_mismatch",
            )

        status = RetailerConnectionStatus(connection.status)
        operation = CAPABILITY_OPERATIONS[cap]
        try:
            authorize_operation(status, operation)
        except RetailerOperationDenied:
            outcome = (
                AdapterOutcome.REQUIRES_USER_ACTION
                if status in _USER_ACTION_STATES
                else AdapterOutcome.ACCESS_DENIED
            )
            return failure_result(
                cap,
                outcome,
                reason_code=_STATE_REASON_CODES.get(status, "lifecycle_denied"),
            )
        except RetailerOperationRequiresExistingAuthorization:
            return failure_result(
                cap,
                AdapterOutcome.ACCESS_DENIED,
                reason_code="existing_authorization_required",
            )

        declaration = adapter.capabilities.declaration_for(cap)
        if declaration.status is not CapabilityStatus.SUPPORTED:
            outcome = (
                AdapterOutcome.REQUIRES_USER_ACTION
                if declaration.status is CapabilityStatus.REQUIRES_USER_ACTION
                else AdapterOutcome.UNSUPPORTED
            )
            return failure_result(
                cap,
                outcome,
                reason_code=declaration.reason_code or "capability_unavailable",
            )

        try:
            credentials = self._resolve_credentials(
                db,
                connection=connection,
                operation=operation,
                secret_types=adapter.required_secret_types(cap),
            )
        except ExecutionFailure as exc:
            return failure_result(
                cap,
                exc.outcome,
                reason_code=exc.reason_code,
                diagnostic=exc.diagnostic,
            )

        authorization = AuthorizedRetailerOperation(
            user_id=user_id,
            connection_id=connection.id,
            retailer_id=retailer_id,
            lifecycle_status=status,
            capability=cap,
            adapter_id=adapter.adapter_id,
            lifecycle_operation=operation,
            request_id=request_id,
            _sentinel=_EXECUTOR_SENTINEL,
            credentials=credentials,
        )

        try:
            result = await self._guard.run(
                retailer_id=retailer_id,
                capability=cap,
                call=lambda: adapter.execute(authorization, cap, request),
                policy=adapter.execution_policy,
            )
        except ExecutionFailure as exc:
            result = failure_result(
                cap,
                exc.outcome,
                reason_code=exc.reason_code,
                diagnostic=exc.diagnostic,
            )

        self._log(
            retailer_id=retailer_id,
            adapter_id=adapter.adapter_id,
            capability=cap,
            connection_id=connection.id,
            request_id=request_id,
            result=result,
        )
        return result

    def _resolve_credentials(
        self,
        db: Session,
        *,
        connection: RetailerConnection,
        operation: RetailerOperation,
        secret_types: tuple[SecretType, ...],
    ) -> RetailerCredentialBundle:
        required = tuple(dict.fromkeys(secret_types))
        if not required:
            return RetailerCredentialBundle({})
        if self._credentials is None:
            raise ExecutionFailure(
                AdapterOutcome.TEMPORARY_FAILURE,
                reason_code="credential_vault_unavailable",
            )
        owner = SecretOwner(
            user_id=connection.user_id,
            connection_id=connection.id,
            retailer_id=connection.retailer_id,
        )
        try:
            return self._credentials.resolve(
                db,
                owner=owner,
                operation=operation,
                secret_types=required,
            )
        except MissingCredentialMaterial:
            raise ExecutionFailure(
                AdapterOutcome.REQUIRES_USER_ACTION,
                reason_code="missing_credential",
            ) from None
        except SecretAccessDenied:
            raise ExecutionFailure(
                AdapterOutcome.ACCESS_DENIED,
                reason_code="credential_access_denied",
            ) from None
        except SecretNotFound:
            raise ExecutionFailure(
                AdapterOutcome.ACCESS_DENIED,
                reason_code="credential_binding_mismatch",
            ) from None
        except (VaultUnavailable, VaultKeyUnavailable):
            raise ExecutionFailure(
                AdapterOutcome.TEMPORARY_FAILURE,
                reason_code="credential_vault_unavailable",
            ) from None
        except CredentialVaultError:
            raise ExecutionFailure(
                AdapterOutcome.TEMPORARY_FAILURE,
                reason_code="credential_vault_error",
            ) from None

    @staticmethod
    def _log(
        *,
        retailer_id: str,
        adapter_id: str,
        capability: AdapterCapability,
        connection_id: object,
        request_id: str | None,
        result: AdapterOperationResult,
    ) -> None:
        logger.info(
            "retailer_adapter_operation",
            extra=redact_log_fields(
                {
                    "component": "retailer_adapters",
                    "retailer_id": retailer_id,
                    "adapter_id": adapter_id,
                    "capability": capability.value,
                    "outcome": result.outcome.value,
                    "reason_code": result.reason_code,
                    "connection_id": str(connection_id),
                    "request_id": request_id,
                    "attempt_count": (
                        None if result.acquisition is None else result.acquisition.attempt_count
                    ),
                }
            ),
        )


def _coerce_capability(value: AdapterCapability | str) -> AdapterCapability:
    try:
        return AdapterCapability(value)
    except ValueError as exc:
        raise InvalidAdapterOperation(
            f"unknown adapter capability: {value!r}"
        ) from exc


__all__ = ["RetailerAdapterExecutor"]
