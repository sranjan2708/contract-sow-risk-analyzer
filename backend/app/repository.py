"""
Database repository for user management.
Uses raw parameterized SQL (%s) with PyMySQL connection context manager.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.app.db import get_connection

logger = logging.getLogger(__name__)


def create_user(email: str, password_hash: str, full_name: str) -> int:
    """
    Insert a new user record into the users table using raw parameterized SQL.

    Args:
        email: Unique user email address.
        password_hash: Bcrypt password hash.
        full_name: Full name of the user.

    Returns:
        The auto-generated user_id (int).
    """
    sql = (
        "INSERT INTO users (email, password_hash, full_name) "
        "VALUES (%s, %s, %s)"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email, password_hash, full_name))
            user_id = cursor.lastrowid
            logger.info("Successfully registered user ID %d (%s)", user_id, email)
            return int(user_id)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user record by email address using raw parameterized SQL.

    Args:
        email: Email address to search for.

    Returns:
        Dict of user row fields or None if not found.
    """
    sql = (
        "SELECT user_id, email, password_hash, full_name, created_at "
        "FROM users WHERE email = %s"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email,))
            return cursor.fetchone()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve user record by user_id using raw parameterized SQL.

    Args:
        user_id: User identifier.

    Returns:
        Dict of user row fields or None if not found.
    """
    sql = (
        "SELECT user_id, email, password_hash, full_name, created_at "
        "FROM users WHERE user_id = %s"
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id,))
            return cursor.fetchone()

