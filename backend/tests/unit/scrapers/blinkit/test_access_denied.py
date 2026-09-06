import pytest

from app.scrapers.base.exceptions import ScraperAccessDeniedError
from app.scrapers.base.types import RawHttpResponse
from app.scrapers.blinkit.scraper import BlinkitScraper


def test_cloudflare_page_is_classified_as_access_denied():
    response = RawHttpResponse(
        url="https://blinkit.com/s/?q=milk", status_code=200, headers={},
        body=b"access denied - you have been blocked - Cloudflare Ray ID abc",
    )
    with pytest.raises(ScraperAccessDeniedError) as error:
        if BlinkitScraper._is_access_denied(response):
            raise ScraperAccessDeniedError("blocked", status_code=response.status_code)
    assert error.value.reason_code == "retailer_access_denied"


def test_access_denied_status_is_classified_without_claiming_product_data():
    response = RawHttpResponse(
        url="https://blinkit.com/s/?q=milk", status_code=403, headers={}, body=b"",
    )
    assert BlinkitScraper._is_access_denied(response)
