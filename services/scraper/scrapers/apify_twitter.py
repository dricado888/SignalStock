"""
Apify Twitter Scraper
=====================
Fetches recent tweets from a list of Twitter/X handles using the Apify
platform. Returns normalized article dicts compatible with the existing
articles table schema.

Actor used: quacker/twitter-scraper
  - Accepts a list of Twitter handles
  - Returns tweet objects with full_text, id_str, user, created_at

Env vars (read by caller in main.py):
  APIFY_API_TOKEN              — Apify API token (required)
  TWITTER_ACCOUNTS             — comma-separated handles, e.g. Reuters,WSJ
  TWITTER_MAX_TWEETS_PER_ACCOUNT — default 10
"""

import logging
import re
from datetime import datetime
from typing import Optional

MIN_MEANINGFUL_LEN = 30  # chars required after stripping URLs, emoji, whitespace


def _is_meaningful(text: str) -> bool:
    """Return True if tweet has enough real text content (not just emoji/URLs)."""
    clean = re.sub(r'http\S+', '', text)          # strip URLs
    clean = re.sub(r'[^\x00-\x7F]+', '', clean)   # strip non-ASCII (emoji, etc.)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return len(clean) >= MIN_MEANINGFUL_LEN

logger = logging.getLogger("scraper.apify_twitter")

APIFY_ACTOR = "quacker/twitter-scraper"


def _parse_twitter_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse Twitter's date format: 'Mon Mar 15 10:30:00 +0000 2026'"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
    except (ValueError, TypeError):
        return None


def _normalize(tweet: dict) -> Optional[dict]:
    """
    Convert an Apify tweet object into an articles-table-compatible dict.

    Handles output from quacker/twitter-scraper. Returns None if the tweet
    lacks the minimum required fields (id or text).
    """
    # quacker/twitter-scraper schema
    tweet_id   = tweet.get("id_str") or str(tweet.get("id", ""))
    full_text  = tweet.get("full_text") or tweet.get("text", "")
    user_obj   = tweet.get("user") or {}
    handle     = user_obj.get("screen_name") or tweet.get("author_id", "unknown")
    created_at = tweet.get("created_at")

    if not tweet_id or not full_text:
        return None
    if not _is_meaningful(full_text):
        return None

    url = f"https://twitter.com/{handle}/status/{tweet_id}"

    return {
        "title":        full_text[:500],
        "content":      f"@{handle}: {full_text}",
        "url":          url,
        "source":       "twitter",
        "published_at": _parse_twitter_date(created_at),
    }


def fetch_tweets(
    api_token: str,
    handles: list[str],
    max_per_handle: int = 10,
) -> list[dict]:
    """
    Run the Apify Twitter scraper actor and return normalized article dicts.

    Runs the actor synchronously (blocking until completion). Each handle
    contributes up to max_per_handle tweets. Total tweet cap is
    len(handles) * max_per_handle.

    Args:
        api_token:       Apify API token.
        handles:         List of Twitter screen names without '@'.
        max_per_handle:  Maximum tweets to fetch per account.

    Returns:
        List of normalized article dicts, ready for insert_article().
        Returns [] on any error so callers degrade gracefully.
    """
    try:
        from apify_client import ApifyClient
    except ImportError:
        logger.error(
            "apify-client is not installed. Run: pip install apify-client"
        )
        return []

    if not handles:
        logger.warning("No Twitter handles configured — skipping Twitter scrape.")
        return []

    client = ApifyClient(api_token)
    total_desired = len(handles) * max_per_handle

    logger.info(
        "Starting Apify actor '%s' for %d handle(s), up to %d tweet(s) total.",
        APIFY_ACTOR,
        len(handles),
        total_desired,
    )

    try:
        run = client.actor(APIFY_ACTOR).call(
            run_input={
                "handle":        handles,          # quacker/twitter-scraper uses "handle" (list)
                "tweetsDesired": total_desired,
                "addUserInfo":   True,
            }
        )
    except Exception as exc:
        logger.error("Apify actor run failed: %s", exc, exc_info=True)
        return []

    if not run or not run.get("defaultDatasetId"):
        logger.error("Apify run returned no dataset ID.")
        return []

    articles: list[dict] = []
    try:
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            normalized = _normalize(item)
            if normalized:
                articles.append(normalized)
    except Exception as exc:
        logger.error("Failed to read Apify dataset: %s", exc, exc_info=True)

    logger.info("Twitter: fetched and normalized %d tweet(s).", len(articles))
    return articles
