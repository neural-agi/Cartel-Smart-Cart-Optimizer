"""Capture-timestamp integrity rules shared by ingestion and read paths.

This module answers one question: is a retailer capture timestamp admissible
temporal evidence? It does not implement freshness policy, expiration, or
lineage supersession. Valid timestamps are preserved as the same instant in
UTC; naive timestamps are never interpreted as UTC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class CaptureTimestampRejectionReason(StrEnum):
    """Machine-readable reasons a capture timestamp is inadmissible."""

    naive = "naive"
    future = "future"
    malformed = "malformed"


class Clock(Protocol):
    """Injected time source for capture-timestamp validation."""

    def now(self) -> datetime: ...


class SystemClock:
    """Default production clock; always returns an aware UTC instant."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class CaptureTimestampRejection(BaseModel):
    """Typed quarantine outcome for an inadmissible capture timestamp.

    The outcome carries only the artifact identifier and a machine-readable
    reason. It never carries payload bytes, credentials, or source secrets.
    """

    model_config = ConfigDict(frozen=True)

    artifact_id: str
    reason: CaptureTimestampRejectionReason
    detail: str


class InvalidCaptureTimestamp(ValueError):
    """Raised when a capture timestamp fails integrity validation.

    Deriving from ``ValueError`` matches the existing ingestion convention used
    by ``ObservationRegistrationConflict`` and pydantic field validators.
    """

    def __init__(self, rejection: CaptureTimestampRejection) -> None:
        self.rejection = rejection
        super().__init__(
            "invalid capture timestamp for artifact "
            f"{rejection.artifact_id!r}: {rejection.reason.value}"
        )


def _clock_now(clock: Clock) -> datetime:
    now = clock.now()
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")
    return now.astimezone(timezone.utc)


def require_timezone_aware(value: datetime) -> datetime:
    """Reject naive datetimes and return the same instant normalized to UTC.

    Used by construction-time model validators, which do not have a clock.
    """

    if not isinstance(value, datetime):
        raise ValueError("capture_timestamp must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("capture_timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def normalize_capture_timestamp(
    value: datetime,
    *,
    artifact_id: str,
    clock: Clock,
) -> datetime:
    """Validate and normalize one capture timestamp.

    Rules:
    - naive or non-datetime values are rejected as ``naive``/``malformed``;
    - aware values are preserved as the same instant in UTC;
    - a timestamp strictly greater than the injected clock's now is rejected as
      ``future``. Equal-to-now is accepted so a provider that stamps then
      validates in the same instant does not self-reject.
    """

    if not isinstance(value, datetime):
        raise InvalidCaptureTimestamp(
            CaptureTimestampRejection(
                artifact_id=artifact_id,
                reason=CaptureTimestampRejectionReason.malformed,
                detail="capture_timestamp must be a datetime",
            )
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidCaptureTimestamp(
            CaptureTimestampRejection(
                artifact_id=artifact_id,
                reason=CaptureTimestampRejectionReason.naive,
                detail="capture_timestamp must be timezone-aware",
            )
        )
    normalized = value.astimezone(timezone.utc)
    if normalized > _clock_now(clock):
        raise InvalidCaptureTimestamp(
            CaptureTimestampRejection(
                artifact_id=artifact_id,
                reason=CaptureTimestampRejectionReason.future,
                detail="capture_timestamp cannot be in the future",
            )
        )
    return normalized
