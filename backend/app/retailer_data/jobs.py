"""Bounded retailer acquisition job construction over the existing ScrapeJob."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.data_ingestion.enums import CaptureType, DownstreamMode, Platform
from app.data_ingestion.types import CaptureContext, RequestParameters, ScrapeJob


class RetailerAcquisitionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: Platform
    query: str = Field(min_length=1, max_length=200)
    country_code: str = Field(min_length=2, max_length=2)
    currency_code: str = Field(min_length=3, max_length=3)
    locale: str = Field(min_length=2, max_length=32)
    location_scope: str = Field(min_length=1, max_length=128)
    session_scope: str = Field(min_length=1, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=128)


class RetailerAcquisitionIdempotencyConflict(ValueError):
    """An idempotency key was reused for a different acquisition request."""


def build_retailer_acquisition_job(request: RetailerAcquisitionRequest) -> ScrapeJob:
    """Create the existing deterministic job identity for at-least-once execution."""

    parameters = [("query", request.query.strip()), ("retailer_only", "true")]
    if request.idempotency_key:
        parameters.insert(0, ("idempotency_key", request.idempotency_key.strip()))
    return ScrapeJob(
        platform=request.provider,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=tuple(parameters)),
        capture_context=CaptureContext(
            country_code=request.country_code.upper(),
            currency_code=request.currency_code.upper(),
            locale=request.locale,
            location_scope=request.location_scope,
            session_scope=request.session_scope,
        ),
        parser_policy_version="blinkit-parser-v1" if request.provider is Platform.BLINKIT else "retailer-parser-v1",
        normalization_policy_version="normalizer-v1",
        downstream_mode=DownstreamMode.PRODUCT_INTELLIGENCE,
        job_contract_version="retailer-acquisition-v1",
    )


class FilesystemRetailerAcquisitionSubmissionStore:
    """Persist bounded submission idempotency beside the existing job lifecycle data."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir / "retailer-acquisition-idempotency"
        self._root.mkdir(parents=True, exist_ok=True)

    def submit(self, request: RetailerAcquisitionRequest) -> ScrapeJob:
        if not request.idempotency_key or not request.idempotency_key.strip():
            return build_retailer_acquisition_job(request)
        job = build_retailer_acquisition_job(request)
        key = hashlib.sha256(request.idempotency_key.strip().encode("utf-8")).hexdigest()
        path = self._root / f"{key}.json"
        fingerprint = self._fingerprint(request)
        record = {"fingerprint": fingerprint, "job_id": job.job_id}
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing.get("fingerprint") != fingerprint or existing.get("job_id") != job.job_id:
                raise RetailerAcquisitionIdempotencyConflict(
                    "idempotency key was already used for a different retailer acquisition"
                )
            return job
        temporary = None
        try:
            fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            temporary = Path(temporary_name)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(record, handle, sort_keys=True, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return job

    @staticmethod
    def _fingerprint(request: RetailerAcquisitionRequest) -> str:
        payload = request.model_dump(mode="json", exclude={"idempotency_key"})
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
