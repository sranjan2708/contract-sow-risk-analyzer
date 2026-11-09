"""
Security and authentication utilities.
Handles password hashing via passlib bcrypt and JWT encoding/decoding via python-jose.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.config import get_settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: Plain text password to hash.

    Returns:
        Bcrypt hashed password string.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a stored bcrypt hash.

    Args:
        plain_password: Plain text password candidate.
        hashed_password: Stored bcrypt password hash.

    Returns:
        True if password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    """
    Generate a signed JWT access token for the given user ID.

    Args:
        user_id: User identifier to encode in token subject ('sub').

    Returns:
        Encoded JWT token string.
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode: Dict[str, Any] = {
        "sub": str(user_id),
        "exp": expire,
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> int:
    """
    Decode and validate a JWT access token, returning the user_id.

    Args:
        token: JWT string to decode.

    Raises:
        ValueError: If token is invalid, expired, malformed, or missing subject.

    Returns:
        Extracted user_id as an integer.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        sub = payload.get("sub")
        if sub is None:
            raise ValueError("Token missing 'sub' subject claim")
        return int(sub)
    except (JWTError, ValueError, TypeError) as exc:
        logger.warning("Failed to decode access token: %s", exc)
        raise ValueError(f"Invalid or expired access token: {exc}") from exc

