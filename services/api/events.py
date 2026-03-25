"""Events listing with filtering, pagination, and stats."""
from typing import Optional
from datetime import datetime, timedelta, timezone

import psycopg2.extras
from fastapi import APIRouter, Depends, Query

from database import get_conn

router = APIRouter(prefix="/events", tags=["events"])


def _build_events_query(where_clauses, params, limit, offset):
    base = """
        SELECT
            e.id, e.event_type, e.sentiment, e.classified_at,
            a.id AS article_id, a.title AS article_title,
            a.url AS article_url, a.source AS article_source,
            a.published_at,
            COALESCE(
                json_agg(
                    json_build_object('ticker', s.ticker, 'company_name', s.company_name)
                ) FILTER (WHERE s.id IS NOT NULL), '[]'
            ) AS stocks
        FROM events e
        JOIN articles a ON e.article_id = a.id
        LEFT JOIN event_stocks es ON e.id = es.event_id
        LEFT JOIN stocks s ON es.stock_id = s.id
    """
    where    = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    group    = "GROUP BY e.id, a.id"
    order    = "ORDER BY COALESCE(a.published_at, e.classified_at) DESC"
    data_sql = f"{base} {where} {group} {order} LIMIT {limit} OFFSET {offset}"
    count_sql = (
        "SELECT COUNT(DISTINCT e.id) FROM events e "
        "JOIN articles a ON e.article_id = a.id "
        "LEFT JOIN event_stocks es ON e.id = es.event_id "
        f"LEFT JOIN stocks s ON es.stock_id = s.id {where}"
    )
    return data_sql, count_sql


@router.get("")
def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    tickers: Optional[str] = Query(None, description="Comma-separated tickers, e.g. AAPL,TSLA"),
    has_stocks: Optional[bool] = Query(None, description="true=only events with stock links, false=only without"),
    exclude_neutral: bool = Query(False, description="Exclude neutral-sentiment events"),
    conn=Depends(get_conn),
):
    offset = (page - 1) * limit
    where, params = [], []

    if event_type:
        where.append("e.event_type = %s")
        params.append(event_type)
    if sentiment:
        where.append("e.sentiment = %s")
        params.append(sentiment)
    if exclude_neutral:
        where.append("e.sentiment != 'neutral'")
    if has_stocks is True:
        where.append("EXISTS (SELECT 1 FROM event_stocks WHERE event_id = e.id)")
    elif has_stocks is False:
        where.append("NOT EXISTS (SELECT 1 FROM event_stocks WHERE event_id = e.id)")
    # Multi-ticker filter takes precedence over single ticker
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if ticker_list:
            where.append(
                "EXISTS (SELECT 1 FROM event_stocks es2 "
                "JOIN stocks s2 ON es2.stock_id=s2.id "
                "WHERE es2.event_id=e.id AND s2.ticker = ANY(%s))"
            )
            params.append(ticker_list)
    elif ticker:
        where.append(
            "EXISTS (SELECT 1 FROM event_stocks es2 "
            "JOIN stocks s2 ON es2.stock_id=s2.id "
            "WHERE es2.event_id=e.id AND s2.ticker = %s)"
        )
        params.append(ticker.upper())

    data_sql, count_sql = _build_events_query(where, params, limit, offset)

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(count_sql, params)
        total = cur.fetchone()["count"]
        cur.execute(data_sql, params)
        rows = [dict(r) for r in cur.fetchall()]

    return {
        "events": rows,
        "total": total,
        "page": page,
        "pages": max(1, -(-int(total) // limit)),
    }


@router.get("/stats")
def events_stats(conn=Depends(get_conn)):
    """Aggregated stats for dashboard charts. No auth required."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Totals
        cur.execute("SELECT COUNT(*) AS total FROM events")
        total_events = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM stocks")
        total_stocks = cur.fetchone()["total"]

        cur.execute(
            "SELECT COUNT(*) AS total FROM events "
            "WHERE classified_at >= NOW() - INTERVAL '24 hours'"
        )
        today_count = cur.fetchone()["total"]

        # Sentiment breakdown
        cur.execute(
            "SELECT sentiment, COUNT(*) AS cnt FROM events GROUP BY sentiment"
        )
        sentiment_counts = {r["sentiment"]: r["cnt"] for r in cur.fetchall()}

        # Events per day — last 7 days
        cur.execute(
            """
            SELECT DATE(COALESCE(a.published_at, e.classified_at)) AS day,
                   COUNT(*) AS cnt
            FROM events e
            JOIN articles a ON e.article_id = a.id
            WHERE COALESCE(a.published_at, e.classified_at) >= NOW() - INTERVAL '7 days'
            GROUP BY day
            ORDER BY day
            """
        )
        events_by_day = [
            {"date": str(r["day"]), "count": r["cnt"]} for r in cur.fetchall()
        ]

        # Top 5 stocks by event count
        cur.execute(
            """
            SELECT s.ticker, COUNT(es.event_id) AS cnt
            FROM stocks s
            JOIN event_stocks es ON s.id = es.stock_id
            GROUP BY s.ticker
            ORDER BY cnt DESC
            LIMIT 5
            """
        )
        top_stocks = [{"ticker": r["ticker"], "count": r["cnt"]} for r in cur.fetchall()]

    total = int(total_events)
    pos = int(sentiment_counts.get("positive", 0))
    bullish_pct = round(pos / total * 100) if total else 0

    return {
        "total_events":     total,
        "total_stocks":     int(total_stocks),
        "today_count":      int(today_count),
        "bullish_pct":      bullish_pct,
        "sentiment_counts": {k: int(v) for k, v in sentiment_counts.items()},
        "events_by_day":    events_by_day,
        "top_stocks":       top_stocks,
    }
