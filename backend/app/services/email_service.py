"""
Real SMTP email dispatch service for okDRIVER civic authority notifications.

Uses Gmail SMTP (TLS/STARTTLS) when credentials are configured; falls back
to simulated logging mode so the rest of the pipeline always works.
"""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger("okdriver.email")


class EmailService:
    """SMTP email dispatcher with Gmail support and graceful fallback."""

    def __init__(self) -> None:
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_addr = settings.SMTP_FROM or settings.SMTP_USER
        self.use_tls = settings.SMTP_USE_TLS
        self._enabled = bool(self.user and self.password)

        if self._enabled:
            logger.info(
                "EmailService initialized: %s:%d (user=%s)", self.host, self.port, self.user
            )
        else:
            logger.warning(
                "EmailService: SMTP credentials not configured — running in SIMULATED mode."
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    def send(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an email via SMTP.

        Returns a dict with 'delivered', 'message_id', and 'error' keys.
        Never raises — errors are caught and returned in the dict.
        """
        if not self._enabled:
            return self._simulate(to, subject)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to
        if reply_to:
            msg["Reply-To"] = reply_to

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
                smtp.ehlo()
                if self.use_tls:
                    smtp.starttls(context=context)
                    smtp.ehlo()
                smtp.login(self.user, self.password)
                smtp.sendmail(self.from_addr, [to], msg.as_string())

            message_id = msg.get("Message-ID", f"<sent@{self.host}>")
            logger.info("Email sent to %s | Subject: %s", to, subject)
            return {
                "delivered": True,
                "message_id": message_id,
                "recipient": to,
                "subject": subject,
                "error": None,
            }

        except smtplib.SMTPAuthenticationError as e:
            logger.error("SMTP auth failed: %s", e)
            return {
                "delivered": False,
                "message_id": None,
                "recipient": to,
                "subject": subject,
                "error": f"Authentication failed: {e}",
            }
        except Exception as e:
            logger.error("SMTP send error: %s", e)
            return {
                "delivered": False,
                "message_id": None,
                "recipient": to,
                "subject": subject,
                "error": str(e),
            }

    def _simulate(self, to: str, subject: str) -> Dict[str, Any]:
        """Return a simulated successful dispatch without sending."""
        import uuid
        message_id = f"<simulated-{uuid.uuid4().hex[:12]}@okdriver.local>"
        logger.info("[SIMULATED] Email to %s | %s", to, subject)
        return {
            "delivered": True,
            "message_id": message_id,
            "recipient": to,
            "subject": subject,
            "error": None,
            "simulated": True,
        }


# Module-level singleton
email_service = EmailService()
