from datetime import datetime, timezone

import pytest

from app.data_ingestion import CaptureContext, CaptureType, DownstreamMode, Platform, RawArtifactReference, RequestParameters, ScrapeJob
from app.data_ingestion.types import CaptureCoverage
from app.schemas.extraction import RawExtractedProduct, RawExtractionResult
from app.scrapers.blinkit.bridge import BlinkitParserBridge


def _artifact() -> RawArtifactReference:
    job = ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "milk"),)),
        capture_context=CaptureContext(country_code="IN", currency_code="INR", locale="en-IN", location_scope="blr", session_scope="s"),
        parser_policy_version="p1", normalization_policy_version="n1", downstream_mode=DownstreamMode.NONE, job_contract_version="j1",
    )
    return RawArtifactReference(
        artifact_id="artifact-1", job_id=job.job_id, attempt_id=f"{job.job_id}:1", platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS, content_digest="digest", storage_reference="opaque", content_type="text/html",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), source_reference="source",
    )


def _result(products: list[RawExtractedProduct], *, complete: bool | None = True, metadata: bool = True) -> RawExtractionResult:
    values = {"platform": "blinkit", "query": "milk", "source_path": "capture.html", "extracted_at": datetime(2026, 1, 1, tzinfo=timezone.utc), "product_count": len(products), "products": products}
    if metadata:
        values.update(evaluation_scope="search:milk:blr", capture_coverage=CaptureCoverage(evaluation_scope="search:milk:blr", pages_evaluated=1, pagination_complete=complete, termination_reason="no_next_page"))
    return RawExtractionResult(**values)


def test_bridge_maps_raw_blinkit_fields_and_preserves_artifact() -> None:
    product = RawExtractedProduct(source_index=1, retailer_product_id="637879", product_name="Milk", displayed_price="₹100", mrp="₹120", quantity="500 ml", stock_availability="in_stock", offer_text="₹20 OFF", raw_text="Milk 500 ml ₹100")
    batch = BlinkitParserBridge().build_batch(_result([product]), _artifact())
    observation = batch.observations[0]
    assert batch.raw_artifact_reference == _artifact()
    assert observation.raw_title == "Milk"
    assert observation.raw_quantity == "500 ml"
    assert observation.raw_price_text == "₹100"
    assert observation.raw_mrp_text == "₹120"
    assert observation.availability_signal == "in_stock"
    assert observation.offer_text == "₹20 OFF"
    assert observation.platform_identifiers == (("retailer_product_id", "637879"), ("source_index", "1"))
    assert batch.completeness.state.value == "COMPLETE"
    assert batch.parser_version == "blinkit-parser-v1"


def test_batch_identity_uses_artifact_and_parser_version_only() -> None:
    artifact = _artifact()
    result = _result([RawExtractedProduct(source_index=1, product_name="Milk", raw_text="Milk")])
    bridge = BlinkitParserBridge()
    first = bridge.build_batch(result, artifact)
    second = bridge.build_batch(result, artifact)
    assert first.batch_id == second.batch_id
    assert first.batch_id == bridge.build_batch(result, artifact).batch_id


def test_duplicate_source_index_fails() -> None:
    products = [RawExtractedProduct(source_index=1, product_name="A", raw_text="A"), RawExtractedProduct(source_index=1, product_name="B", raw_text="B")]
    with pytest.raises(ValueError, match="source record"):
        BlinkitParserBridge().build_batch(_result(products), _artifact())


def test_empty_without_completeness_metadata_fails_closed() -> None:
    with pytest.raises(ValueError, match="completeness"):
        BlinkitParserBridge().build_batch(_result([], metadata=False), _artifact())


def test_empty_complete_is_explicit() -> None:
    batch = BlinkitParserBridge().build_batch(_result([]), _artifact())
    assert batch.completeness.state.value == "EMPTY"


def test_partial_and_unknown_are_preserved() -> None:
    product = RawExtractedProduct(source_index=1, product_name="A", raw_text="A")
    assert BlinkitParserBridge().build_batch(_result([product], complete=False), _artifact()).completeness.state.value == "PARTIAL"
    assert BlinkitParserBridge().build_batch(_result([product], complete=None), _artifact()).completeness.state.value == "UNKNOWN"
