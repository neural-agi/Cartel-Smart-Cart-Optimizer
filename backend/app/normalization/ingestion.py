"""Deterministic normalization of parsed retail observations."""

from __future__ import annotations

from app.data_ingestion import NormalizedObservation, ParsedRetailObservation, ParsedRetailObservationBatch
from app.product_intelligence.models import EvidenceReference


class DeterministicIngestionNormalizer:
    """Convert parsed observations without interpreting business meaning."""

    normalization_version = "normalizer-v1"

    def normalize(self, batch: ParsedRetailObservationBatch) -> tuple[NormalizedObservation, ...]:
        return tuple(self._normalize_observation(batch, observation) for observation in batch.observations)

    def _normalize_observation(
        self,
        batch: ParsedRetailObservationBatch,
        observation: ParsedRetailObservation,
    ) -> NormalizedObservation:
        return NormalizedObservation(
            platform=observation.platform,
            source_record_id=observation.source_record_id,
            raw_artifact_reference=batch.raw_artifact_reference,
            normalized_name=self._text(observation.raw_title),
            normalized_quantity=self._text(observation.raw_quantity),
            normalized_category=self._text(observation.raw_category),
            platform_identifiers=observation.platform_identifiers,
            observed_price_text=self._text(observation.raw_price_text),
            observed_mrp_text=self._text(observation.raw_mrp_text),
            observed_offer_text=self._text(observation.offer_text),
            availability_signal=self._text(observation.availability_signal),
            evidence_references=self._evidence(observation),
            field_references=observation.field_references,
            completeness=batch.completeness,
            parser_version=batch.parser_version,
            normalization_version=self.normalization_version,
        )

    @staticmethod
    def _text(value: str | None) -> str | None:
        return None if value is None else " ".join(value.split())

    @staticmethod
    def _evidence(observation: ParsedRetailObservation) -> tuple[EvidenceReference, ...]:
        references: list[EvidenceReference] = []
        seen: set[tuple[str, str]] = set()
        for field_reference in observation.field_references:
            reference = field_reference.evidence_reference
            key = (reference.source_type, reference.source_id)
            if key not in seen:
                seen.add(key)
                references.append(reference)
        return tuple(references)
