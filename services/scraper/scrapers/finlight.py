
"""
Finlight.me API client.

Rate limit: 10,000 requests/month ≈ 14 requests/hour.
We track daily usage in Redis to stay safely under the monthly cap.
Daily budget: 10,000 / 30 ≈ 333 requests/day.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Keep well under the monthly cap: 333 req/day leaves headroom.
DAILY_REQUEST_LIMIT = 300
RATE_LIMIT_KEY_PREFIX = "rate_limit:finlight"

# Finlight endpoint for financial headlines
BASE_URL = "https://api.finlight.me/v1"
ARTICLES_ENDPOINT = f"{BASE_URL}/articles"


def _rate_limit_key() -> str:
    """Redis key scoped to today's date."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{RATE_LIMIT_KEY_PREFIX}:{today}"


def _check_rate_limit(redis_client: Any) -> bool:
    """
    Return True if we are still under today's request budget.

    Args:
        redis_client: An active Redis client instance.
    """
    key = _rate_limit_key()
    count = redis_client.get(key)
    used = int(count) if count else 0
    if used >= DAILY_REQUEST_LIMIT:
        logger.warning("Finlight daily limit reached (%d/%d). Skipping.", used, DAILY_REQUEST_LIMIT)
        return False
    return True


def _increment_rate_limit(redis_client: Any) -> None:
    """Increment today's request counter; expire key at midnight (86400 s)."""
    key = _rate_limit_key()
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, 86400)
    pipe.execute()


def fetch_articles(
    api_key: str,
    redis_client: Any,
    query: str = "stocks OR earnings OR market OR finance",
    max_results: int = 25,
    retries: int = 3,
) -> list[dict]:
    """
    Fetch recent financial articles from Finlight.me.

    Args:
        api_key:      Finlight API key.
        redis_client: Active Redis client (used for rate-limit tracking).
        query:        Search query string.
        max_results:  Max articles to request per call.
        retries:      Number of retry attempts with exponential backoff.

    Returns:
        List of article dicts with keys:
        {title, content, url, source, published_at}
    """
    if not _check_rate_limit(redis_client):
        return []

    headers = {"X-API-KEY": api_key, "Accept": "application/json"}
    params = {
        "query": query,
        "limit": max_results,
        "language": "en",
    }

    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                ARTICLES_ENDPOINT,
                headers=headers,
                params=params,
                timeout=15,
            )
            _increment_rate_limit(redis_client)

            if response.status_code == 429:
                logger.warning("Finlight rate-limited (HTTP 429). Backing off %ds.", int(delay))
                time.sleep(delay)
                delay *= 2
                continue

            response.raise_for_status()
            data = response.json()

            articles = []
            for item in data.get("articles", []):
                # Normalise to our internal format
                articles.append({
                    "title":        item.get("title", "").strip(),
                    "content":      item.get("content") or item.get("description") or "",
                    "url":          item.get("url", ""),
                    "source":       item.get("source") if isinstance(item.get("source"), str) else (item.get("source") or {}).get("name", "finlight"),
                    "published_at": item.get("publishedAt"),
                })

            logger.info("Finlight returned %d articles.", len(articles))
            return articles

        except requests.exceptions.Timeout:
            logger.warning("Finlight request timed out (attempt %d/%d).", attempt, retries)
        except requests.exceptions.RequestException as exc:
            logger.error("Finlight request error (attempt %d/%d): %s", attempt, retries, exc)

        if attempt < retries:
            time.sleep(delay)
            delay *= 2

    logger.error("Finlight: all %d attempts failed.", retries)
    return []
