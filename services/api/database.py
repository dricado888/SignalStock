"""PostgreSQL connection pool shared across the API."""
import os
import psycopg2
import psycopg2.pool
import psycopg2.extras

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            1, 10, dsn=os.environ["DATABASE_URL"]
        )
    return _pool


def get_conn():
    """FastAPI dependency — yields a connection, returns it on exit."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)
