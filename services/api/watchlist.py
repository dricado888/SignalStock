"""Watchlist CRUD endpoints."""
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from database import get_conn

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class AddStockIn(BaseModel):
    ticker: str


@router.get("")
def get_watchlist(conn=Depends(get_conn), current_user=Depends(get_current_user)):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT s.id, s.ticker, s.company_name, w.created_at AS added_at
            FROM watchlists w
            JOIN stocks s ON w.stock_id = s.id
            WHERE w.user_id = %s
            ORDER BY w.created_at DESC
            """,
            (current_user["id"],),
        )
        return [dict(r) for r in cur.fetchall()]


@router.post("", status_code=201)
def add_to_watchlist(
    body: AddStockIn,
    conn=Depends(get_conn),
    current_user=Depends(get_current_user),
):
    ticker = body.ticker.upper().strip()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, ticker, company_name FROM stocks WHERE ticker = %s", (ticker,))
        stock = cur.fetchone()
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock '{ticker}' not found in database")

        cur.execute(
            "INSERT INTO watchlists (user_id, stock_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (current_user["id"], stock["id"]),
        )
    conn.commit()
    return dict(stock)


@router.delete("/{stock_id}", status_code=204)
def remove_from_watchlist(
    stock_id: int,
    conn=Depends(get_conn),
    current_user=Depends(get_current_user),
):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM watchlists WHERE user_id = %s AND stock_id = %s",
            (current_user["id"], stock_id),
        )
    conn.commit()
