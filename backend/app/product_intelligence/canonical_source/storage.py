from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.config import get_settings
from app.product_intelligence.canonical_source.types import (
    CanonicalEvidenceArtifact,
    CanonicalEvidenceReview,
)


class CanonicalEvidenceFilesystemStore:
    """Append-only source-isolated artifact and review persistence."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or get_settings().data_dir / "product_intelligence" / "canonical_source"
        self.artifact_dir = self.root_dir / "artifacts"
        self.review_dir = self.root_dir / "reviews"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.review_dir.mkdir(parents=True, exist_ok=True)

    def put_artifact(self, artifact: CanonicalEvidenceArtifact) -> CanonicalEvidenceArtifact:
        path = self.artifact_dir / f"{artifact.artifact_id.replace(':', '_')}.json"
        payload = json.dumps(artifact.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if path.exists():
            existing = CanonicalEvidenceArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if existing.content_digest != artifact.content_digest or existing.raw_payload != artifact.raw_payload:
                raise ValueError("canonical evidence artifact identity conflict")
            return existing
        if not path.exists():
            temp = path.with_suffix(".json.tmp")
            temp.write_text(payload, encoding="utf-8")
            os.replace(temp, path)
        return artifact

    def put_review(self, review: CanonicalEvidenceReview) -> CanonicalEvidenceReview:
        path = self.review_dir / f"{review.candidate.candidate_id}.json"
        payload = json.dumps(review.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if path.exists():
            existing = CanonicalEvidenceReview.model_validate(json.loads(path.read_text(encoding="utf-8")))
            if existing.candidate.model_copy(update={"status": None}) != review.candidate.model_copy(update={"status": None}):
                raise ValueError("canonical evidence review identity conflict")
        temp = path.with_suffix(".json.tmp")
        temp.write_text(payload, encoding="utf-8")
        os.replace(temp, path)
        return review

    def get_review(self, candidate_id: str) -> CanonicalEvidenceReview | None:
        path = self.review_dir / f"{candidate_id}.json"
        if not path.exists():
            return None
        return CanonicalEvidenceReview.model_validate(json.loads(path.read_text(encoding="utf-8")))
