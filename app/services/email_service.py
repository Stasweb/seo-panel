from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings


class EmailService:
    def is_configured(self) -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)

    async def send_email(self, *, to_email: str, subject: str, body: str) -> bool:
        if not to_email:
            return False
        if not self.is_configured():
            return False

        msg = EmailMessage()
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        def _send():
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
                if settings.SMTP_USE_TLS:
                    smtp.starttls()
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(msg)

        try:
            await asyncio.to_thread(_send)
            return True
        except Exception:
            return False


email_service = EmailService()

