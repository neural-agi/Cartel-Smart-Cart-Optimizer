"""Validated local retailer evidence input for the existing ingestion runtime."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.data_ingestion import AcquisitionResult, CaptureCoverage, CaptureType
from app.schemas.extraction import RawExtractionResult
from app.scrapers.blinkit.parser import BlinkitProductParser

MAX_EVIDENCE_BYTES = 10 * 1024 * 1024


class OperatorEvidenceManifest(BaseModel):
    """Sidecar describing one operator-captured, sanitized Blinkit page artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    retailer: Literal["BLINKIT"]
    sanitized_capture: Literal[True]
    source_reference: str
    captured_at: datetime
    capture_type: Literal["SEARCH_RESULTS", "PRODUCT_DETAIL"]
    content_type: Literal["text/html"]
    payload_file: str
    payload_sha256: str
    location_scope: str
    query: str | None = None
    coverage: CaptureCoverage

    @field_validator("source_reference")
    @classmethod
    def validate_source_reference(cls, value: str) -> str:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("source_reference must be a valid Blinkit URL") from exc
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"blinkit.com", "www.blinkit.com"}
            or port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ValueError("source_reference must be an HTTPS Blinkit URL without credentials or fragment")
        return value

    @field_validator("payload_file", "location_scope")
    @classmethod
    def validate_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence metadata must not be blank")
        return value

    @field_validator("payload_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("payload_sha256 must be a lowercase SHA-256 digest")
        return value

    @field_validator("captured_at")
    @classmethod
    def validate_capture_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must include a timezone")
        if value.astimezone(timezone.utc) > datetime.now(timezone.utc):
            raise ValueError("captured_at cannot be in the future")
        return value

    @model_validator(mode="after")
    def validate_capture_context(self) -> "OperatorEvidenceManifest":
        if self.capture_type == "SEARCH_RESULTS" and not (self.query and self.query.strip()):
            raise ValueError("search evidence requires its observed query")
        try:
            parsed = urlsplit(self.source_reference)
        except ValueError as exc:
            raise ValueError("source_reference must be a valid Blinkit URL") from exc
        if self.capture_type == "SEARCH_RESULTS":
            if parsed.path not in {"/s", "/s/"}:
                raise ValueError("search evidence must come from the Blinkit search route")
            if not parsed.query:
                raise ValueError("search evidence source URL must retain its observed query")
            from urllib.parse import parse_qsl

            query_parameters = parse_qsl(parsed.query, keep_blank_values=True)
            if any(key != "q" for key, _ in query_parameters):
                raise ValueError("search source URL may retain only the observed q parameter")
        else:
            if parsed.query:
                raise ValueError("product-detail source URL must not contain query parameters")
            if not re.fullmatch(r"/prn/[^/]+/prid/[^/?#]+", parsed.path):
                raise ValueError("product-detail evidence must come from a Blinkit product route")
        if self.coverage.pages_evaluated < 1:
            raise ValueError("evidence coverage must report at least one captured page")
        return self


class ValidatedOperatorEvidence(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    manifest: OperatorEvidenceManifest
    manifest_path: Path
    payload: bytes
    parsed: RawExtractionResult
    evidence_digest: str


def load_operator_evidence(path: Path, *, parser: BlinkitProductParser | None = None) -> ValidatedOperatorEvidence:
    """Load and validate the sidecar and sanitized HTML before any persistence."""
    manifest_path = path.expanduser().resolve(strict=True)
    payload_json = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = OperatorEvidenceManifest.model_validate(payload_json)

    evidence_root = manifest_path.parent.resolve(strict=True)
    payload_candidate = evidence_root / manifest.payload_file
    if payload_candidate.is_symlink():
        raise ValueError("payload_file must not be a symbolic link")
    payload_path = payload_candidate.resolve(strict=True)
    if payload_path == manifest_path or not payload_path.is_relative_to(evidence_root):
        raise ValueError("payload_file must resolve to a separate file beside the manifest")
    if payload_path.is_symlink() or not payload_path.is_file():
        raise ValueError("payload_file must be a regular local file")
    if payload_path.stat().st_size > MAX_EVIDENCE_BYTES:
        raise ValueError("evidence payload exceeds the 10 MiB limit")
    payload = payload_path.read_bytes()
    if not payload or hashlib.sha256(payload).hexdigest() != manifest.payload_sha256:
        raise ValueError("evidence payload is empty or its SHA-256 digest does not match")
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("HTML evidence must be UTF-8") from exc

    parsed = (parser or BlinkitProductParser()).parse_content(
        payload,
        query=manifest.query,
        source_reference=manifest.source_reference,
    )
    if parsed.platform.casefold() != "blinkit" or parsed.product_count != len(parsed.products):
        raise ValueError("parser output does not match Blinkit evidence contract")
    if not parsed.products:
        raise ValueError("evidence contains no parsed retailer products")
    source = urlsplit(manifest.source_reference)
    if manifest.capture_type == "SEARCH_RESULTS":
        from urllib.parse import parse_qs

        query_values = parse_qs(source.query).get("q", [])
        if query_values != [manifest.query]:
            raise ValueError("search source URL query must match the observed query metadata")
    elif len(parsed.products) != 1:
        raise ValueError("product-detail evidence must identify exactly one product")

    product_ids: set[str] = set()
    for product in parsed.products:
        retailer_id = product.retailer_product_id
        if not retailer_id or not retailer_id.strip():
            raise ValueError("every imported product requires an explicit retailer product ID")
        if retailer_id in product_ids:
            raise ValueError("evidence contains ambiguous duplicate retailer product IDs")
        product_ids.add(retailer_id)
        if not product.product_url:
            raise ValueError("every imported product requires a verified Blinkit product URL")
        if not product.product_name.strip():
            raise ValueError("every imported product requires an observed title")
        if not product.quantity or not product.quantity.strip():
            raise ValueError("every imported product requires observed variant/pack information")
        if not product.raw_text.strip():
            raise ValueError("every imported product requires source-backed raw text")
    if manifest.capture_type == "PRODUCT_DETAIL":
        route_id = source.path.rsplit("/", 1)[-1]
        if parsed.products[0].retailer_product_id != route_id:
            raise ValueError("product-detail route ID does not match parsed retailer product identity")

    digest = hashlib.sha256(
        json.dumps(
            manifest.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\0"
        + payload
    ).hexdigest()
    return ValidatedOperatorEvidence(
        manifest=manifest,
        manifest_path=manifest_path,
        payload=payload,
        parsed=parsed,
        evidence_digest=digest,
    )


class LocalOperatorEvidenceAdapter:
    """Satisfy the existing acquisition protocol without any network access."""

    def __init__(self, evidence: ValidatedOperatorEvidence) -> None:
        self.evidence = evidence

    async def acquire_search(self, *, query: str, evaluation_scope: str) -> AcquisitionResult:
        manifest = self.evidence.manifest
        if manifest.query and query != manifest.query:
            raise ValueError("job query does not match evidence query")
        coverage = manifest.coverage
        return AcquisitionResult(
            payload=self.evidence.payload,
            source_reference=manifest.source_reference,
            content_type=manifest.content_type,
            capture_timestamp=manifest.captured_at,
            evaluation_scope=evaluation_scope,
            pages_evaluated=coverage.pages_evaluated,
            pagination_complete=coverage.pagination_complete,
            termination_reason=coverage.termination_reason,
            capture_type=CaptureType(manifest.capture_type),
            warnings=(),
            capture_coverage=coverage.model_copy(update={"evaluation_scope": evaluation_scope}),
        )


async def import_validated_evidence(evidence: ValidatedOperatorEvidence, *, settings):
    """Run validated bytes through the existing worker/runtime and its registries."""
    from app.data_ingestion import CaptureContext, CaptureType, DownstreamMode, Platform, RequestParameters, ScrapeJob
    from app.workers.bootstrap import build_product_intelligence_runtime

    manifest = evidence.manifest
    parameters = [("evidence_digest", evidence.evidence_digest)]
    if manifest.query is not None:
        parameters.append(("query", manifest.query))
    job = ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType(manifest.capture_type),
        request_parameters=RequestParameters(values=tuple(sorted(parameters))),
        capture_context=CaptureContext(
            country_code="IN",
            currency_code="INR",
            locale="en-IN",
            location_scope=manifest.location_scope,
            session_scope="operator-evidence-import",
        ),
        parser_policy_version="blinkit-parser-v1",
        normalization_policy_version="normalizer-v1",
        downstream_mode=DownstreamMode.PRODUCT_INTELLIGENCE,
        job_contract_version="scrape-job-v1",
    )
    coordinator = build_product_intelligence_runtime(
        settings,
        acquisition_adapter=LocalOperatorEvidenceAdapter(evidence),
    )
    # Operator evidence imports are content-addressed registry operations, not
    # scrape-job retries. The runtime remains the same; only job lifecycle
    # reporting is omitted because an unresolved identity is an expected result.
    coordinator.ingestion_worker._lifecycle_reporter = None
    return await coordinator.product_intelligence_runtime.execute(job)
