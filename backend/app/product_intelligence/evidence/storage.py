from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.product_intelligence.evidence.types import (
    EvidenceBundle,
    EvidenceRegistrationRequest,
)
from app.product_intelligence.models import EvidenceReference


logger = get_logger(__name__)

EVIDENCE_ROOT_DIRNAME = "product_intelligence"
EVIDENCE_SUBDIR = "evidence"


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def _safe_segment(value: str) -> str:
    segment = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
    return segment.strip("_") or "unknown"


@dataclass(slots=True)
class EvidenceRecord:
    """Filesystem-backed evidence registration record."""

    evidence_id: str
    request: EvidenceRegistrationRequest
    created_at: datetime
    record_path: Path
    bundle_path: Path

    def to_bundle(self) -> EvidenceBundle:
        return EvidenceBundle(
            platform=self.request.platform,
            source_artifact_reference=self.request.source_artifact_reference,
            capture_timestamp=self.request.capture_timestamp,
            parser_version=self.request.parser_version,
            capture_context_reference=self.request.capture_context_reference,
            evidence_references=[
                EvidenceReference(
                    source_type="evidence_record",
                    source_id=self.evidence_id,
                    capture_timestamp=self.request.capture_timestamp,
                    note="filesystem evidence registry record",
                ),
                EvidenceReference(
                    source_type="source_artifact",
                    source_id=self.request.source_artifact_reference,
                    capture_timestamp=self.request.capture_timestamp,
                    note="original captured source artifact reference",
                ),
            ],
        )


class EvidenceFilesystemStore:
    """Append-only filesystem persistence for evidence registrations."""

    def __init__(self, root_dir: Path | None = None) -> None:
        settings = get_settings()
        self.root_dir = root_dir or (
            settings.data_dir / EVIDENCE_ROOT_DIRNAME / EVIDENCE_SUBDIR
        )
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _request_fingerprint(self, request: EvidenceRegistrationRequest) -> str:
        canonical = _canonical_json(request.model_dump(mode="json"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _record_dir(self, request: EvidenceRegistrationRequest) -> Path:
        platform_dir = self.root_dir / _safe_segment(request.platform)
        return platform_dir / self._request_fingerprint(request)

    def _record_paths(self, request: EvidenceRegistrationRequest) -> tuple[Path, Path]:
        record_dir = self._record_dir(request)
        return record_dir / "record.json", record_dir / "bundle.json"

    def register(self, request: EvidenceRegistrationRequest) -> EvidenceRecord:
        record_path, bundle_path = self._record_paths(request)
        record_dir = record_path.parent
        record_dir.mkdir(parents=True, exist_ok=True)

        evidence_id = record_dir.name

        if not record_path.exists():
            created_at = datetime.now(timezone.utc)
            record_payload = {
                "evidence_id": evidence_id,
                "created_at": created_at.isoformat(),
                "request": request.model_dump(mode="json"),
            }
            record_path.write_text(_canonical_json(record_payload), encoding="utf-8")
            bundle = EvidenceRecord(
                evidence_id=evidence_id,
                request=request,
                created_at=created_at,
                record_path=record_path,
                bundle_path=bundle_path,
            ).to_bundle()
            bundle_payload = bundle.model_dump(mode="json")
            bundle_path.write_text(_canonical_json(bundle_payload), encoding="utf-8")
            logger.info(
                "evidence_record_created platform=%s evidence_id=%s record_path=%s",
                request.platform,
                evidence_id,
                str(record_path),
            )
        else:
            payload = json.loads(record_path.read_text(encoding="utf-8"))
            created_at = datetime.fromisoformat(payload["created_at"])
            if not bundle_path.exists():
                bundle = EvidenceRecord(
                    evidence_id=evidence_id,
                    request=EvidenceRegistrationRequest.model_validate(
                        payload["request"]
                    ),
                    created_at=created_at,
                    record_path=record_path,
                    bundle_path=bundle_path,
                ).to_bundle()
                bundle_path.write_text(
                    _canonical_json(bundle.model_dump(mode="json")),
                    encoding="utf-8",
                )
            logger.info(
                "evidence_record_reused platform=%s evidence_id=%s record_path=%s",
                request.platform,
                evidence_id,
                str(record_path),
            )

        return EvidenceRecord(
            evidence_id=evidence_id,
            request=request,
            created_at=created_at,
            record_path=record_path,
            bundle_path=bundle_path,
        )

    def load(self, request: EvidenceRegistrationRequest) -> EvidenceRecord:
        record_path, bundle_path = self._record_paths(request)
        if not record_path.exists():
            raise FileNotFoundError(
                f"Evidence record does not exist for platform={request.platform!r}"
            )

        payload = json.loads(record_path.read_text(encoding="utf-8"))
        created_at = datetime.fromisoformat(payload["created_at"])
        stored_request = EvidenceRegistrationRequest.model_validate(payload["request"])
        return EvidenceRecord(
            evidence_id=payload["evidence_id"],
            request=stored_request,
            created_at=created_at,
            record_path=record_path,
            bundle_path=bundle_path,
        )

    def load_bundle(self, request: EvidenceRegistrationRequest) -> EvidenceBundle:
        record = self.load(request)
        if record.bundle_path.exists():
            payload = json.loads(record.bundle_path.read_text(encoding="utf-8"))
            return EvidenceBundle.model_validate(payload)
        bundle = record.to_bundle()
        record.bundle_path.write_text(
            _canonical_json(bundle.model_dump(mode="json")),
            encoding="utf-8",
        )
        return bundle
