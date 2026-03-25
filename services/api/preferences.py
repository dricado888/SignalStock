"""User email preference endpoints + token-based unsubscribe."""
import os
from typing import Annotated, List

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user
from database import get_conn

router = APIRouter(tags=["preferences"])

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173")

ALL_EVENT_TYPES = [
    "earnings_report", "merger_acquisition", "product_launch",
    "regulatory_action", "executive_change", "lawsuit", "partnership", "other",
]


# ── Schemas ──────────────────────────────────────────────────────────────────

class PreferencesOut(BaseModel):
    email_enabled: bool
    notify_positive: bool
    notify_negative: bool
    notify_neutral: bool
    notify_event_types: List[str]

class PreferencesIn(BaseModel):
    email_enabled: bool
    notify_positive: bool
    notify_negative: bool
    notify_neutral: bool
    notify_event_types: List[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_prefs(conn, user_id: int) -> dict:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO user_preferences (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
            (user_id,),
        )
        cur.execute(
            "SELECT email_enabled, notify_positive, notify_negative, notify_neutral, notify_event_types "
            "FROM user_preferences WHERE user_id = %s",
            (user_id,),
        )
        return dict(cur.fetchone())


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(
    current_user: Annotated[dict, Depends(get_current_user)],
    conn=Depends(get_conn),
):
    prefs = _get_or_create_prefs(conn, current_user["id"])
    conn.commit()
    return prefs


@router.put("/preferences", response_model=PreferencesOut)
def update_preferences(
    body: PreferencesIn,
    current_user: Annotated[dict, Depends(get_current_user)],
    conn=Depends(get_conn),
):
    # Validate event types
    invalid = [et for et in body.notify_event_types if et not in ALL_EVENT_TYPES]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Invalid event types: {invalid}")

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO user_preferences
                (user_id, email_enabled, notify_positive, notify_negative,
                 notify_neutral, notify_event_types, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (user_id) DO UPDATE SET
                email_enabled      = EXCLUDED.email_enabled,
                notify_positive    = EXCLUDED.notify_positive,
                notify_negative    = EXCLUDED.notify_negative,
                notify_neutral     = EXCLUDED.notify_neutral,
                notify_event_types = EXCLUDED.notify_event_types,
                updated_at         = now()
            RETURNING email_enabled, notify_positive, notify_negative,
                      notify_neutral, notify_event_types
            """,
            (
                current_user["id"],
                body.email_enabled,
                body.notify_positive,
                body.notify_negative,
                body.notify_neutral,
                body.notify_event_types,
            ),
        )
        updated = dict(cur.fetchone())
    conn.commit()
    return updated


@router.get("/auth/unsubscribe")
def unsubscribe(
    token: str = Query(..., description="Unsubscribe token from email link"),
    conn=Depends(get_conn),
):
    """One-click unsubscribe — no auth required. Called from email footer link."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT user_id FROM user_preferences WHERE unsubscribe_token = %s",
            (token,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invalid unsubscribe token")

        cur.execute(
            "UPDATE user_preferences SET email_enabled = FALSE, updated_at = now() "
            "WHERE unsubscribe_token = %s",
            (token,),
        )
    conn.commit()
    return {
        "success": True,
        "message": "You have been unsubscribed from SignalStock email alerts.",
        "manage_url": f"{APP_BASE_URL}/settings",
    }
