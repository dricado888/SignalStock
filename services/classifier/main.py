"""
SignalStock Event Classifier
============================
Consumes article IDs from the Redis queue "articles:pending", fetches each
article from PostgreSQL, classifies it via Hugging Face free serverless inference, and writes the result to
the events + event_stocks tables.

Flow per article:
  Redis BRPOP articles:pending
      → fetch article from DB
      → skip if already classified
      → call HF inference → {event_type, sentiment, confidence}
      → INSERT into events
      → on failure → RPUSH back to queue (retry later)
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

import hf_client

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("classifier.main")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

DATABASE_URL: str    = os.environ["DATABASE_URL"]
REDIS_URL: str       = os.environ.get("REDIS_URL", "redis://localhost:6379")
QUEUE_KEY: str       = "articles:pending"
# BRPOP timeout in seconds; 0 = block forever, >0 = allows graceful shutdown checks
BRPOP_TIMEOUT: int   = int(os.environ.get("BRPOP_TIMEOUT", "10"))

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def create_db_pool(dsn: str) -> psycopg2.pool.ThreadedConnectionPool:
    """Create a psycopg2 connection pool."""
    return psycopg2.pool.ThreadedConnectionPool(1, 5, dsn=dsn)


def fetch_article(conn: psycopg2.extensions.connection, article_id: int) -> Optional[dict]:
    """
    Fetch a single article row by ID.

    Args:
        conn:       Active psycopg2 connection.
        article_id: Row ID in the articles table.

    Returns:
        Dict with article fields, or None if not found.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT id, title, content, url, source FROM articles WHERE id = %s",
            (article_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def is_already_classified(conn: psycopg2.extensions.connection, article_id: int) -> bool:
    """
    Return True if at least one event already exists for this article.

    Args:
        conn:       Active psycopg2 connection.
        article_id: Article to check.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM events WHERE article_id = %s LIMIT 1", (article_id,))
        return cur.fetchone() is not None


def insert_event(
    conn: psycopg2.extensions.connection,
    article_id: int,
    event_type: str,
    sentiment: str,
) -> int:
    """
    Insert one event row and return its new ID.

    Args:
        conn:       Active psycopg2 connection.
        article_id: FK to articles table.
        event_type: Classified event category string.
        sentiment:  'positive', 'negative', or 'neutral'.

    Returns:
        Newly created event ID.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO events (article_id, event_type, sentiment, classified_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING id
            """,
            (article_id, event_type, sentiment),
        )
        row = cur.fetchone()
        conn.commit()
        return row[0]



# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_article(
    article_id: int,
    pool: psycopg2.pool.ThreadedConnectionPool,
    rc: redis.Redis,
) -> None:
    """
    Full pipeline for a single article: fetch → classify → store.

    On classification failure the article ID is pushed back to the tail of
    the queue so it will be retried after other pending articles.

    Args:
        article_id:   ID popped from the Redis queue.
        pool:         psycopg2 connection pool.
        rc: Active Redis client.
    """
    conn = pool.getconn()
    try:
        # 1. Fetch article
        article = fetch_article(conn, article_id)
        if not article:
            logger.warning("Article id=%d not found in DB. Discarding.", article_id)
            return

        # 2. Deduplication check
        if is_already_classified(conn, article_id):
            logger.info("Article id=%d already classified. Skipping.", article_id)
            return

        # 3. Classify via HF inference
        result = hf_client.classify_article(
            title=article.get("title", ""),
            content=article.get("content", ""),
        )

        # confidence=0.0 + event_type="other" is the all-models-failed sentinel
        if result.get("confidence", 1.0) == 0.0 and result.get("event_type") == "other":
            if result.get("_permanent_failure"):
                logger.error(
                    "Classification permanently failed for article id=%d "
                    "(all models unavailable). Discarding — check HF_TOKEN or try later.",
                    article_id,
                )
            else:
                logger.warning("Classification failed for article id=%d. Re-queuing.", article_id)
                rc.rpush(QUEUE_KEY, article_id)
            return

        # 4. Persist event
        event_id = insert_event(
            conn,
            article_id,
            result["event_type"],
            result["sentiment"],
        )

        logger.info(
            "Saved event id=%d for article id=%d (type=%s, sentiment=%s, confidence=%.2f).",
            event_id, article_id,
            result["event_type"], result["sentiment"], result.get("confidence", 0.0),
        )

    except Exception as exc:
        logger.error(
            "Unexpected error processing article id=%d: %s",
            article_id, exc, exc_info=True,
        )
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        pool.putconn(conn)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Main loop: block on Redis queue and process articles as they arrive.

    Uses BRPOP so the process idles (no CPU spin) when the queue is empty.
    Exits cleanly on KeyboardInterrupt.
    """
    logger.info("SignalStock classifier starting up.")

    # Connect to PostgreSQL
    try:
        pool = create_db_pool(DATABASE_URL)
        logger.info("PostgreSQL connection pool created.")
    except Exception as exc:
        logger.critical("Cannot connect to PostgreSQL: %s", exc)
        sys.exit(1)

    # Connect to Redis
    try:
        rc = redis.from_url(REDIS_URL, decode_responses=True)
        rc.ping()
        logger.info("Redis connected.")
    except Exception as exc:
        logger.critical("Cannot connect to Redis: %s", exc)
        sys.exit(1)

    queue_depth = rc.llen(QUEUE_KEY)
    logger.info(
        "Classifier ready. Queue depth: %d. Waiting for articles (Ctrl+C to stop).",
        queue_depth,
    )

    while True:
        try:
            # BRPOP blocks for BRPOP_TIMEOUT seconds then returns None
            # This lets us catch KeyboardInterrupt between polls.
            result = rc.brpop(QUEUE_KEY, timeout=BRPOP_TIMEOUT)
            if result is None:
                # Timeout — queue is empty, loop and wait again
                continue

            _, article_id_str = result
            try:
                article_id = int(article_id_str)
            except ValueError:
                logger.error("Invalid article ID in queue: %r. Discarding.", article_id_str)
                continue

            logger.info("Dequeued article id=%d.", article_id)
            process_article(article_id, pool, rc)

        except KeyboardInterrupt:
            logger.info("Interrupted. Shutting down cleanly.")
            break
        except redis.exceptions.ConnectionError as exc:
            logger.error("Redis connection lost: %s. Retrying in 5s.", exc)
            time.sleep(5)
        except Exception as exc:
            logger.error("Unexpected error in main loop: %s", exc, exc_info=True)
            time.sleep(1)

    pool.closeall()
    logger.info("Classifier shut down.")


if __name__ == "__main__":
    main()
