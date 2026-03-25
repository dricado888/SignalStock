"""
Google Gemini API client for financial news event classification.

Rate limit (free tier): 60 req/min, but we self-impose 40 req/hour to
stay conservative and avoid burst issues. Usage is tracked per clock-hour
in Redis so limits survive restarts.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Valid values enforced by DB CHECK constraint and downstream logic
VALID_EVENT_TYPES = {
    "earnings_beat", "earnings_miss", "product_launch", "acquisition",
    "partnership", "regulatory", "recall", "leadership_change",
    "ipo", "buyback", "market_downturn", "merger", "other",
}
VALID_SENTIMENTS = {"positive", "negative", "neutral"}

HOURLY_REQUEST_LIMIT = 40
RATE_LIMIT_KEY_PREFIX = "rate_limit:gemini"

# Prompt instructs Gemini to return strict JSON so we can parse it reliably.
CLASSIFICATION_PROMPT = """\
You are a financial news classifier. Analyze the article below and return ONLY a JSON object — no markdown, no explanation, just raw JSON.

JSON schema:
{{
  "event_type": one of [{event_types}],
  "sentiment": one of ["positive", "negative", "neutral"],
  "tickers": list of stock ticker symbols explicitly mentioned (e.g. ["AAPL", "NVDA"]), empty list if none
}}

Rules:
- event_type must be the single best-fitting category
- sentiment reflects the likely market impact (positive = good for stock price)
- tickers: only include uppercase ticker symbols that are clearly referenced
- If the article is not clearly about a financial event, use "other" and "neutral"

Article title: {title}

Article content:
{content}
"""


def _rate_limit_key() -> str:
    """Redis key scoped to the current UTC hour."""
    now = datetime.now(timezone.utc)
    return f"{RATE_LIMIT_KEY_PREFIX}:{now.strftime('%Y-%m-%d-%H')}"


def _check_rate_limit(redis_client: Any) -> bool:
    """
    Return True if we are under the hourly Gemini request budget.

    Args:
        redis_client: Active Redis client instance.
    """
    key = _rate_limit_key()
    count = redis_client.get(key)
    used = int(count) if count else 0
    if used >= HOURLY_REQUEST_LIMIT:
        logger.warning(
            "Gemini hourly limit reached (%d/%d). Will wait for next hour.",
            used, HOURLY_REQUEST_LIMIT,
        )
        return False
    return True


def _increment_rate_limit(redis_client: Any) -> None:
    """Increment the hourly counter; expire after 2 hours to auto-clean."""
    key = _rate_limit_key()
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, 7200)  # 2 hours
    pipe.execute()


def seconds_until_next_hour() -> int:
    """Return seconds remaining until the top of the next UTC hour."""
    now = datetime.now(timezone.utc)
    seconds_elapsed = now.minute * 60 + now.second
    return 3600 - seconds_elapsed


def wait_for_rate_limit_reset(redis_client: Any) -> None:
    """
    Block until the Gemini hourly rate limit resets.

    Checks every 30 seconds so we start processing as soon as the hour turns.

    Args:
        redis_client: Active Redis client instance.
    """
    wait_secs = seconds_until_next_hour()
    logger.info("Rate limit hit. Waiting %ds for the next hour window.", wait_secs)
    while not _check_rate_limit(redis_client):
        time.sleep(30)
    logger.info("Rate limit reset. Resuming classification.")


def classify_article(
    article: dict,
    redis_client: Any,
    model_name: str = "gemini-2.0-flash",
) -> dict | None:
    """
    Classify a single article using the Gemini API.

    Sends the article title + content to Gemini and parses the returned JSON.
    On invalid JSON or unexpected response shape, falls back to
    event_type="other" / sentiment="neutral" / tickers=[].

    Args:
        article:      Dict with at least {id, title, content}.
        redis_client: Active Redis client (for rate-limit tracking).
        model_name:   Gemini model to use.

    Returns:
        Dict with keys {event_type, sentiment, tickers}, or None if the
        API call failed (caller should re-queue the article).
    """
    # Block if we've exhausted this hour's budget
    if not _check_rate_limit(redis_client):
        wait_for_rate_limit_reset(redis_client)

    prompt = CLASSIFICATION_PROMPT.format(
        event_types=", ".join(f'"{e}"' for e in sorted(VALID_EVENT_TYPES)),
        title=article.get("title", ""),
        content=(article.get("content") or "")[:4000],  # cap tokens
    )

    model = genai.GenerativeModel(model_name)
    delay = 60  # start with 60s on rate limit
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=256,
                ),
            )
            _increment_rate_limit(redis_client)

            raw_text = response.text.strip()
            result = _parse_response(raw_text)
            logger.info(
                "Classified article id=%d → type=%s sentiment=%s tickers=%s",
                article["id"], result["event_type"], result["sentiment"], result["tickers"],
            )
            return result

        except Exception as exc:
            err_str = str(exc)

            # Permanent: bad API key
            if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                logger.critical("Gemini API key is invalid. Fix GEMINI_API_KEY in .env and restart.")
                raise SystemExit(1)

            # Permanent: wrong model name
            if "is not found" in err_str and "404" in err_str:
                logger.critical("Gemini model '%s' not found. Fix model name and restart.", model_name)
                raise SystemExit(1)

            # Rate limited (429) — sleep and retry, do NOT re-queue
            if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower():
                if attempt < max_retries:
                    logger.warning(
                        "Gemini rate limit hit (attempt %d/%d). Sleeping %ds before retry.",
                        attempt, max_retries, delay,
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    logger.error(
                        "Gemini rate limit persists after %d retries for article id=%d. "
                        "Daily quota may be exhausted — restart tomorrow or upgrade plan.",
                        max_retries, article.get("id"),
                    )
                    raise SystemExit(1)

            # Transient error — log and let caller re-queue
            logger.error(
                "Gemini API error for article id=%d (attempt %d/%d): %s",
                article.get("id"), attempt, max_retries, exc,
            )
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            return None  # re-queue after all retries exhausted


def _parse_response(raw: str) -> dict:
    """
    Parse Gemini's raw text response into a validated classification dict.

    Falls back to {other, neutral, []} if JSON is malformed or fields are invalid.

    Args:
        raw: Raw text from Gemini response.

    Returns:
        Dict with {event_type, sentiment, tickers}.
    """
    fallback = {"event_type": "other", "sentiment": "neutral", "tickers": []}

    # Strip markdown code fences if Gemini wraps in ```json ... ```
    text = raw
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON: %.200s", raw)
        return fallback

    event_type = data.get("event_type", "other")
    sentiment  = data.get("sentiment", "neutral")
    tickers    = data.get("tickers", [])

    # Validate and sanitise
    if event_type not in VALID_EVENT_TYPES:
        logger.warning("Unknown event_type '%s', defaulting to 'other'.", event_type)
        event_type = "other"

    if sentiment not in VALID_SENTIMENTS:
        logger.warning("Unknown sentiment '%s', defaulting to 'neutral'.", sentiment)
        sentiment = "neutral"

    if not isinstance(tickers, list):
        tickers = []
    else:
        # Keep only plausible ticker strings (1-5 uppercase letters)
        tickers = [
            t for t in tickers
            if isinstance(t, str) and t.isupper() and 1 <= len(t) <= 5
        ]

    return {"event_type": event_type, "sentiment": sentiment, "tickers": tickers}
