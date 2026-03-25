"""
SignalStock Alert Engine
========================
Polls the database every POLL_INTERVAL seconds for stock events that match
users' watchlists and haven't been alerted yet. Sends an email via SendGrid
for each match and records it in alerts_sent to prevent duplicates.

Flow per poll:
  SELECT alertable events (watchlist JOIN events LEFT JOIN alerts_sent)
      -> send_alert_email(user, event, stock, article)
      -> INSERT into alerts_sent
      -> sleep POLL_INTERVAL
"""

import logging
import os
import sys
import time

import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv

import email_client

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("alerts.main")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

DATABASE_URL: str  = os.environ["DATABASE_URL"]
POLL_INTERVAL: int = int(os.environ.get("POLL_INTERVAL", "60"))
BATCH_SIZE: int    = int(os.environ.get("BATCH_SIZE", "50"))

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def create_db_pool(dsn: str) -> psycopg2.pool.ThreadedConnectionPool:
    """Create a psycopg2 connection pool."""
    return psycopg2.pool.ThreadedConnectionPool(1, 5, dsn=dsn)


def fetch_alertable_events(
    conn: psycopg2.extensions.connection,
    limit: int,
) -> list[dict]:
    """
    Return watchlist-matched events that haven't been alerted yet.

    Joins users -> watchlists -> stocks -> event_stocks -> events -> articles,
    excluding rows already present in alerts_sent.

    Args:
        conn:  Active psycopg2 connection.
        limit: Max rows to return per call.

    Returns:
        List of dicts with keys:
          {user_id, email, event_id, event_type, sentiment,
           stock_id, ticker, company_name,
           article_id, title, url, published_at}
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT
                u.id                    AS user_id,
                u.email,
                e.id                    AS event_id,
                e.event_type,
                e.sentiment,
                s.id                    AS stock_id,
                s.ticker,
                s.company_name,
                a.id                    AS article_id,
                a.title,
                a.url,
                a.source,
                a.published_at,
                up.unsubscribe_token
            FROM users u
            JOIN user_preferences   up ON up.user_id     = u.id
            JOIN watchlists         w  ON w.user_id      = u.id
            JOIN stocks             s  ON s.id           = w.stock_id
            JOIN event_stocks       es ON es.stock_id    = s.id
            JOIN events             e  ON e.id           = es.event_id
            JOIN articles           a  ON a.id           = e.article_id
            WHERE up.email_enabled = TRUE
              AND (
                  (e.sentiment = 'positive' AND up.notify_positive = TRUE) OR
                  (e.sentiment = 'negative' AND up.notify_negative = TRUE) OR
                  (e.sentiment = 'neutral'  AND up.notify_neutral  = TRUE)
              )
              AND e.event_type = ANY(up.notify_event_types)
              AND NOT EXISTS (
                  SELECT 1 FROM alerts_sent als
                  WHERE als.user_id = u.id AND als.event_id = e.id
              )
            ORDER BY a.published_at DESC NULLS LAST
            LIMIT %s
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def record_alert_sent(
    conn: psycopg2.extensions.connection,
    user_id: int,
    event_id: int,
) -> None:
    """
    Insert an alerts_sent row, ignoring if it already exists.

    Args:
        conn:     Active psycopg2 connection.
        user_id:  FK to users.id.
        event_id: FK to events.id.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts_sent (user_id, event_id, sent_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id, event_id) DO NOTHING
            """,
            (user_id, event_id),
        )


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------


def process_alert(row: dict, conn: psycopg2.extensions.connection) -> bool:
    """
    Send one alert email and record it on success.

    Args:
        row:  Dict from fetch_alertable_events.
        conn: Active psycopg2 connection (caller manages pool).

    Returns:
        True if email sent and recorded, False otherwise.
    """
    user_id           = row["user_id"]
    event_id          = row["event_id"]
    email             = row["email"]
    ticker            = row["ticker"]
    unsubscribe_token = row.get("unsubscribe_token", "")

    event   = {k: row[k] for k in ("event_id", "event_type", "sentiment")}
    stock   = {k: row[k] for k in ("stock_id", "ticker", "company_name")}
    article = {k: row[k] for k in ("article_id", "title", "url", "source", "published_at")}

    sent = email_client.send_alert_email(
        user_email=email,
        event=event,
        stock=stock,
        article=article,
        unsubscribe_token=str(unsubscribe_token) if unsubscribe_token else "",
    )

    if sent:
        record_alert_sent(conn, user_id, event_id)
        conn.commit()
        logger.info(
            "Alert recorded: user_id=%d event_id=%d ticker=%s",
            user_id, event_id, ticker,
        )
    else:
        logger.warning(
            "Email not sent; alert NOT recorded for user_id=%d event_id=%d.",
            user_id, event_id,
        )

    return sent


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """
    Main loop: poll for alertable events and send emails every POLL_INTERVAL s.

    - Fetches up to BATCH_SIZE rows per poll.
    - Records each successful send immediately so re-runs won't duplicate.
    - Sleeps POLL_INTERVAL seconds after each poll (even if events were found).
    - Exits cleanly on KeyboardInterrupt.
    """
    logger.info("SignalStock alert engine starting up.")

    try:
        pool = create_db_pool(DATABASE_URL)
        logger.info("PostgreSQL connection pool created.")
    except Exception as exc:
        logger.critical("Cannot connect to PostgreSQL: %s", exc)
        sys.exit(1)

    while True:
        conn = None
        try:
            conn = pool.getconn()
            rows = fetch_alertable_events(conn, BATCH_SIZE)

            if not rows:
                logger.debug("No pending alerts. Sleeping %ds.", POLL_INTERVAL)
            else:
                logger.info(
                    "Found %d pending alert(s). Sending...", len(rows)
                )
                sent_count = 0
                for row in rows:
                    if process_alert(row, conn):
                        sent_count += 1
                logger.info(
                    "Sent %d/%d alert(s) this cycle.", sent_count, len(rows)
                )

        except KeyboardInterrupt:
            logger.info("Interrupted. Shutting down cleanly.")
            if conn is not None:
                pool.putconn(conn)
            break
        except psycopg2.Error as exc:
            logger.error("Database error: %s", exc)
            try:
                if conn is not None:
                    conn.rollback()
            except Exception:
                pass
        except Exception as exc:
            logger.error("Unexpected error: %s", exc, exc_info=True)
        finally:
            if conn is not None:
                pool.putconn(conn)
                conn = None

        try:
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Interrupted during sleep. Shutting down cleanly.")
            break

    pool.closeall()
    logger.info("Alert engine shut down.")


if __name__ == "__main__":
    main()
