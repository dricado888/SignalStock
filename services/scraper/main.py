"""
SignalStock News Scraper
========================
Fetches financial articles from Finlight and NewsAPI, deduplicates by URL,
persists to PostgreSQL, and enqueues article IDs to Redis for downstream
classification.

Runs as an infinite loop; each cycle sleeps POLL_INTERVAL_SECONDS (default 300).
"""

import logging
import os
import sys
import time
from typing import Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool
import redis
from dotenv import load_dotenv

from scrapers import finlight, newsapi, rss
from scrapers import apify_twitter

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("scraper.main")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

FINLIGHT_API_KEY: str    = os.environ["FINLIGHT_API_KEY"]
NEWSAPI_KEY: str         = os.environ["NEWSAPI_KEY"]
DATABASE_URL: str        = os.environ["DATABASE_URL"]
REDIS_URL: str           = os.environ.get("REDIS_URL", "redis://localhost:6379")
POLL_INTERVAL_SECONDS: int = int(os.environ.get("POLL_INTERVAL_SECONDS", "300"))
REDIS_QUEUE_KEY: str     = "articles:pending"

# Twitter / Apify config (optional — Twitter scraping is skipped if token absent)
APIFY_API_TOKEN: str          = os.environ.get("APIFY_API_TOKEN", "")
TWITTER_ACCOUNTS: str         = os.environ.get("TWITTER_ACCOUNTS", "")
TWITTER_POLL_INTERVAL: int    = int(os.environ.get("TWITTER_POLL_INTERVAL_SECONDS", "21600"))
TWITTER_MAX_PER_ACCOUNT: int  = int(os.environ.get("TWITTER_MAX_TWEETS_PER_ACCOUNT", "10"))

# Tracks when the last Twitter poll ran (monotonic seconds)
_last_twitter_poll: float = 0.0

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def create_db_pool(dsn: str, min_conn: int = 1, max_conn: int = 5) -> psycopg2.pool.ThreadedConnectionPool:
    """
    Create a threaded psycopg2 connection pool.

    Args:
        dsn:      PostgreSQL connection string.
        min_conn: Minimum idle connections.
        max_conn: Maximum connections in pool.
    """
    return psycopg2.pool.ThreadedConnectionPool(min_conn, max_conn, dsn=dsn)


