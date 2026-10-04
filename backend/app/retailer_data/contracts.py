"""Typed boundary between retailer data providers and governed ingestion.

Providers produce acquisition evidence, not canonical products. The existing
parser, observation registry, identity resolver, and catalog remain the only
path to consumer-searchable records.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.data_ingestion import AcquisitionResult, Platform, ScrapeJob


class RetailerAcquisitionOutcome(StrEnum):
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    UNAUTHORIZED = "unauthorized"
    ACCESS_DENIED = "access_denied"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    PROVIDER_ERROR = "provider_error"
    INVALID_RESPONSE = "invalid_response"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    LOCATION_UNAVAILABLE = "location_unavailable"


class AcquisitionMethod(StrEnum):
    OFFICIAL_API = "official_api"
    AUTHORIZED_BROWSER = "authorized_browser"
    AUTHORIZED_THIRD_PARTY = "authorized_third_party"
    OPERATOR_EVIDENCE = "operator_evidence"


class EvidenceQuality(StrEnum):
    AUTHORITATIVE = "authoritative"
    OPERATOR_VERIFIED = "operator_verified"
    INSUFFICIENT = "insufficient"


class RequestExecutionState(StrEnum):
    """Whether the provider request reached an HTTP response boundary."""

    NOT_ATTEMPTED = "request_not_attempted"
    ATTEMPTED_NO_RESPONSE = "request_attempted_no_response"
    HTTP_RESPONSE_RECEIVED = "http_response_received"


class LocationScope(BaseModel):
    """A non-global delivery context for a retailer observation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    country_code: str
    locality: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    scope_id: str

    @field_validator("country_code", "scope_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip() or value.strip() == "*":
            raise ValueError("location scope fields must be non-global and non-empty")
        return value.strip()

    @field_validator("locality", "postal_code")
    @classmethod
    def _optional_non_empty(cls, value: str | None) -> str | None:
        return None if value is None else value.strip() or None

    @model_validator(mode="after")
    def _has_context(self) -> "LocationScope":
        if not any((self.locality, self.postal_code, self.latitude is not None and self.longitude is not None)):
            raise ValueError("location scope must identify a locality, postal code, or coordinate pair")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be supplied together")
        return self


class RetailerAcquisitionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    retailer: Platform
    provider_id: str
    method: AcquisitionMethod
    location: LocationScope
    job: ScrapeJob

    @field_validator("provider_id")
    @classmethod
    def _provider_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provider_id must be non-empty")
        return value.strip()

    @model_validator(mode="after")
    def _job_scope(self) -> "RetailerAcquisitionRequest":
        if self.job.platform is not self.retailer:
            raise ValueError("job platform must match retailer")
        if self.job.capture_context.location_scope != self.location.scope_id:
            raise ValueError("job location_scope must match provider location scope")
        return self


class RetailerAcquisitionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    outcome: RetailerAcquisitionOutcome
    retailer: Platform
    provider_id: str
    method: AcquisitionMethod
    location: LocationScope
    evidence_quality: EvidenceQuality
    acquisition: AcquisitionResult | None = None
    reason_code: str | None = None
    diagnostic: str | None = None
    observed_at: datetime | None = None
    request_state: RequestExecutionState = RequestExecutionState.NOT_ATTEMPTED

    @model_validator(mode="after")
    def _outcome_contract(self) -> "RetailerAcquisitionResult":
        if self.outcome is RetailerAcquisitionOutcome.SUCCESS:
            if self.acquisition is None or self.evidence_quality is EvidenceQuality.INSUFFICIENT:
                raise ValueError("successful acquisition requires sufficient evidence")
            if self.acquisition.payload == b"":
                raise ValueError("successful acquisition payload cannot be empty")
        elif self.acquisition is not None:
            raise ValueError("failed acquisition must not carry retailer evidence")
        if self.outcome is not RetailerAcquisitionOutcome.SUCCESS and not (self.reason_code or self.diagnostic):
            raise ValueError("failed acquisition requires a reason")
        return self
