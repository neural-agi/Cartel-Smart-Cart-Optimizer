import pytest

from app.scrapers.blinkit.scraper import BlinkitScraper
from app.scrapers.base.types import RawHttpResponse


PRODUCT_URL = "https://blinkit.com/prn/country-delight-buffalo-fresh-milk/prid/637879"


def test_product_reference_rejects_host_or_id_mismatch() -> None:
    scraper = BlinkitScraper()

    with pytest.raises(ValueError):
        __import__("asyncio").run(
            scraper.acquire_product(
                "https://example.com/prn/item/prid/637879",
                expected_retailer_product_id="637879",
            )
        )
    with pytest.raises(ValueError):
        __import__("asyncio").run(
            scraper.acquire_product(PRODUCT_URL, expected_retailer_product_id="19512")
        )


@pytest.mark.asyncio
async def test_product_reference_reuses_browser_path_and_expected_id(monkeypatch) -> None:
    scraper = BlinkitScraper()
    calls = {}

    async def fetch(query, *, target_url=None, **kwargs):
        calls.update(query=query, target_url=target_url, kwargs=kwargs)
        return RawHttpResponse(
            url=target_url,
            status_code=200,
            headers={},
            body=b"<html></html>",
            content_type="text/html",
        )

    monkeypatch.setattr(scraper, "_fetch_via_browser", fetch)
    response = await scraper.acquire_product(PRODUCT_URL, expected_retailer_product_id="637879")

    assert response.status_code == 200
    assert calls["query"] == "637879"
    assert calls["target_url"] == PRODUCT_URL
