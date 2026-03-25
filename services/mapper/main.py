"""
SignalStock Stock Mapper
========================
Polls the database for classified events that have no event_stocks rows yet,
extracts ticker symbols from each event's article, and writes the linkages to
the stocks + event_stocks tables.

Flow per batch:
  SELECT events WHERE NOT EXISTS event_stocks  (up to BATCH_SIZE rows)
      → extract_tickers(title, content)
      → get_or_create stock row for each ticker
      → INSERT into event_stocks
      → commit
      → sleep POLL_INTERVAL if queue was empty, else continue immediately
"""

import logging
import os
import sys
import time
from typing import Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv

import ticker_extractor
from company_mapping import TICKER_TO_COMPANY
from sector_affinity import get_indirect_tickers

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("mapper.main")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]
# Seconds to wait between polls when the queue is empty
POLL_INTERVAL: int = int(os.environ.get("POLL_INTERVAL", "30"))
# Max events processed per DB query
BATCH_SIZE: int = int(os.environ.get("BATCH_SIZE", "10"))

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def create_db_pool(dsn: str) -> psycopg2.pool.ThreadedConnectionPool:
    """Create a psycopg2 connection pool."""
    return psycopg2.pool.ThreadedConnectionPool(1, 5, dsn=dsn)


def fetch_unmapped_events(
    conn: psycopg2.extensions.connection,
    limit: int,
) -> list[dict]:
    """
    Return classified events that have no event_stocks rows yet.

    Args:
        conn:  Active psycopg2 connection.
        limit: Maximum number of events to return.

    Returns:
        List of dicts with keys: {id, article_id, event_type, title, content}.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT e.id, e.article_id, e.event_type, a.title, a.content
            FROM events e
            JOIN articles a ON e.article_id = a.id
            WHERE NOT EXISTS (
                SELECT 1 FROM event_stocks es WHERE es.event_id = e.id
            )
            ORDER BY e.classified_at ASC
            LIMIT %s
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_stock_id_if_exists(
    conn: psycopg2.extensions.connection,
    ticker: str,
) -> Optional[int]:
    """
    Return the stocks.id for a ticker if it already exists, else None.

    Used for sector-affinity linking: we only link indirectly-affected
    stocks that are already tracked — we never auto-create them.

    Args:
        conn:   Active psycopg2 connection.
        ticker: Stock ticker symbol (e.g. "NVDA").

    Returns:
        Integer stock ID, or None if not found.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM stocks WHERE ticker = %s", (ticker,))
        row = cur.fetchone()
        return row[0] if row else None


