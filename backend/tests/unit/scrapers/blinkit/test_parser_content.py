from pathlib import Path

from app.scrapers.blinkit.parser import BlinkitProductParser


HTML = """
<div role="button">Milk 500 ml ₹100 ADD</div>
"""


def test_parse_content_preserves_remote_source_without_path() -> None:
    result = BlinkitProductParser().parse_content(
        HTML.encode("utf-8"),
        query="milk",
        source_reference="https://blinkit.com/s/?q=milk",
    )
    assert result.source_path is None
    assert result.source_reference == "https://blinkit.com/s/?q=milk"
    assert result.product_count == len(result.products)


def test_parse_html_remains_compatible_with_file_metadata() -> None:
    result = BlinkitProductParser().parse_html(
        HTML,
        source_path=Path("capture.html"),
        query="milk",
    )
    assert result.source_path == Path("capture.html")
    assert result.source_reference is None
