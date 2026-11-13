from email import policy
from email.parser import BytesParser

import pytest

from app.auth.email_delivery import EmailDeliveryUnavailable, FileEmailDelivery
from app.core.config import Settings


def test_file_email_delivery_captures_message_without_smtp(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="development",
        email_delivery_mode="file",
        local_email_dir=tmp_path,
    )

    FileEmailDelivery(settings).send(
        "test@example.com",
        "Verify your Cartel account",
        "Open http://localhost:3000/verify-email#token=test-token",
    )

    messages = list(tmp_path.glob("*.eml"))
    assert len(messages) == 1
    parsed = BytesParser(policy=policy.default).parsebytes(messages[0].read_bytes())
    assert parsed["To"] == "test@example.com"
    assert "test-token" in parsed.get_content()


def test_file_email_delivery_is_rejected_in_production(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        docs_enabled=False,
        public_origin="https://cartel.example",
        auth_required=True,
        auth_tokens="operator=local-test-token",
        email_delivery_mode="file",
        local_email_dir=tmp_path,
    )

    with pytest.raises(EmailDeliveryUnavailable):
        FileEmailDelivery(settings)
