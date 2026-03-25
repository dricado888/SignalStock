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
