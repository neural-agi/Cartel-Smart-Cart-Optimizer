"""Provider-independent credential vault (AEAD storage only).

This package contains no retailer authentication, OAuth callback, browser
automation, acquisition, checkout, or HTTP surface. It stores opaque secret
material encrypted at rest and bound to a persisted retailer connection.

``CredentialVault`` is exported lazily so importing the ORM model (which needs
:mod:`app.credential_vault.types` and :mod:`app.credential_vault.crypto`) does
not pull the service and its model imports into a partially initialized
package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.credential_vault.types import (
    CredentialVaultError,
    SecretMetadata,
    SecretOwner,
    SecretReference,
    SecretStatus,
    SecretType,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.credential_vault.service import CredentialVault

__all__ = [
    "CredentialVault",
    "CredentialVaultError",
    "SecretMetadata",
    "SecretOwner",
    "SecretReference",
    "SecretStatus",
    "SecretType",
]


def __getattr__(name: str) -> Any:
    if name == "CredentialVault":
        from app.credential_vault.service import CredentialVault

        return CredentialVault
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
