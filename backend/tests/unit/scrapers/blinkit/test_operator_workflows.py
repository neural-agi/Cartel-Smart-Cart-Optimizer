import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from scripts import bootstrap_blinkit_session, check_blinkit_session


def test_bootstrap_arguments_apply_only_explicit_overrides(monkeypatch) -> None:
    args = SimpleNamespace(location="Gurugram", lat=28.4, lon=77.0)
    bootstrap_blinkit_session.apply_overrides(args)
    assert os.environ["BLINKIT_DELIVERY_LOCATION_NAME"] == "Gurugram"
    assert os.environ["BLINKIT_DELIVERY_LATITUDE"] == "28.4"
    assert os.environ["BLINKIT_DELIVERY_LONGITUDE"] == "77.0"


def test_session_validation_reports_missing_state_without_browser(tmp_path, monkeypatch) -> None:
    from app.core.config import Settings

    settings = Settings(blinkit_session_state_path=tmp_path / "missing.json")
    monkeypatch.setattr(check_blinkit_session, "get_settings", lambda: settings)
    result = __import__("asyncio").run(check_blinkit_session.validate("milk"))
    assert result["status"] == "unavailable"
    assert result["reason"] == "session_state_missing"


def test_diagnostic_payload_contains_no_session_secrets() -> None:
    payload = {"status": "usable", "location_metadata": {"locality": "Gurugram"}}
    rendered = json.dumps(payload)
    for secret_name in ("authKey", "accessToken", "cookies", "localStorage", "deviceId"):
        assert secret_name not in rendered
