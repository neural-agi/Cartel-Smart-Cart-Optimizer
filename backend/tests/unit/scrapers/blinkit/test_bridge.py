"""Phase J.1.1: the Blinkit parser bridge is denied before validation.

The bridge used to translate extracted Blinkit products into ingestion
contracts. That path is now policy-blocked, so these tests assert denial
happens before any Blinkit input is inspected or transformed. Generic bridge
behaviour is covered by the ZEPTO fixture bridge in
``tests/support/fixture_pipeline.py``.
"""

from datetime import datetime, timezone

import pytest

from app.data_ingestion import (
    CaptureContext,
    CaptureType,
    DownstreamMode,
    Platform,
    RawArtifactReference,
    RequestParameters,
    ScrapeJob,
)
from app.data_ingestion.types import CaptureCoverage
from app.retailer_policy import RetailerPolicyBlocked
from app.schemas.extraction import RawExtractedProduct, RawExtractionResult
from app.scrapers.blinkit.bridge import BlinkitParserBridge


def _artifact() -> RawArtifactReference:
    job = ScrapeJob(
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        request_parameters=RequestParameters(values=(("query", "milk"),)),
        capture_context=CaptureContext(
            country_code="IN",
            currency_code="INR",
            locale="en-IN",
            location_scope="blr",
            session_scope="s",
        ),
        parser_policy_version="p1",
        normalization_policy_version="n1",
        downstream_mode=DownstreamMode.NONE,
        job_contract_version="j1",
    )
    return RawArtifactReference(
        artifact_id="artifact-1",
        job_id=job.job_id,
        attempt_id=f"{job.job_id}:1",
        platform=Platform.BLINKIT,
        capture_type=CaptureType.SEARCH_RESULTS,
        content_digest="digest",
        storage_reference="opaque",
        content_type="text/html",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_reference="source",
    )


def _result(
    products: list[RawExtractedProduct],
    *,
    complete: bool | None = True,
    metadata: bool = True,
) -> RawExtractionResult:
    values = {
        "platform": "blinkit",
        "query": "milk",
        "source_path": "capture.html",
        "extracted_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "product_count": len(products),
        "products": products,
    }
    if metadata:
        values.update(
            evaluation_scope="search:milk:blr",
            capture_coverage=CaptureCoverage(
                evaluation_scope="search:milk:blr",
                pages_evaluated=1,
                pagination_complete=complete,
                termination_reason="no_next_page",
            ),
        )
    return RawExtractionResult(**values)


def _product() -> RawExtractedProduct:
    return RawExtractedProduct(
        source_index=1,
        platform="blinkit",
        retailer_product_id="637879",
        product_url="https://blinkit.com/prn/milk/prid/637879",
        product_name="Milk",
        displayed_price="₹100",
        quantity="500 ml",
        raw_text="Milk 500 ml ₹100",
    )


@pytest.mark.parametrize(
    "result",
    [
        _result([_product()]),
        _result([_product()], complete=False),
        _result([_product()], complete=None),
        _result([]),
        _result([], metadata=False),
    ],
)
def test_bridge_denies_blinkit_input_before_validation(result) -> None:
    with pytest.raises(RetailerPolicyBlocked) as error:
        BlinkitParserBridge().build_batch(result, _artifact())

    assert error.value.reason_code == "blinkit_commercial_authorization_required"
