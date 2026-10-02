"""Gửi email qua SMTP với retry + exponential backoff (dev dùng Mailpit)."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid

from app.core.config import get_settings
from app.core.logging import get_logger
from worker.celery_app import celery_app

logger = get_logger(__name__)


def build_message(to: str, subject: str, text: str, html: str, sender: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain="lys.local")
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


@celery_app.task(
    name="worker.tasks.email.send_email",
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=6,
)
def send_email(to: str, subject: str, text: str, html: str) -> str:
    settings = get_settings()
    message = build_message(to, subject, text, html, settings.smtp_from)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        smtp.send_message(message)
    logger.info("email_sent", to_domain=to.split("@")[-1], subject=subject)
    return str(message["Message-ID"])
