"""
Unit tests for backend security utilities: password hashing and JWT token handling.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from jose import jwt
import pytest

from backend.app.config import get_settings
from backend.app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    """Verify password hashing produces valid hash and verification succeeds/fails accurately."""
    raw_password = "SecurePassword123!"
    hashed = hash_password(raw_password)

    # Hash should be distinct from the plain text
    assert hashed != raw_password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    # Correct password verifies True
    assert verify_password(raw_password, hashed) is True

    # Incorrect password verifies False
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False


def test_token_round_trip():
    """Verify create_access_token and decode_access_token correctly round-trip user_id."""
    user_id = 42
    token = create_access_token(user_id=user_id)
    assert isinstance(token, str)
    assert len(token) > 0

    decoded_id = decode_access_token(token)
    assert decoded_id == user_id
    assert isinstance(decoded_id, int)


def test_garbage_token_raises_value_error():
    """Verify passing a garbage or malformed token string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid or expired access token"):
        decode_access_token("not.a.valid.jwt.token")

    with pytest.raises(ValueError, match="Invalid or expired access token"):
        decode_access_token("completely-invalid-garbage")


def test_expired_token_raises_value_error():
    """Verify that an expired token raises ValueError."""
    settings = get_settings()
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    token = jwt.encode(
        {"sub": "99", "exp": expired_time},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(ValueError, match="Invalid or expired access token"):
        decode_access_token(token)


def test_token_without_sub_raises_value_error():
    """Verify that a valid token missing the 'sub' claim raises ValueError."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    token = jwt.encode(
        {"data": "some_value", "exp": expire},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(ValueError, match="Invalid or expired access token"):
        decode_access_token(token)

