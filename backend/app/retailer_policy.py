"""Phase J.1.1 retailer policy boundary.

Blinkit is intentionally unavailable until written commercial-use
authorization is recorded outside this codebase. This is deliberately not
configuration-driven: an environment variable, feature flag, or admin setting
must not turn the restriction back on accidentally.

The boundary is intentionally narrow: it contains only the Blinkit decision and
does not attempt to model other retailers' authorization.
"""

from enum import StrEnum
from urllib.parse import urlsplit

BLINKIT_RETAILER_ID = "BLINKIT"
POLICY_VERSION = "phase-j.1.1-blinkit-blocked-v1"
POLICY_REASON_CODE = "blinkit_commercial_authorization_required"

_BLINKIT_IDENTIFIERS = frozenset(
    {
        "blinkit",
        "blinkit.com",
        "www.blinkit.com",
        "blinkit.in",
        "www.blinkit.in",
    }
)


class RetailerPolicyStatus(StrEnum):
    BLOCKED = "BLOCKED"
    ALLOWED = "ALLOWED"


class RetailerPolicyBlocked(RuntimeError):
    status = RetailerPolicyStatus.BLOCKED
    reason_code = POLICY_REASON_CODE
    policy_version = POLICY_VERSION

    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(
            f"Blinkit {operation} is blocked pending written commercial-use authorization"
        )


def _normalized_identity(retailer_id: object) -> str:
    if not isinstance(retailer_id, str):
        return ""
    text = retailer_id.strip()
    if not text:
        return ""
    if "://" in text:
        try:
            return (urlsplit(text).hostname or "").casefold()
        except ValueError:
            return ""
    return text.split("/", 1)[0].casefold()


def is_blinkit(retailer_id: object) -> bool:
    """Return whether an identity, enum, host, or URL refers to Blinkit."""

    normalized = _normalized_identity(retailer_id)
    if not normalized:
        return False
    if normalized in _BLINKIT_IDENTIFIERS:
        return True
    if normalized.endswith((".blinkit.com", ".blinkit.in")):
        return True
    # Blinkit-specific provider/adapter identifiers such as "blinkit-native".
    return normalized.startswith(("blinkit-", "blinkit_"))


def ensure_retailer_allowed(retailer_id: object, operation: str) -> None:
    if is_blinkit(retailer_id):
        raise RetailerPolicyBlocked(operation)


def blinkit_consumer_eligible() -> bool:
    return False


__all__ = [
    "BLINKIT_RETAILER_ID",
    "POLICY_REASON_CODE",
    "POLICY_VERSION",
    "RetailerPolicyBlocked",
    "RetailerPolicyStatus",
    "blinkit_consumer_eligible",
    "ensure_retailer_allowed",
    "is_blinkit",
]
