"""Deterministic normalization of parsed retail observations."""

from __future__ import annotations

from app.data_ingestion import NormalizedObservation, ParsedRetailObservation, ParsedRetailObservationBatch
from app.product_intelligence.models import EvidenceReference
from app.normalization.pricing.parser import GovernedRetailPriceParser


class DeterministicIngestionNormalizer:
    """Convert parsed observations without interpreting business meaning."""

    normalization_version = "normalizer-v1"

    def __init__(self, *, price_parser: GovernedRetailPriceParser | None = None) -> None:
        self.price_parser = price_parser or GovernedRetailPriceParser()

    def normalize(self, batch: ParsedRetailObservationBatch, *, currency_code: str | None = None) -> tuple[NormalizedObservation, ...]:
        return tuple(self._normalize_observation(batch, observation, currency_code=currency_code) for observation in batch.observations)

    def _normalize_observation(
        self,
        batch: ParsedRetailObservationBatch,
        observation: ParsedRetailObservation,
        *,
        currency_code: str | None,
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
            observed_selling_price=self.price_parser.parse(
                self._text(observation.raw_price_text), currency_code=currency_code
            ),
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
