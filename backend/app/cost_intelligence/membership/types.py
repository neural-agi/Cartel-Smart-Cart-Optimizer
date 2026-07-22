from __future__ import annotations

from enum import StrEnum


class MembershipType(StrEnum):
    """Supported deterministic membership interpretations."""

    ENTITLEMENT = "entitlement"
    BENEFIT = "benefit"
    UNKNOWN = "unknown"
