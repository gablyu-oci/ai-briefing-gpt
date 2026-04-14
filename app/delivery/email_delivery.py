"""
email_delivery.py — Send briefing emails via Gmail-compatible SMTP.

Reads SMTP credentials from environment variables and falls back to a
stubbed send when credentials are not configured.
"""

import html
import logging
import os
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid

logger = logging.getLogger(__name__)


def _first_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _first_secret(*names: str, file_env_names: tuple[str, ...] = ()) -> str:
    value = _first_env(*names)
    if value:
        return value

    for name in file_env_names:
        path = os.environ.get(name, "").strip()
        if not path:
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            logger.warning("Could not read SMTP secret file from %s", name)
    return ""


def _resolve_smtp_settings() -> dict:
    username = _first_env(
        "EMAIL_SMTP_USER",
        "SMTP_USERNAME",
        "GMAIL_USER",
        "GMAIL_EMAIL",
    )
    password = _first_secret(
        "EMAIL_SMTP_PASSWORD",
        "SMTP_PASSWORD",
        "GMAIL_APP_PASSWORD",
        "GMAIL_PASSWORD",
        "GMAIL_SECRET",
        file_env_names=(
            "EMAIL_SMTP_PASSWORD_FILE",
            "SMTP_PASSWORD_FILE",
            "GMAIL_APP_PASSWORD_FILE",
            "GMAIL_SECRET_FILE",
        ),
    )
    sender = (
        _first_env(
            "EMAIL_FROM_EMAIL",
            "GMAIL_FROM_EMAIL",
            "GMAIL_EMAIL",
            "GMAIL_USER",
        )
        or username
        or "briefing@example.com"
    )

    port_text = _first_env("EMAIL_SMTP_PORT", "SMTP_PORT") or "465"
    try:
        port = int(port_text)
    except ValueError:
        logger.warning("Invalid SMTP port '%s'; falling back to 465", port_text)
        port = 465

    return {
        "host": _first_env("EMAIL_SMTP_HOST", "SMTP_HOST") or "smtp.gmail.com",
        "port": port,
        "username": username,
        "password": password,
        "sender": sender,
    }


def _html_to_text(html_content: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html_content)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "AI briefing attached as HTML content."


def _resolve_audience_email(audience_id: str, default_email: str) -> str:
    return (
        _first_env(
            f"BRIEFING_EMAIL_{audience_id.upper()}",
            f"AUDIENCE_EMAIL_{audience_id.upper()}",
        )
        or default_email
    )


def _open_smtp_connection(host: str, port: int):
    if port == 465:
        return smtplib.SMTP_SSL(host, port, timeout=30)

    server = smtplib.SMTP(host, port, timeout=30)
    server.ehlo()
    server.starttls()
    server.ehlo()
    return server


def send_briefing_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: str | None = None,
) -> dict:
    """Send a single briefing email via Gmail-compatible SMTP."""
    smtp_settings = _resolve_smtp_settings()
    sender = from_email or smtp_settings["sender"]
    username = smtp_settings["username"]
    password = smtp_settings["password"]

    if not username or not password:
        logger.info(
            "[EMAIL STUB] Would send to %s: %s (%d bytes)",
            to_email,
            subject,
            len(html_content),
        )
        return {
            "status": "stubbed",
            "to": to_email,
            "subject": subject,
            "html_bytes": len(html_content),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    message = EmailMessage()
    message_id = make_msgid(domain=sender.split("@", 1)[1] if "@" in sender else None)
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message["Message-ID"] = message_id
    message.set_content(_html_to_text(html_content))
    message.add_alternative(html_content, subtype="html")

    try:
        with _open_smtp_connection(smtp_settings["host"], smtp_settings["port"]) as server:
            server.login(username, password)
            server.send_message(message)
        logger.info("Email sent to %s: Message-ID=%s", to_email, message_id)
        return {
            "status": "sent",
            "to": to_email,
            "subject": subject,
            "message_id": message_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        return {
            "status": "failed",
            "to": to_email,
            "subject": subject,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def send_all_briefings(
    audience_html: dict[str, str],
    date_str: str,
    audience_emails: dict[str, str] | None = None,
    subject_prefix: str = "AI Weekly Briefing",
) -> list[dict]:
    """Send briefings to all audiences."""
    from briefing.config import AUDIENCE_PROFILES

    if audience_emails is None:
        audience_emails = {
            aid: _resolve_audience_email(aid, p["email"])
            for aid, p in AUDIENCE_PROFILES.items()
        }

    results = []
    for aud_id, html_content in audience_html.items():
        email = audience_emails.get(aud_id)
        if not email:
            logger.warning("No email for audience %s, skipping", aud_id)
            continue

        subject = f"{subject_prefix} — {date_str}"
        result = send_briefing_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
        )
        results.append(result)

    return results
