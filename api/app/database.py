"""
Database connection pool and cursor management.

Uses python-oracledb's built-in connection pooling. Connections are acquired
from the pool per-request and released back automatically via the dependency
injection pattern.
"""

import os

import oracledb
from contextlib import contextmanager
from typing import Generator

from app.config import settings

# Return LOB columns as Python strings/bytes instead of LOB objects.
oracledb.defaults.fetch_lobs = False

# Module-level pool reference, initialized on startup
_pool: oracledb.ConnectionPool | None = None


def init_pool():
    """
    Initialize the Oracle connection pool. Called once at application startup.
    """
    global _pool

    pool_params = {
        "user": settings.oracle_user,
        "password": settings.oracle_password,
        "dsn": settings.oracle_dsn,
        "min": settings.pool_min,
        "max": settings.pool_max,
        "increment": settings.pool_increment,
    }

    wallet_dir = settings.oracle_wallet_dir.strip() if settings.oracle_wallet_dir else ""
    if wallet_dir and os.path.isdir(wallet_dir):
        pool_params["config_dir"] = wallet_dir
        pool_params["wallet_location"] = wallet_dir
        pool_params["wallet_password"] = settings.oracle_password

    _pool = oracledb.create_pool(**pool_params)


def close_pool():
    """Close the connection pool. Called at application shutdown."""
    global _pool
    if _pool:
        _pool.close(force=True)
        _pool = None


def get_connection() -> Generator[oracledb.Connection, None, None]:
    """
    FastAPI dependency that yields a database connection from the pool.

    Usage in a router:
        @router.get("/something")
        async def get_something(conn: oracledb.Connection = Depends(get_connection)):
            cursor = conn.cursor()
            ...
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")

    conn = _pool.acquire()
    try:
        yield conn
    finally:
        _pool.release(conn)


@contextmanager
def get_cursor(conn: oracledb.Connection):
    """
    Context manager for cursor lifecycle. Ensures cursors are closed
    even if an exception occurs.

    Usage:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT ...")
    """
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
