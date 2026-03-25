"""
NewsAPI.org client.

Rate limit (free plan): 100 requests/day ≈ 4 requests/hour.
We track daily usage in Redis and enforce a hard ceiling of 90 req/day
to leave a safety margin.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Stay under the 100 req/day free-plan cap.
DAILY_REQUEST_LIMIT = 90
RATE_LIMIT_KEY_PREFIX = "rate_limit:newsapi"

BASE_URL = "https://newsapi.org/v2"
TOP_HEADLINES_ENDPOINT = f"{BASE_URL}/top-headlines"
EVERYTHING_ENDPOINT = f"{BASE_URL}/everything"


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
        logger.warning("NewsAPI daily limit reached (%d/%d). Skipping.", used, DAILY_REQUEST_LIMIT)
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
    max_results: int = 20,
    retries: int = 3,
) -> list[dict]:
    """
    Fetch top business/finance headlines from NewsAPI.

    Calls the `top-headlines` endpoint with category=business first,
    then falls back to `everything` with finance-focused keywords if
    the first call returns few results.

    Args:
        api_key:      NewsAPI key.
        redis_client: Active Redis client (used for rate-limit tracking).
        max_results:  Max articles per request (capped at 100 by NewsAPI).
        retries:      Number of retry attempts with exponential backoff.

    Returns:
        List of article dicts with keys:
        {title, content, url, source, published_at}
    """
    if not _check_rate_limit(redis_client):
        return []

    articles: list[dict] = []

    # --- Attempt 1: business top-headlines ---------------------------------
    articles = _request(
        endpoint=TOP_HEADLINES_ENDPOINT,
        params={
            "apiKey":   api_key,
            "category": "business",
            "language": "en",
            "pageSize": max_results,
        },
        redis_client=redis_client,
        retries=retries,
    )

    # --- Attempt 2: keyword search if headlines returned nothing -----------
    if not articles:
        if not _check_rate_limit(redis_client):
            return []
        articles = _request(
            endpoint=EVERYTHING_ENDPOINT,
            params={
                "apiKey":    api_key,
                "q":         "stocks OR earnings OR IPO OR market OR finance",
                "language":  "en",
                "sortBy":    "publishedAt",
                "pageSize":  max_results,
            },
            redis_client=redis_client,
            retries=retries,
        )

    logger.info("NewsAPI returned %d articles total.", len(articles))
    return articles


def _request(
    endpoint: str,
    params: dict,
    redis_client: Any,
    retries: int,
) -> list[dict]:
    """
    Internal helper: make one API call with retry + exponential backoff.

    Args:
        endpoint:     Full URL to call.
        params:       Query parameters (includes apiKey).
        redis_client: Redis client for rate-limit tracking.
        retries:      Max number of attempts.

    Returns:
        Normalised list of article dicts, or empty list on failure.
    """
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(endpoint, params=params, timeout=15)
            _increment_rate_limit(redis_client)

            if response.status_code == 429:
                logger.warning("NewsAPI rate-limited (HTTP 429). Backing off %ds.", int(delay))
                time.sleep(delay)
                delay *= 2
                continue

            if response.status_code == 426:
                # Developer plan restriction; log and bail out
                logger.warning("NewsAPI requires a paid plan for this endpoint. Skipping.")
                return []

            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                logger.error("NewsAPI error response: %s", data.get("message", "unknown"))
                return []

            return _normalise(data.get("articles", []))

        except requests.exceptions.Timeout:
            logger.warning("NewsAPI request timed out (attempt %d/%d).", attempt, retries)
        except requests.exceptions.RequestException as exc:
            logger.error("NewsAPI request error (attempt %d/%d): %s", attempt, retries, exc)

        if attempt < retries:
            time.sleep(delay)
            delay *= 2

    logger.error("NewsAPI: all %d attempts failed for %s.", retries, endpoint)
    return []


def _normalise(raw_articles: list[dict]) -> list[dict]:
    """
    Convert NewsAPI article objects to the shared internal format.

    Args:
        raw_articles: List of raw dicts from the NewsAPI response.

    Returns:
        Normalised list with {title, content, url, source, published_at}.
    """
    results = []
    for item in raw_articles:
        # NewsAPI sometimes returns [Removed] articles for removed content
        url = item.get("url", "")
        if not url or "removed" in url.lower():
            continue

        results.append({
            "title":        (item.get("title") or "").strip(),
            "content":      item.get("content") or item.get("description") or "",
            "url":          url,
            "source":       item.get("source", {}).get("name", "newsapi"),
            "published_at": item.get("publishedAt"),
        })
    return results
