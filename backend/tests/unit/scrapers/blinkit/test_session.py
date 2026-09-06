from app.scrapers.blinkit.session import BlinkitBrowserSession


def test_product_readiness_rejects_visible_location_overlay() -> None:
    predicate = BlinkitBrowserSession(
        headers={"user-agent": "test"},
        timeout_seconds=1,
    )._product_results_predicate()

    assert "locationOverlayActive" in predicate
    assert "provide your delivery location" in predicate
    assert "if (locationOverlayActive) return false" in predicate
    assert "element === document.body" in predicate
    assert "style.position === \"fixed\"" in predicate


def test_default_mvp_location_matches_verified_gurugram_scope(monkeypatch) -> None:
    from app.core.config import Settings

    for key in (
        "BLINKIT_DELIVERY_LOCATION_NAME",
        "BLINKIT_DELIVERY_LATITUDE",
        "BLINKIT_DELIVERY_LONGITUDE",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = Settings(_env_file=None)
    assert settings.blinkit_delivery_location_name == "Gurugram"
    assert settings.blinkit_delivery_latitude == 28.413333
    assert settings.blinkit_delivery_longitude == 77.072833
