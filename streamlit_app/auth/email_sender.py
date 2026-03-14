"""Email sending for verification and password reset.

Uses SMTP credentials from environment variables:
  NANOBOT_SMTP_HOST, NANOBOT_SMTP_PORT, NANOBOT_SMTP_USER, NANOBOT_SMTP_PASS, NANOBOT_SMTP_FROM
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _smtp_config() -> dict:
    return {
        "host": os.environ.get("NANOBOT_SMTP_HOST", ""),
        "port": int(os.environ.get("NANOBOT_SMTP_PORT", "587")),
        "user": os.environ.get("NANOBOT_SMTP_USER", ""),
        "password": os.environ.get("NANOBOT_SMTP_PASS", ""),
        "from_addr": os.environ.get("NANOBOT_SMTP_FROM", ""),
    }


def _send(to: str, subject: str, html_body: str) -> bool:
    """Send an email.  Returns True on success."""
    cfg = _smtp_config()
    if not all([cfg["host"], cfg["user"], cfg["password"], cfg["from_addr"]]):
        logger.warning("SMTP not configured — email not sent to %s (subject: %s)", to, subject)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from_addr"]
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(cfg["user"], cfg["password"])
            smtp.sendmail(cfg["from_addr"], [to], msg.as_string())
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def send_verification_email(to: str, token: str, base_url: str) -> bool:
    """Send email-confirmation link."""
    link = f"{base_url.rstrip('/')}/verify-email?token={token}"
    html = f"""
    <h2>Confirm your email</h2>
    <p>Click the link below to verify your account:</p>
    <p><a href="{link}">{link}</a></p>
    <p>This link expires in 48 hours.</p>
    """
    return _send(to, "Verify your Nanobot account", html)


def send_password_reset_email(to: str, token: str, base_url: str) -> bool:
    """Send password-reset link."""
    link = f"{base_url.rstrip('/')}/reset-password?token={token}"
    html = f"""
    <h2>Reset your password</h2>
    <p>Click below to set a new password:</p>
    <p><a href="{link}">{link}</a></p>
    <p>This link expires in 1 hour. If you didn't request this, ignore this email.</p>
    """
    return _send(to, "Password Reset — Nanobot", html)
