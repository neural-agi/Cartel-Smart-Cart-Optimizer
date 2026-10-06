from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from app.product_intelligence.canonical_source.types import (
    CanonicalEvidenceArtifact,
    CanonicalEvidenceCandidate,
    CanonicalEvidenceClaim,
)
from app.product_intelligence.models import EvidenceReference


class CanonicalSourceUnavailable(RuntimeError):
    """Raised when a source cannot be retrieved or validated."""


class CanonicalEvidenceProvider(Protocol):
    async def fetch(self, source_record_id: str) -> CanonicalEvidenceArtifact:
        """Retrieve one source record without mutating the Cartel catalog."""

    def normalize(self, artifact: CanonicalEvidenceArtifact) -> CanonicalEvidenceCandidate:
        """Normalize source evidence without assigning canonical identity."""


class OpenFoodFactsProvider:
    """Open Food Facts adapter; source data remains isolated as evidence."""

    source = "open_food_facts"
    provider_version = "open-food-facts-v1"

    def __init__(self, client: httpx.AsyncClient | None = None, *, base_url: str = "https://world.openfoodfacts.org") -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def fetch(self, source_record_id: str) -> CanonicalEvidenceArtifact:
        record_id = source_record_id.strip()
        if not record_id:
            raise ValueError("source_record_id is required")
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=20.0, headers={"User-Agent": "CartelCanonicalEvidence/1.0"})
        try:
            response = await client.get(f"{self._base_url}/api/v2/product/{record_id}.json")
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CanonicalSourceUnavailable(f"Open Food Facts record retrieval failed for {record_id}") from exc
        finally:
            if owns_client:
                await client.aclose()
        if not isinstance(payload, dict) or payload.get("status") != 1 or not isinstance(payload.get("product"), dict):
            raise CanonicalSourceUnavailable(f"Open Food Facts record is unavailable for {record_id}")
        product = payload["product"]
        revision = str(product.get("last_modified_t") or product.get("rev") or "unknown")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        artifact_id = f"{self.source}:{record_id}:{revision}:{digest[:16]}"
        evidence = (EvidenceReference(source_type=self.source, source_id=record_id, capture_timestamp=datetime.now(timezone.utc)),)
        return CanonicalEvidenceArtifact(
            artifact_id=artifact_id,
            source=self.source,
            source_record_id=record_id,
            source_revision=revision,
            retrieved_at=datetime.now(timezone.utc),
            content_digest=digest,
            provider_version=self.provider_version,
            raw_payload=payload,
            evidence_references=evidence,
        )

    @staticmethod
    def normalize(artifact: CanonicalEvidenceArtifact) -> CanonicalEvidenceCandidate:
        if artifact.source != OpenFoodFactsProvider.source:
            raise ValueError("artifact source does not match Open Food Facts provider")
        product = artifact.raw_payload.get("product")
        if not isinstance(product, dict):
            raise ValueError("source product payload is missing")
        values = {
            "product_name": product.get("product_name") or product.get("product_name_en"),
            "brand": product.get("brands"),
            "quantity": product.get("quantity"),
            "gtin": product.get("code") or artifact.source_record_id,
            "categories": product.get("categories"),
        }
        claims = []
        for name, value in values.items():
            if value is not None and str(value).strip():
                claims.append(CanonicalEvidenceClaim(name=name, value=str(value).strip(), evidence_path=f"product.{name}"))
        required = {"product_name", "brand", "quantity", "gtin"}
        if not required.issubset({claim.name for claim in claims}):
            raise ValueError("source record lacks identity-critical canonical evidence")
        if not re.fullmatch(r"\d+(?:[.,]\d+)?\s*[A-Za-z]+", values["quantity"].strip()):
            raise ValueError("source quantity is not an explicit value and unit")
        if not re.fullmatch(r"\d{8,14}", values["gtin"].strip()):
            raise ValueError("source GTIN is malformed")
        candidate_id = hashlib.sha256(artifact.artifact_id.encode("utf-8")).hexdigest()[:24]
        return CanonicalEvidenceCandidate(
            candidate_id=f"canonical_candidate_{candidate_id}",
            artifact_id=artifact.artifact_id,
            source=artifact.source,
            source_record_id=artifact.source_record_id,
            source_revision=artifact.source_revision,
            claims=tuple(sorted(claims, key=lambda claim: claim.name)),
        )
