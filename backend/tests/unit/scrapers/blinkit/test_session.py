from app.scrapers.blinkit.session import BlinkitBrowserSession


def test_product_readiness_rejects_visible_location_overlay() -> None:
    predicate = BlinkitBrowserSession(
        headers={"user-agent": "test"},
        timeout_seconds=1,
    )._product_results_predicate()

    assert "locationOverlayActive" in predicate
    assert "provide your delivery location" in predicate
    assert "if (locationOverlayActive) return false" in predicate
