"""Immutable contracts for deterministic scrape-job ingestion."""

from app.data_ingestion.enums import (
    AttemptOutcome,
    CaptureType,
    DownstreamMode,
    FailureCategory,
    JobState,
    Platform,
)
from app.data_ingestion.types import (
    CaptureContext,
    JobCancellation,
    JobFailure,
    LifecycleTransition,
    RawArtifactReference,
    ReplayReference,
    RequestParameters,
    ScrapeAttempt,
    ScrapeJob,
)

__all__ = [
    "AttemptOutcome",
    "CaptureContext",
    "CaptureType",
    "DownstreamMode",
    "FailureCategory",
    "JobCancellation",
    "JobFailure",
    "JobState",
    "LifecycleTransition",
    "Platform",
    "RawArtifactReference",
    "ReplayReference",
    "RequestParameters",
    "ScrapeAttempt",
    "ScrapeJob",
]
