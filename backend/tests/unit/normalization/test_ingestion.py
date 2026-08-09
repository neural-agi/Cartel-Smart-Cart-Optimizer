from datetime import datetime, timezone

from app.data_ingestion import CaptureType, CompletenessState, ObservationCompleteness, ObservationFieldReference, ParsedRetailObservation, ParsedRetailObservationBatch, Platform, RawArtifactReference
from app.normalization import DeterministicIngestionNormalizer
from app.product_intelligence.models import EvidenceReference


def _batch() -> ParsedRetailObservationBatch:
    artifact = RawArtifactReference(artifact_id="artifact-1", job_id="job-1", attempt_id="attempt-1", platform=Platform.BLINKIT, capture_type=CaptureType.SEARCH_RESULTS, content_digest="digest", storage_reference="opaque", content_type="text/html", capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), source_reference="https://example.test")
    evidence = EvidenceReference(source_type="raw_artifact", source_id="artifact-1")
    field = ObservationFieldReference(evidence_reference=evidence, locator="products[1].product_name")
    observation = ParsedRetailObservation(source_record_id="1", platform=Platform.BLINKIT, raw_title="  Milk  500 ml ", raw_quantity=" 500   ml ", raw_price_text=" ₹100 ", raw_mrp_text=" ₹120 ", offer_text=" ₹20  OFF ", availability_signal=" in_stock ", platform_identifiers=(("source_index", "1"),), field_references=(field,))
    completeness = ObservationCompleteness(state=CompletenessState.COMPLETE, scope_reference="scope", basis="no_next_page")
    return ParsedRetailObservationBatch(raw_artifact_reference=artifact, parser_version="blinkit-parser-v1", observations=(observation,), completeness=completeness)


def test_normalizer_maps_fields_and_preserves_provenance() -> None:
    result = DeterministicIngestionNormalizer().normalize(_batch())
    observation = result[0]
    assert observation.normalized_name == "Milk 500 ml"
    assert observation.normalized_quantity == "500 ml"
    assert observation.observed_price_text == "₹100"
    assert observation.observed_mrp_text == "₹120"
    assert observation.observed_offer_text == "₹20 OFF"
    assert observation.availability_signal == "in_stock"
    assert observation.platform_identifiers == (("source_index", "1"),)
    assert observation.evidence_references[0].source_id == "artifact-1"
    assert observation.field_references[0].locator == "products[1].product_name"
    assert observation.completeness.state is CompletenessState.COMPLETE
    assert observation.normalization_version == "normalizer-v1"
    assert observation.parser_version == "blinkit-parser-v1"


def test_normalizer_is_deterministic_and_does_not_convert_quantity_or_price() -> None:
    first = DeterministicIngestionNormalizer().normalize(_batch())
    second = DeterministicIngestionNormalizer().normalize(_batch())
    assert first == second
    assert first[0].normalized_quantity == "500 ml"
    assert first[0].observed_price_text == "₹100"


def test_empty_batch_produces_no_fabricated_observations() -> None:
    batch = _batch().model_copy(update={"observations": (), "completeness": ObservationCompleteness(state=CompletenessState.EMPTY, scope_reference="scope", basis="no_next_page")})
    assert DeterministicIngestionNormalizer().normalize(batch) == ()
