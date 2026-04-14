"""
test_email_delivery.py — Tests for Gmail SMTP delivery configuration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.delivery import email_delivery


def test_resolve_smtp_settings_supports_gmail_secret_file(tmp_path, monkeypatch):
    secret_file = tmp_path / "gmail_secret.txt"
    secret_file.write_text("app-password-123\n", encoding="utf-8")

    monkeypatch.setenv("GMAIL_USER", "briefing@example.com")
    monkeypatch.setenv("GMAIL_SECRET_FILE", str(secret_file))
    monkeypatch.delenv("GMAIL_SECRET", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)

    settings = email_delivery._resolve_smtp_settings()

    assert settings["host"] == "smtp.gmail.com"
    assert settings["port"] == 465
    assert settings["username"] == "briefing@example.com"
    assert settings["password"] == "app-password-123"
    assert settings["sender"] == "briefing@example.com"


def test_send_briefing_email_stubs_when_credentials_missing(monkeypatch):
    for key in [
        "EMAIL_SMTP_USER",
        "SMTP_USERNAME",
        "GMAIL_USER",
        "GMAIL_EMAIL",
        "EMAIL_SMTP_PASSWORD",
        "SMTP_PASSWORD",
        "GMAIL_APP_PASSWORD",
        "GMAIL_PASSWORD",
        "GMAIL_SECRET",
        "EMAIL_SMTP_PASSWORD_FILE",
        "SMTP_PASSWORD_FILE",
        "GMAIL_APP_PASSWORD_FILE",
        "GMAIL_SECRET_FILE",
    ]:
        monkeypatch.delenv(key, raising=False)

    result = email_delivery.send_briefing_email(
        to_email="exec@example.com",
        subject="Weekly Briefing",
        html_content="<h1>Hello</h1>",
    )

    assert result["status"] == "stubbed"
    assert result["to"] == "exec@example.com"


def test_resolve_audience_email_prefers_env_override(monkeypatch):
    monkeypatch.setenv("BRIEFING_EMAIL_GREG", "greg.real@example.com")

    resolved = email_delivery._resolve_audience_email("greg", "greg@example.com")

    assert resolved == "greg.real@example.com"
