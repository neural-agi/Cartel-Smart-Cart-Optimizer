"""Deterministic identity builders for immutable ingestion contracts."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.data_ingestion.types import NormalizedObservation, ParsedRetailObservationBatch, ReplayReference, ScrapeJob


def _digest(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class ScrapeJobIdentityBuilder:
    """Build the canonical identity of a scrape job."""

    def build(self, job: "ScrapeJob") -> dict[str, Any]:
        return {
            "platform": job.platform.value,
            "capture_type": job.capture_type.value,
            "request_parameters": tuple(job.request_parameters.values),
            "capture_context": {
                "country_code": job.capture_context.country_code,
                "currency_code": job.capture_context.currency_code,
                "locale": job.capture_context.locale,
                "location_scope": job.capture_context.location_scope,
                "session_scope": job.capture_context.session_scope,
                "additional_parameters": tuple(
                    job.capture_context.additional_parameters
                ),
            },
            "parser_policy_version": job.parser_policy_version,
            "normalization_policy_version": job.normalization_policy_version,
            "downstream_mode": job.downstream_mode.value,
            "job_contract_version": job.job_contract_version,
        }

    def job_id(self, job: "ScrapeJob") -> str:
        return _digest(self.build(job))


class ScrapeAttemptIdentityBuilder:
    """Build the deterministic identity of an attempt within a job."""

    def attempt_id(self, job_id: str, attempt_number: int) -> str:
        return f"{job_id}:{attempt_number}"


class ReplayReferenceIdentityBuilder:
    """Build the canonical identity of a replay reference."""

    def build(self, reference: "ReplayReference") -> dict[str, Any]:
        return {
            "original_job_id": reference.original_job_id,
            "artifact_id": (
                reference.artifact_reference.artifact_id
                if reference.artifact_reference is not None
                else None
            ),
            "replay_target": reference.replay_target,
            "parser_policy_version": reference.parser_policy_version,
            "normalization_policy_version": reference.normalization_policy_version,
            "downstream_mode": (
                reference.downstream_mode.value
                if reference.downstream_mode is not None
                else None
            ),
        }

    def replay_id(self, reference: "ReplayReference") -> str:
        return _digest(self.build(reference))


class ParsedObservationBatchIdentityBuilder:
    def batch_id(self, batch: "ParsedRetailObservationBatch") -> str:
        return _digest({
            "artifact_id": batch.raw_artifact_reference.artifact_id,
            "parser_version": batch.parser_version,
        })


class ArtifactIdentityBuilder:
    def artifact_id(self, *, job_id: str, attempt_id: str, capture_type: str, content_digest: str) -> str:
        return _digest({"job_id": job_id, "attempt_id": attempt_id, "capture_type": capture_type, "content_digest": content_digest})


class NormalizedObservationIdentityBuilder:
    def build(self, observation: "NormalizedObservation") -> dict[str, Any]:
        return {
            "platform": observation.platform.value,
            "source_record_id": observation.source_record_id,
            "artifact_id": observation.raw_artifact_reference.artifact_id,
            "normalized_name": observation.normalized_name,
            "normalized_quantity": observation.normalized_quantity,
            "normalized_category": observation.normalized_category,
            "platform_identifiers": tuple(observation.platform_identifiers),
            "observed_price_text": observation.observed_price_text,
            "observed_mrp_text": observation.observed_mrp_text,
            "observed_offer_text": observation.observed_offer_text,
            "availability_signal": observation.availability_signal,
            "completeness": observation.completeness.model_dump(mode="json"),
            "normalization_version": observation.normalization_version,
        }

    def observation_id(self, observation: "NormalizedObservation") -> str:
        return _digest(self.build(observation))
