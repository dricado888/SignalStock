"""
SendGrid email client for SignalStock alert emails.

Uses SendGrid v3 Web API (Python SDK).
Free tier: 100 emails/day, no credit card required.
Sign up at: https://sendgrid.com
"""

import logging
import os
import time
from datetime import datetime
from typing import Optional

import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

import email_template

logger = logging.getLogger(__name__)


def send_alert_email(
    user_email: str,
    event: dict,
    stock: dict,
    article: dict,
    unsubscribe_token: str = "",
) -> bool:
    """
    Send a stock event alert email via SendGrid.

    Args:
        user_email: Recipient email address.
        event:      Dict with keys: {event_id, event_type, sentiment}.
        stock:      Dict with keys: {stock_id, ticker, company_name}.
        article:    Dict with keys: {article_id, title, url, published_at}.

    Returns:
        True if the email was sent successfully (HTTP 2xx), False otherwise.
    """
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    from_email = os.environ.get("SENDGRID_FROM_EMAIL", "")

    if not api_key:
        logger.error("SENDGRID_API_KEY not set. Cannot send email.")
        return False
    if not from_email:
        logger.error("SENDGRID_FROM_EMAIL not set. Cannot send email.")
        return False

    ticker       = stock["ticker"]
    company_name = stock["company_name"]
    event_type   = event["event_type"]
    sentiment    = event["sentiment"]

    app_base = os.environ.get("APP_BASE_URL", "http://localhost:5173")
    unsubscribe_url = (
        f"{app_base}/unsubscribe?token={unsubscribe_token}"
        if unsubscribe_token
        else f"{app_base}/settings"
    )

    subject = email_template.build_subject(event_type, sentiment, ticker)
    html    = email_template.build_html(
        ticker=ticker,
        company_name=company_name,
        event_type=event_type,
        sentiment=sentiment,
        article_title=article["title"],
        article_url=article["url"],
        published_at=article.get("published_at"),
        source=article.get("source"),
        unsubscribe_url=unsubscribe_url,
        manage_url=f"{app_base}/settings",
    )

    message = Mail(
        from_email=Email(from_email, "SignalStock"),
        to_emails=To(user_email),
        subject=subject,
        html_content=Content("text/html", html),
    )

    return _send_with_retry(api_key, message, user_email, ticker)


def _send_with_retry(
    api_key: str,
    message: Mail,
    user_email: str,
    ticker: str,
    max_attempts: int = 3,
) -> bool:
    """
    Attempt to send via SendGrid with retry logic for transient failures.

    Args:
        api_key:      SendGrid API key.
        message:      Constructed Mail object.
        user_email:   Used only for logging.
        ticker:       Used only for logging.
        max_attempts: Maximum send attempts before giving up.

    Returns:
        True on success, False if all attempts failed.
    """
    sg = sendgrid.SendGridAPIClient(api_key=api_key)
    delay = 10.0

    for attempt in range(1, max_attempts + 1):
        try:
            response = sg.send(message)
            status = response.status_code

            if 200 <= status < 300:
                logger.info(
                    "Alert sent to %s for %s (HTTP %d).",
                    user_email, ticker, status,
                )
                return True

            if status == 429:
                # Rate limited — sleep longer and retry
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(
                    "SendGrid rate limit hit. Sleeping %ds before retry.",
                    retry_after,
                )
                time.sleep(retry_after)
                continue

            if status in (400, 401, 403):
                # Permanent failures — no point retrying
                logger.error(
                    "SendGrid permanent error %d for %s. "
                    "Check SENDGRID_API_KEY and SENDGRID_FROM_EMAIL.",
                    status, user_email,
                )
                return False

            # Other 4xx/5xx — log and retry
            logger.warning(
                "SendGrid HTTP %d on attempt %d/%d for %s.",
                status, attempt, max_attempts, user_email,
            )

        except Exception as exc:
            logger.warning(
                "SendGrid request error (attempt %d/%d) for %s: %s",
                attempt, max_attempts, user_email, exc,
            )

        if attempt < max_attempts:
            time.sleep(delay)
            delay *= 2

    logger.error(
        "Failed to send alert to %s for %s after %d attempts.",
        user_email, ticker, max_attempts,
    )
    return False
