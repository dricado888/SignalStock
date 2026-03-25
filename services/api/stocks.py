"""Stock search and live price endpoints — public, no auth required."""
import os
import time
import psycopg2.extras
import httpx
import redis as redis_lib
from fastapi import APIRouter, Depends, Query

from database import get_conn

router = APIRouter(prefix="/stocks", tags=["stocks"])

# ---------------------------------------------------------------------------
# Redis + Finnhub config
# ---------------------------------------------------------------------------
FINNHUB_KEY  = os.getenv("FINNHUB_API_KEY", "")
REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379")
PRICE_TTL    = 60  # seconds

def _redis():
    try:
        return redis_lib.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


def _fetch_quote(ticker: str, r) -> dict | None:
    """Fetch a single Finnhub quote, using Redis cache."""
    cache_key = f"price:{ticker.upper()}"
    if r:
        cached = r.get(cache_key)
        if cached:
            import json
            return json.loads(cached)

    if not FINNHUB_KEY:
        return None

    try:
        resp = httpx.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": ticker.upper(), "token": FINNHUB_KEY},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        price      = data.get("c")
        prev_close = data.get("pc") or 0
        change_abs = data.get("d") or 0
        change_pct = data.get("dp") or 0
        if price is None or price == 0:
            return None

        direction = "up" if change_pct > 0.01 else "down" if change_pct < -0.01 else "flat"
        result = {
            "ticker":     ticker.upper(),
            "price":      round(float(price), 2),
            "change_abs": round(float(change_abs), 2),
            "change_pct": round(float(change_pct), 2),
            "direction":  direction,
        }
        if r:
            import json
            r.set(cache_key, json.dumps(result), ex=PRICE_TTL)
        return result
    except Exception:
        return None


@router.get("")
def search_stocks(
    q: str = Query("", description="Search ticker or company name"),
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_conn),
):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if q:
            cur.execute(
                """
                SELECT id, ticker, company_name
                FROM stocks
                WHERE ticker ILIKE %s OR company_name ILIKE %s
                ORDER BY ticker
                LIMIT %s
                """,
                (f"%{q.upper()}%", f"%{q}%", limit),
            )
        else:
            cur.execute(
                "SELECT id, ticker, company_name FROM stocks ORDER BY ticker LIMIT %s",
                (limit,),
            )
        return [dict(r) for r in cur.fetchall()]


@router.get("/prices")
def get_stock_prices(
    tickers: str = Query(..., description="Comma-separated tickers, e.g. NVDA,AAPL"),
):
    """Fetch live quotes from Finnhub for up to 10 tickers. Cached 60s in Redis."""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()][:10]
    if not ticker_list:
        return []

    r = _redis()
    results = []
    for ticker in ticker_list:
        quote = _fetch_quote(ticker, r)
        if quote:
            results.append(quote)
    return results