def get_or_create_stock(
    conn: psycopg2.extensions.connection,
    ticker: str,
    company_name: str,
) -> int:
    """
    Return existing stock ID or insert a new row.

    Args:
        conn:         Active psycopg2 connection.
        ticker:       Stock ticker symbol (e.g. "AAPL").
        company_name: Human-readable name used when creating a new row.

    Returns:
        Stocks table row ID.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM stocks WHERE ticker = %s", (ticker,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO stocks (ticker, company_name) VALUES (%s, %s) RETURNING id",
            (ticker, company_name),
        )
        return cur.fetchone()[0]


def link_event_stock(
    conn: psycopg2.extensions.connection,
    event_id: int,
    stock_id: int,
) -> None:
    """
    Insert an event_stocks row, ignoring duplicates.

    Args:
        conn:     Active psycopg2 connection.
        event_id: FK to events.id.
        stock_id: FK to stocks.id.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO event_stocks (event_id, stock_id)
            VALUES (%s, %s)
            ON CONFLICT (event_id, stock_id) DO NOTHING
            """,
            (event_id, stock_id),
        )


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------


def process_event(
    event: dict,
    conn: psycopg2.extensions.connection,
    skipped_ids: set[int],
) -> bool:
    """
    Extract tickers for one event and create stock linkages.

    Events with no extractable tickers are added to skipped_ids so they are
    not repeatedly re-processed within the same session (they will be retried
    on the next service restart).

    Args:
        event:       Dict with {id, article_id, title, content}.
        conn:        Active psycopg2 connection (caller handles pool).
        skipped_ids: Mutable set; event IDs with no tickers are added here.

    Returns:
        True if at least one stock link was created.
    """
    event_id   = event["id"]
    title      = event.get("title", "")
    content    = event.get("content", "")
    event_type = event.get("event_type", "")

    tickers = ticker_extractor.extract_tickers(title, content)

    linked = 0

    # --- Step 1: direct ticker extraction (existing behaviour) ---
    for ticker in tickers:
        company_name = TICKER_TO_COMPANY.get(ticker, ticker)
        try:
            stock_id = get_or_create_stock(conn, ticker, company_name)
            link_event_stock(conn, event_id, stock_id)
            linked += 1
        except Exception as exc:
            logger.error(
                "Failed to link ticker %s to event id=%d: %s",
                ticker,
                event_id,
                exc,
            )
            try:
                conn.rollback()
            except Exception:
                pass

    # --- Step 2: sector affinity (indirect stock linking) ---
    # Only applied to generic market/macro news (event_type == "other").
    # Company-specific events (earnings, M&A, product launch) that happen to
    # mention common economic terms should NOT inherit sector stocks.
    if event_type == "other":
        indirect_tickers = get_indirect_tickers(title)
        indirect_linked  = 0
        for ticker in indirect_tickers:
            try:
                stock_id = get_stock_id_if_exists(conn, ticker)
                if stock_id is None:
                    continue
                link_event_stock(conn, event_id, stock_id)
                indirect_linked += 1
            except Exception as exc:
                logger.error(
                    "Failed to link indirect ticker %s to event id=%d: %s",
                    ticker,
                    event_id,
                    exc,
                )
                try:
                    conn.rollback()
                except Exception:
                    pass

        if indirect_linked > 0:
            linked += indirect_linked
            logger.info(
                "Event id=%d → sector affinity linked %d indirect ticker(s): %s",
                event_id,
                indirect_linked,
                indirect_tickers,
            )

    if linked > 0:
        conn.commit()
        logger.info(
            "Event id=%d → total %d stock link(s) created (direct=%d).",
            event_id,
            linked,
            len(tickers),
        )
        return True

    # Nothing found via either method — skip for this session
    logger.warning(
        "No tickers found for event id=%d (article id=%d, title=%.80s). "
        "Skipping for this session.",
        event_id,
        event["article_id"],
        title,
    )
    skipped_ids.add(event_id)
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """
    Main loop: poll database for unmapped events and link them to stocks.

    - Fetches up to BATCH_SIZE events per iteration.
    - Sleeps POLL_INTERVAL seconds when no unmapped events are found.
    - Keeps an in-memory set of events that had no tickers so they are not
      re-attempted on every poll within the same session.
    - Exits cleanly on KeyboardInterrupt.
    """
    logger.info("SignalStock stock mapper starting up.")

    try:
        pool = create_db_pool(DATABASE_URL)
        logger.info("PostgreSQL connection pool created.")
    except Exception as exc:
        logger.critical("Cannot connect to PostgreSQL: %s", exc)
        sys.exit(1)

    # Events with no tickers — skip within this session to avoid tight loops
    skipped_ids: set[int] = set()

    while True:
        conn = None
        try:
            conn = pool.getconn()
            events = fetch_unmapped_events(conn, BATCH_SIZE)
            pool.putconn(conn)
            conn = None

            # Filter out events we already know have no tickers
            events = [e for e in events if e["id"] not in skipped_ids]

            if not events:
                logger.debug(
                    "No new unmapped events. Sleeping %ds.", POLL_INTERVAL
                )
                time.sleep(POLL_INTERVAL)
                continue

            logger.info(
                "Found %d unmapped event(s). Processing...", len(events)
            )
            conn = pool.getconn()
            for event in events:
                process_event(event, conn, skipped_ids)

        except KeyboardInterrupt:
            logger.info("Interrupted. Shutting down cleanly.")
            break
        except psycopg2.Error as exc:
            logger.error("Database error in main loop: %s", exc)
            try:
                if conn is not None:
                    conn.rollback()
            except Exception:
                pass
            time.sleep(5)
        except Exception as exc:
            logger.error(
                "Unexpected error in main loop: %s", exc, exc_info=True
            )
            time.sleep(1)
        finally:
            if conn is not None:
                pool.putconn(conn)
                conn = None

    pool.closeall()
    logger.info("Mapper shut down.")


if __name__ == "__main__":
    main()
