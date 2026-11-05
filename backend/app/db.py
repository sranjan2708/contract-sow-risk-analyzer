"""
Database access layer using PyMySQL and DictCursor.
Raw parameterized SQL only — NO SQLAlchemy or ORM allowed.
Database connection is NOT required to start the application or run test suites.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import pymysql
from pymysql.cursors import DictCursor

from backend.app.config import get_settings

logger = logging.getLogger(__name__)


@contextmanager
def get_connection() -> Generator[pymysql.Connection, None, None]:
    """
    Context manager yielding a PyMySQL connection with DictCursor.
    Commits on success, rolls back on exception, and guarantees connection close.
    """
    settings = get_settings()
    conn = pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ping() -> bool:
    """
    Check connectivity to the MySQL database server.
    Returns True if reachable, False otherwise.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 AS status")
                result = cursor.fetchone()
                return bool(result and result.get("status") == 1)
    except Exception as exc:
        logger.warning("Database ping failed (DB not required in mock/test mode): %s", exc)
        return False

