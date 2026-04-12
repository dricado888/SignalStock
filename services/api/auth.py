"""JWT auth: register, login, /me."""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt as _bcrypt
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field

from database import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.environ.get("JWT_SECRET", "change-me-in-production-please")
if SECRET_KEY == "change-me-in-production-please":
    import logging as _log
    _log.getLogger(__name__).warning(
        "JWT_SECRET is using the insecure default value! Set JWT_SECRET env var in production."
    )
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

bearer = HTTPBearer()


def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime

class TokenOut(BaseModel):
    token: str
    user: UserOut


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, ALGORITHM)


def _verify_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    conn=Depends(get_conn),
) -> dict:
    user_id = _verify_token(creds.credentials)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, email, created_at FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, conn=Depends(get_conn)):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Email already registered")

        hashed = _hash_password(body.password)
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email, created_at",
            (body.email, hashed),
        )
        user = dict(cur.fetchone())
        # Auto-create default preferences row for new user
        cur.execute(
            "INSERT INTO user_preferences (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
            (user["id"],),
        )
    conn.commit()
    return {"token": _make_token(user["id"]), "user": user}


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, conn=Depends(get_conn)):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = %s",
            (body.email,),
        )
        row = cur.fetchone()

    if not row or not _verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}
    return {"token": _make_token(user["id"]), "user": user}


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user
