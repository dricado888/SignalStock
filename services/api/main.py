"""SignalStock API — FastAPI entry point."""
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import get_conn

import auth
import events
import watchlist
import stocks
import preferences

app = FastAPI(title="SignalStock API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(watchlist.router)
app.include_router(stocks.router)
app.include_router(preferences.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/admin/requeue")
def admin_requeue(secret: str, conn=Depends(get_conn)):
    """Delete all events/event_stocks and re-queue articles to Redis. Temporary endpoint."""
    import redis as _redis
    if secret != os.environ.get("ADMIN_SECRET", "no-secret-set"):
        raise HTTPException(status_code=403, detail="Forbidden")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM event_stocks")
        cur.execute("DELETE FROM events")
        cur.execute("SELECT id FROM articles ORDER BY scraped_at DESC LIMIT 500")
        article_ids = [r[0] for r in cur.fetchall()]
    conn.commit()
    rc = _redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    for aid in article_ids:
        rc.rpush("articles:pending", aid)
    return {"deleted_events": True, "requeued_articles": len(article_ids)}
