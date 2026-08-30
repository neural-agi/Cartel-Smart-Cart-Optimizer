"""Bridge Blinkit extraction output into immutable ingestion contracts."""

from __future__ import annotations

from app.data_ingestion import (
    CompletenessState,
    ObservationCompleteness,
    ObservationFieldReference,
    ParsedRetailObservation,
    ParsedRetailObservationBatch,
    Platform,
    RawArtifactReference,
)
from app.product_intelligence.models import EvidenceReference
from app.schemas.extraction import RawExtractionResult, RawExtractedProduct


class BlinkitParserBridge:
    parser_version = "blinkit-parser-v1"

    def build_batch(self, result: RawExtractionResult, artifact_reference: RawArtifactReference) -> ParsedRetailObservationBatch:
        self._validate_input(result, artifact_reference)
        coverage = result.capture_coverage
        assert coverage is not None
        observations = tuple(self._observation(product, artifact_reference) for product in result.products)
        return ParsedRetailObservationBatch(
            raw_artifact_reference=artifact_reference,
            parser_version=result.parser_version,
            observations=observations,
            warnings=tuple(result.warnings),
            completeness=self._completeness(result, coverage, bool(observations)),
        )

    def _validate_input(self, result: RawExtractionResult, artifact: RawArtifactReference) -> None:
        if result.platform.lower() != "blinkit" or artifact.platform is not Platform.BLINKIT:
            raise ValueError("Blinkit bridge requires Blinkit input")
        if result.evaluation_scope is None or result.capture_coverage is None:
            raise ValueError("completeness metadata is required")
        if result.evaluation_scope != result.capture_coverage.evaluation_scope:
            raise ValueError("evaluation scope metadata must agree")
        if result.product_count != len(result.products):
            raise ValueError("product count must match extracted products")
        ids = [product.source_index for product in result.products]
        if len(ids) != len(set(ids)):
            raise ValueError("source record identifiers must be unique")

    def _observation(self, product: RawExtractedProduct, artifact: RawArtifactReference) -> ParsedRetailObservation:
        source_id = str(product.source_index)
        evidence = EvidenceReference(source_type="raw_artifact", source_id=artifact.artifact_id)
        fields = tuple(
            ObservationFieldReference(evidence_reference=evidence, locator=f"products[{source_id}].{name}")
            for name in ("product_name", "quantity", "raw_category", "displayed_price", "mrp", "offer_text", "stock_availability", "raw_text")
        )
        identifiers = [("source_index", source_id)]
        if product.retailer_product_id:
            identifiers.append(("retailer_product_id", product.retailer_product_id))
        return ParsedRetailObservation(
            source_record_id=source_id,
            platform=Platform.BLINKIT,
            raw_title=product.product_name,
            raw_quantity=product.quantity,
            platform_identifiers=tuple(sorted(identifiers)),
            raw_price_text=product.displayed_price,
            raw_mrp_text=product.mrp,
            offer_text=product.offer_text,
            availability_signal=product.stock_availability,
            field_references=fields,
        )

    def _completeness(self, result: RawExtractionResult, coverage, has_observations: bool) -> ObservationCompleteness:
        if not has_observations:
            if coverage.pagination_complete is not True:
                raise ValueError("empty extraction lacks explicit completion evidence")
            return ObservationCompleteness(state=CompletenessState.EMPTY, scope_reference=result.evaluation_scope, basis=coverage.termination_reason)
        if coverage.pagination_complete is False:
            return ObservationCompleteness(state=CompletenessState.PARTIAL, scope_reference=result.evaluation_scope, basis=coverage.termination_reason, missing_scope=("remaining-pagination",))
        if coverage.pagination_complete is None:
            return ObservationCompleteness(state=CompletenessState.UNKNOWN, scope_reference=result.evaluation_scope, basis=coverage.termination_reason)
        return ObservationCompleteness(state=CompletenessState.COMPLETE, scope_reference=result.evaluation_scope, basis=coverage.termination_reason)
