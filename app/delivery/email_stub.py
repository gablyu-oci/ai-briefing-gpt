"""
email_stub.py — Email delivery stub (Postmark-ready interface).

This module provides the interface for email delivery but does not
actually send emails. It's ready to be wired to Postmark or any
other email provider.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailDelivery:
    """
    Postmark-ready email delivery interface.

    To activate, set environment variables:
        POSTMARK_API_TOKEN=your-token
        POSTMARK_FROM_EMAIL=briefing@yourdomain.com
    """

    def __init__(self, api_token: str | None = None, from_email: str | None = None):
        self.api_token = api_token
        self.from_email = from_email or "ai-briefing@oracle.com"
        self.enabled = api_token is not None

    def send_briefing(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        audience_id: str,
    ) -> dict:
        """
        Send a briefing email.

        Returns a dict with delivery status:
            {"status": "sent"|"stubbed", "message_id": str, "timestamp": str}
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        if not self.enabled:
            logger.info(
                "[EMAIL STUB] Would send to %s: '%s' (%d bytes HTML)",
                to_email, subject, len(html_content),
            )
            return {
                "status": "stubbed",
                "to": to_email,
                "subject": subject,
                "message_id": f"stub-{audience_id}-{timestamp}",
                "timestamp": timestamp,
            }

        # TODO: Implement actual Postmark API call
        # import requests
        # response = requests.post(
        #     "https://api.postmarkapp.com/email",
        #     headers={
        #         "X-Postmark-Server-Token": self.api_token,
        #         "Content-Type": "application/json",
        #     },
        #     json={
        #         "From": self.from_email,
        #         "To": to_email,
        #         "Subject": subject,
        #         "HtmlBody": html_content,
        #         "MessageStream": "outbound",
        #     },
        # )

        logger.info("[EMAIL] Sent to %s: '%s'", to_email, subject)
        return {
            "status": "sent",
            "to": to_email,
            "subject": subject,
            "message_id": f"postmark-{audience_id}-{timestamp}",
            "timestamp": timestamp,
        }

    def send_all_briefings(
        self,
        briefing_paths: dict[str, Path],
        audience_emails: dict[str, str],
        date_str: str,
    ) -> list[dict]:
        """
        Send briefings to all audiences.
        Returns list of delivery results.
        """
        results = []
        for audience_id, path in briefing_paths.items():
            if audience_id == "index":
                continue

            email = audience_emails.get(audience_id)
            if not email:
                logger.warning("No email configured for audience %s", audience_id)
                continue

            html_content = path.read_text(encoding="utf-8")
            subject = f"AI Daily Briefing — {date_str}"

            result = self.send_briefing(
                to_email=email,
                subject=subject,
                html_content=html_content,
                audience_id=audience_id,
            )
            results.append(result)

        return results
