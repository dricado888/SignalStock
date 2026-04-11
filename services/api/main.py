"""SignalStock API — FastAPI entry point."""
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health/db")
def health_db():
    """Diagnostic: test DB connection and report the error if it fails."""
    import os, psycopg2
    url = os.environ.get("DATABASE_URL", "NOT_SET")
    # Redact password for safety
    try:
        from urllib.parse import urlparse
        p = urlparse(url)
        safe_url = f"{p.scheme}://{p.username}:***@{p.hostname}:{p.port}{p.path}"
    except Exception:
        safe_url = url[:30] + "..."
    try:
        conn = psycopg2.connect(url)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            count = cur.fetchone()[0]
        conn.close()
        return {"status": "ok", "events_count": count, "url": safe_url}
    except Exception as e:
        return {"status": "error", "error": str(e), "url": safe_url}