def article_exists(conn: psycopg2.extensions.connection, url: str) -> bool:
    """
    Check whether an article with the given URL is already in the database.

    Args:
        conn: An active psycopg2 connection.
        url:  Article URL to look up.

    Returns:
        True if the article is already stored.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM articles WHERE url = %s", (url,))
        return cur.fetchone() is not None


def insert_article(conn: psycopg2.extensions.connection, article: dict) -> Optional[int]:
    """
    Insert one article row and return its new database ID.

    Performs no-op if a race condition causes a duplicate URL (ON CONFLICT).

    Args:
        conn:    An active psycopg2 connection.
        article: Dict with keys: title, content, url, source, published_at.

    Returns:
        The new article ID, or None if insertion was skipped.
    """
    sql = """
        INSERT INTO articles (title, content, url, source, published_at)
        VALUES (%(title)s, %(content)s, %(url)s, %(source)s, %(published_at)s)
        ON CONFLICT (url) DO NOTHING
        RETURNING id
    """
    with conn.cursor() as cur:
        cur.execute(sql, article)
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

def create_redis_client(url: str) -> redis.Redis:
    """
    Create and return a Redis client, verifying connectivity with PING.

    Args:
        url: Redis connection URL (e.g. redis://localhost:6379).
    """
    client = redis.from_url(url, decode_responses=True)
    client.ping()   # raises ConnectionError immediately if unreachable
    return client


def enqueue_article(redis_client: redis.Redis, article_id: int) -> None:
    """
    Push an article ID onto the pending-articles Redis queue.

    Args:
        redis_client: Active Redis client.
        article_id:   Integer ID from the articles table.
    """
    redis_client.lpush(REDIS_QUEUE_KEY, article_id)


# ---------------------------------------------------------------------------
# Core scrape cycle
# ---------------------------------------------------------------------------

def scrape_and_store(
    pool: psycopg2.pool.ThreadedConnectionPool,
    redis_client: redis.Redis,
) -> int:
    """
    Run one full scrape cycle: fetch → deduplicate → store → enqueue.

    Fetches from both Finlight and NewsAPI; failures in one source do not
    prevent the other from running.

    Args:
        pool:         psycopg2 connection pool.
        redis_client: Active Redis client.

    Returns:
        Number of new articles inserted this cycle.
    """
    # Gather raw articles from both sources
    raw_articles: list[dict] = []

    try:
        fl_articles = finlight.fetch_articles(FINLIGHT_API_KEY, redis_client)
        logger.info("Finlight: fetched %d articles.", len(fl_articles))
        raw_articles.extend(fl_articles)
    except Exception as exc:
        logger.error("Finlight scrape failed: %s", exc, exc_info=True)

    try:
        na_articles = newsapi.fetch_articles(NEWSAPI_KEY, redis_client)
        logger.info("NewsAPI: fetched %d articles.", len(na_articles))
        raw_articles.extend(na_articles)
    except Exception as exc:
        logger.error("NewsAPI scrape failed: %s", exc, exc_info=True)

    try:
        rss_articles = rss.fetch_articles()
        logger.info("RSS: fetched %d articles total.", len(rss_articles))
        raw_articles.extend(rss_articles)
    except Exception as exc:
        logger.error("RSS scrape failed: %s", exc, exc_info=True)

    # Twitter — only run when Apify token is configured and interval has elapsed
    global _last_twitter_poll
    if APIFY_API_TOKEN and (time.time() - _last_twitter_poll >= TWITTER_POLL_INTERVAL):
        handles = [h.strip() for h in TWITTER_ACCOUNTS.split(",") if h.strip()]
        try:
            tw_articles = apify_twitter.fetch_tweets(
                APIFY_API_TOKEN, handles, TWITTER_MAX_PER_ACCOUNT
            )
            logger.info("Twitter: fetched %d tweets.", len(tw_articles))
            raw_articles.extend(tw_articles)
            _last_twitter_poll = time.time()
        except Exception as exc:
            logger.error("Twitter scrape failed: %s", exc, exc_info=True)
    elif not APIFY_API_TOKEN:
        logger.debug("APIFY_API_TOKEN not set — Twitter scraping disabled.")

    if not raw_articles:
        logger.info("No articles fetched this cycle.")
        return 0

    # Remove intra-batch URL duplicates before hitting the DB
    seen_urls: set[str] = set()
    unique_articles: list[dict] = []
    for a in raw_articles:
        url = a.get("url", "").strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(a)

    logger.info("After dedup: %d unique articles to evaluate.", len(unique_articles))

    new_count = 0
    conn = pool.getconn()
    try:
        for article in unique_articles:
            url = article.get("url", "").strip()

            # Skip articles with no URL or no meaningful content
            if not url or not article.get("title"):
                logger.debug("Skipping article with missing url/title.")
                continue

            try:
                if article_exists(conn, url):
                    logger.debug("Duplicate, skipping: %s", url)
                    continue

                article_id = insert_article(conn, article)
                if article_id is None:
                    # ON CONFLICT branch: another process inserted concurrently
                    logger.debug("Concurrent insert for URL: %s", url)
                    continue

                enqueue_article(redis_client, article_id)
                new_count += 1
                logger.info("Stored & queued article id=%d: %.80s", article_id, article["title"])

            except Exception as exc:
                logger.error("Failed to store article '%s': %s", url, exc, exc_info=True)
                conn.rollback()

    finally:
        pool.putconn(conn)

    logger.info("Cycle complete: %d new articles stored.", new_count)
    return new_count


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Main loop: connect to dependencies, then scrape on a fixed interval.
    Exits with code 1 if initial dependency connections fail.
    """
    logger.info("SignalStock scraper starting up.")

    # Connect to PostgreSQL
    try:
        pool = create_db_pool(DATABASE_URL)
        logger.info("PostgreSQL connection pool created.")
    except Exception as exc:
        logger.critical("Cannot connect to PostgreSQL: %s", exc)
        sys.exit(1)

    # Connect to Redis
    try:
        redis_client = create_redis_client(REDIS_URL)
        logger.info("Redis connected.")
    except Exception as exc:
        logger.critical("Cannot connect to Redis: %s", exc)
        sys.exit(1)

    logger.info(
        "Scraper ready. Poll interval: %ds. Press Ctrl+C to stop.",
        POLL_INTERVAL_SECONDS,
    )

    while True:
        try:
            scrape_and_store(pool, redis_client)
        except KeyboardInterrupt:
            logger.info("Interrupted by user. Shutting down.")
            break
        except Exception as exc:
            # Catch-all so the loop never crashes permanently
            logger.error("Unexpected error in scrape cycle: %s", exc, exc_info=True)

        logger.info("Sleeping %ds until next cycle.", POLL_INTERVAL_SECONDS)
        try:
            time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("Interrupted during sleep. Shutting down.")
            break

    pool.closeall()
    logger.info("Scraper shut down cleanly.")


if __name__ == "__main__":
    main()
