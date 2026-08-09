from __future__ import annotations

from app.data_ingestion.enums import CompletenessState
from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.evidence.types import EvidenceBundle
from app.product_intelligence.ingestion.types import ProductIntelligenceIngestionHandoff
from app.product_intelligence.models import ListingObservation, PlatformListing
from app.product_intelligence.orchestrator.service import ProductIntelligencePipelineRequest


class ProductIntelligenceIngestionAdapter:
    """Pure mapping boundary from normalized ingestion to Product Intelligence."""

    def build_handoff(self, observation: NormalizedObservation) -> ProductIntelligenceIngestionHandoff:
        self._validate(observation)
        completeness = observation.completeness
        if completeness.state is CompletenessState.EMPTY:
            return ProductIntelligenceIngestionHandoff(
                observation_id=observation.observation_id,
                raw_artifact_reference=observation.raw_artifact_reference,
                evidence_references=observation.evidence_references,
                field_references=observation.field_references,
                completeness=completeness,
                normalization_version=observation.normalization_version,
                parser_version=observation.parser_version,
            )

        listing = PlatformListing(
            platform=observation.platform.value,
            platform_listing_id=observation.source_record_id,
            raw_title=observation.normalized_name,
            raw_quantity_text=observation.normalized_quantity,
            raw_category_text=observation.normalized_category,
        )
        listing_observation = ListingObservation(
            platform_listing_id=observation.source_record_id,
            displayed_price=observation.observed_price_text,
            reference_price=observation.observed_mrp_text,
            offer_text=observation.observed_offer_text,
            availability_signal=observation.availability_signal,
            capture_timestamp=observation.raw_artifact_reference.capture_timestamp,
            parser_version=observation.parser_version,
            source_artifact_reference=observation.raw_artifact_reference.artifact_id,
        )
        evidence_bundle = EvidenceBundle(
            platform=observation.platform.value,
            source_artifact_reference=observation.raw_artifact_reference.artifact_id,
            capture_timestamp=observation.raw_artifact_reference.capture_timestamp,
            evidence_references=list(observation.evidence_references),
            parser_version=observation.parser_version,
        )
        request = ProductIntelligencePipelineRequest(
            platform_listing=listing,
            listing_observation=listing_observation,
            evidence_bundles=[evidence_bundle],
        )
        return ProductIntelligenceIngestionHandoff(
            observation_id=observation.observation_id,
            raw_artifact_reference=observation.raw_artifact_reference,
            evidence_references=observation.evidence_references,
            field_references=observation.field_references,
            completeness=completeness,
            normalization_version=observation.normalization_version,
            parser_version=observation.parser_version,
            platform_listing=listing,
            listing_observation=listing_observation,
            evidence_bundle=evidence_bundle,
            pipeline_request=request,
        )

    @staticmethod
    def _validate(observation: NormalizedObservation) -> None:
        if observation.normalized_name is None and observation.completeness.state is not CompletenessState.EMPTY:
            raise ValueError("normalized_name is required for a Product Intelligence listing")
