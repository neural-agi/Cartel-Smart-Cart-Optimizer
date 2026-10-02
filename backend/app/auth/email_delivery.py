"""Email delivery boundary for verification and password recovery."""

from email.message import EmailMessage
from smtplib import SMTP, SMTPException, SMTP_SSL
from typing import Protocol

from app.core.config import Settings


class EmailDelivery(Protocol):
    def send(self, recipient: str, subject: str, body: str) -> None: ...


class EmailDeliveryUnavailable(RuntimeError):
    pass


class SmtpEmailDelivery:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, recipient: str, subject: str, body: str) -> None:
        if not self.settings.email_delivery_configured:
            raise EmailDeliveryUnavailable("email delivery is not configured")
        message = EmailMessage()
        message["From"] = self.settings.smtp_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        try:
            if self.settings.smtp_port == 465:
                with SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as client:
                    if self.settings.smtp_username:
                        client.login(self.settings.smtp_username, self.settings.smtp_password.get_secret_value())
                    client.send_message(message)
            else:
                if not self.settings.smtp_starttls:
                    raise EmailDeliveryUnavailable("email delivery requires encrypted transport")
                with SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as client:
                    client.starttls()
                    if self.settings.smtp_username:
                        client.login(self.settings.smtp_username, self.settings.smtp_password.get_secret_value())
                    client.send_message(message)
        except (OSError, SMTPException) as exc:
            raise EmailDeliveryUnavailable("email delivery failed") from exc
