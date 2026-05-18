"""SMTP email notifier."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from config import (
    EMAIL_HOST,
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_TO,
    EMAIL_USE_TLS,
    EMAIL_USER,
)


def _email_configured() -> bool:
    required = [EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD, EMAIL_TO]
    return all(required)


def send_email(title: str, body: str) -> bool:
    """Send a plain-text email. Returns True only after SMTP success."""

    if not _email_configured():
        print("[Email] Missing SMTP configuration. Skip email sending.")
        return False

    message = EmailMessage()
    message["Subject"] = f"【每日优秀论文推荐】{title}"
    message["From"] = EMAIL_USER
    message["To"] = EMAIL_TO
    message.set_content(body)

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=30) as smtp:
            if EMAIL_USE_TLS:
                smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp.send_message(message)
        print("[Email] Email sent successfully.")
        return True
    except Exception as exc:  # smtplib raises several exception families.
        print(f"[Email] Failed to send email: {exc}")
        return False
